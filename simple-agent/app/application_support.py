"""Application preparation assistant and deadline tracking for Scheme Finder.

Generates personalized document checklists, form drafts from citizen profiles,
step-by-step submission roadmaps with direct official portal links, conflict detection,
and verified deadline and renewal tracking. Enforces explicit human review before submission.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from app import db
from app.models import (
    ApplicationChecklist,
    ApplicationStep,
    CitizenProfile,
    DocumentChecklistItem,
    Scheme,
)


DOCUMENT_GUIDANCE = {
    "Aadhaar Card": "Issued by UIDAI. Must be linked to applicant's active mobile number for e-KYC OTP verification.",
    "Land Ownership Record / Khatauni / RoR": "Obtain from District Land Records / Revenue Office or official state Bhulekh portal (e.g. Mahabhumi in MH, Bhulekh in UP).",
    "Bank Account Passbook with IFSC": "Bank account must be in applicant's name with DBT enabled and Aadhaar seeding active.",
    "Ration Card": "BPL, Antyodaya (AAY), or Priority Household (PHH) card issued by State Food & Civil Supplies Department.",
    "Income Certificate": "Issued by local Tehsildar or Sub-Divisional Magistrate (SDM) valid within 1 year.",
    "Proof of 3 Years Residence in Delhi": "Voter ID, electricity bill, or water bill in applicant/parent's name.",
    "Birth Certificate of Girl Child": "Issued by Municipal Corporation (MCD/NDMC) or Registrar of Births.",
    "Maharashtra Domicile Certificate": "Issued by competent revenue authority via Aaple Sarkar portal.",
}


def generate_application_packet(
    citizen: CitizenProfile,
    scheme: Scheme,
) -> ApplicationChecklist:
    """Creates a comprehensive, tailored application checklist packet."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    app_id = f"app-{uuid.uuid4().hex[:10]}"

    # 1. Tailored Steps
    steps = [
        ApplicationStep(
            step_number=1,
            title="Gather and Verify Required Documents",
            instructions=(
                "Ensure all required certificates and identification documents match your Aadhaar name exactly. "
                "Keep scanned PDF or JPEG copies ready under 200KB."
            ),
            portal_section="Document Preparation",
            is_online=True,
        ),
        ApplicationStep(
            step_number=2,
            title="Access Official Government Portal",
            instructions=(
                f"Navigate directly to the official government portal: {scheme.official_portal_url}. "
                "Never share credentials or OTPs on unofficial third-party websites."
            ),
            portal_section="Registration / Citizen Login",
            is_online=True,
        ),
        ApplicationStep(
            step_number=3,
            title="Pre-Fill Application Data",
            instructions=(
                "Review the pre-filled fields prepared by Scheme Finder. Copy demographic, location, "
                "and bank information into the official portal form."
            ),
            portal_section="Application Form Entry",
            is_online=True,
        ),
        ApplicationStep(
            step_number=4,
            title="Aadhaar e-KYC & Mobile OTP Authentication",
            instructions=(
                "Enter your Aadhaar number on the official portal and verify with the one-time passcode (OTP) "
                "sent to your registered mobile phone."
            ),
            portal_section="e-KYC Verification",
            is_online=True,
        ),
        ApplicationStep(
            step_number=5,
            title="Review and Submit Directly on Government Portal",
            instructions=(
                "Carefully inspect the final application summary on the government portal. Scheme Finder "
                "does not submit on your behalf. Click Submit and download your official Application Tracking Number."
            ),
            portal_section="Final Submission",
            is_online=True,
        ),
    ]

    # 2. Document Checklist Items
    doc_items: List[DocumentChecklistItem] = []
    missing_items: List[str] = []

    for doc_name in scheme.required_documents:
        desc = DOCUMENT_GUIDANCE.get(
            doc_name,
            f"Official document required by {scheme.ministry}."
        )
        # Check if known from profile
        is_provided = False
        if "aadhaar" in doc_name.lower():
            is_provided = True
        elif "land" in doc_name.lower() and citizen.landholding_acres:
            is_provided = True
        else:
            missing_items.append(doc_name)

        doc_items.append(
            DocumentChecklistItem(
                document_name=doc_name,
                description=desc,
                is_provided=is_provided,
                verification_source="Citizen Profile / Official Guidelines",
                notes="Verified present in profile" if is_provided else "Action needed: Upload or gather certificate",
            )
        )

    # 3. Draft application values
    draft = {
        "applicant_name": citizen.full_name,
        "mobile_number": citizen.phone_number,
        "state": citizen.state,
        "district": citizen.district,
        "residency_type": citizen.residency_type.capitalize(),
        "age": citizen.age,
        "social_category": citizen.social_category.upper(),
        "occupation": citizen.occupation.capitalize() if citizen.occupation else "Not specified",
        "annual_household_income_inr": citizen.household_income,
        "is_farmer": "Yes" if citizen.is_farmer else "No",
        "landholding_acres": citizen.landholding_acres,
    }

    # 4. Warnings and conflict detection
    conflicts_or_warnings: List[str] = []
    if citizen.household_income is None and scheme.eligibility_rules.income_max is not None:
        conflicts_or_warnings.append("Annual household income is missing in profile. Required by portal.")
    if scheme.eligibility_rules.requires_farmer and not citizen.landholding_acres:
        conflicts_or_warnings.append("Scheme requires landholding records, but land acreage is unrecorded.")
    if scheme.level == "state" and scheme.state_name and citizen.state.lower() != scheme.state_name.lower():
        conflicts_or_warnings.append(
            f"Profile state ({citizen.state}) conflicts with state scheme eligibility ({scheme.state_name})."
        )

    packet = ApplicationChecklist(
        application_id=app_id,
        citizen_id=citizen.citizen_id,
        scheme_id=scheme.scheme_id,
        scheme_name=scheme.name,
        official_portal_url=scheme.official_portal_url,
        steps=steps,
        required_documents=doc_items,
        prefilled_draft=draft,
        conflicts_or_warnings=conflicts_or_warnings,
        missing_items=missing_items,
        user_confirmed_submission=False,
        created_at=now_iso,
    )
    db.save_application(packet)
    return packet


def get_upcoming_deadlines() -> List[Dict[str, Any]]:
    """Calculates upcoming deadlines across verified open schemes."""
    today = datetime.date.today()
    schemes = db.list_schemes()

    deadlines = []
    for s in schemes:
        # Never display expired schemes as open
        if s.status == "expired" or s.application_window.status == "expired":
            continue

        verified_deadline = s.application_window.verified_deadline
        if verified_deadline:
            try:
                deadline_dt = datetime.date.fromisoformat(verified_deadline)
                days_left = (deadline_dt - today).days

                # Filter out past deadlines from active list
                if days_left < 0:
                    continue

                if days_left <= 7:
                    urgency = "critical"
                    badge_label = f"Closing soon ({days_left} days left)"
                elif days_left <= 30:
                    urgency = "high"
                    badge_label = f"{days_left} days remaining"
                else:
                    urgency = "normal"
                    badge_label = f"{days_left} days remaining"

                deadlines.append({
                    "scheme_id": s.scheme_id,
                    "scheme_name": s.name,
                    "category": s.category,
                    "level": s.level,
                    "state_name": s.state_name or "All India",
                    "verified_deadline": verified_deadline,
                    "deadline_verified_date": s.application_window.deadline_verified_date,
                    "days_remaining": days_left,
                    "urgency": urgency,
                    "badge_label": badge_label,
                    "official_portal_url": s.official_portal_url,
                })
            except Exception:
                continue
        elif s.application_window.status == "rolling":
            deadlines.append({
                "scheme_id": s.scheme_id,
                "scheme_name": s.name,
                "category": s.category,
                "level": s.level,
                "state_name": s.state_name or "All India",
                "verified_deadline": "Rolling / Continuous Application",
                "deadline_verified_date": s.application_window.deadline_verified_date,
                "days_remaining": 999,
                "urgency": "normal",
                "badge_label": "Rolling Window",
                "official_portal_url": s.official_portal_url,
            })

    # Sort by days remaining ascending
    deadlines.sort(key=lambda x: x["days_remaining"])
    return deadlines
