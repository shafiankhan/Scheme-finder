"""Deterministic eligibility evaluation engine for Scheme Finder.

Implements versioned, rule-based screening comparing citizen profiles against
explicit scheme criteria. Produces auditable condition breakdowns, identifies
missing information, generates focused follow-up questions, and clearly distinguishes
preliminary AI screening from official government determinations.
"""

from __future__ import annotations

from typing import List, Optional
from app.models import CitizenProfile, EligibilityAssessment, Scheme


DISCLAIMER_TEXT = (
    "This is an autonomous preliminary screening based on available versioned criteria. "
    "It is not an official government determination or guarantee of approval. "
    "Final eligibility is determined exclusively by the respective government authority."
)


def assess_scheme_eligibility(profile: CitizenProfile, scheme: Scheme) -> EligibilityAssessment:
    """Evaluate a citizen profile against a single scheme's criteria deterministically."""
    conditions_satisfied: List[str] = []
    conditions_failed: List[str] = []
    conditions_unverified: List[str] = []
    missing_information: List[str] = []
    follow_up_questions: List[str] = []

    rules = scheme.eligibility_rules

    # 1. Check scheme status / validity
    if scheme.status == "expired" or scheme.application_window.status == "expired":
        conditions_failed.append(
            f"Scheme is closed/expired (verified deadline was {scheme.application_window.verified_deadline or 'past'})."
        )
        return EligibilityAssessment(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.name,
            status="ineligible",
            conditions_satisfied=conditions_satisfied,
            conditions_failed=conditions_failed,
            conditions_unverified=conditions_unverified,
            missing_information=missing_information,
            follow_up_questions=follow_up_questions,
            verified_benefit=scheme.verified_benefit,
            verified_deadline=scheme.application_window.verified_deadline,
            official_portal_url=scheme.official_portal_url,
            last_verified_at=scheme.last_verified_at,
            disclaimer=DISCLAIMER_TEXT,
        )

    if scheme.status == "under_review":
        conditions_unverified.append(
            f"Scheme rules are currently under review. Flags: {'; '.join(scheme.uncertainty_flags)}"
        )

    # 2. State restriction
    if rules.allowed_states:
        if profile.state not in rules.allowed_states:
            conditions_failed.append(
                f"Residency restriction: requires state in {', '.join(rules.allowed_states)}; citizen resides in {profile.state}."
            )
        else:
            conditions_satisfied.append(f"Residency in {profile.state} matches eligible state.")

    # 3. Age bounds
    if rules.age_min is not None:
        if profile.age < rules.age_min:
            conditions_failed.append(
                f"Age requirement: minimum age is {rules.age_min} years; citizen is {profile.age}."
            )
        else:
            conditions_satisfied.append(f"Age {profile.age} satisfies minimum age {rules.age_min}.")

    if rules.age_max is not None:
        if profile.age > rules.age_max:
            conditions_failed.append(
                f"Age requirement: maximum age is {rules.age_max} years; citizen is {profile.age}."
            )
        else:
            conditions_satisfied.append(f"Age {profile.age} satisfies maximum age {rules.age_max}.")

    # 4. Income bounds
    if rules.income_max is not None:
        if profile.household_income is None:
            missing_information.append("household_income")
            conditions_unverified.append(
                f"Annual income ceiling of ₹{rules.income_max:,} not yet verified."
            )
            follow_up_questions.append(
                f"What is your annual household income? (This scheme requires income under ₹{rules.income_max:,})"
            )
        elif profile.household_income > rules.income_max:
            conditions_failed.append(
                f"Income ceiling: annual household income ₹{profile.household_income:,} exceeds limit ₹{rules.income_max:,}."
            )
        else:
            conditions_satisfied.append(
                f"Annual household income ₹{profile.household_income:,} is within ceiling ₹{rules.income_max:,}."
            )

    # 5. Farmer criteria
    if rules.requires_farmer:
        if not profile.is_farmer:
            conditions_failed.append("Occupation requirement: scheme is strictly for active farmers.")
        else:
            conditions_satisfied.append("Applicant is verified as an active farmer.")
            if rules.max_landholding_acres is not None:
                if profile.landholding_acres is None:
                    missing_information.append("landholding_acres")
                    conditions_unverified.append(
                        f"Landholding ceiling of {rules.max_landholding_acres} acres not yet verified."
                    )
                    follow_up_questions.append(
                        "How many acres of agricultural land do you own or cultivate?"
                    )
                elif profile.landholding_acres > rules.max_landholding_acres:
                    conditions_failed.append(
                        f"Landholding ceiling: {profile.landholding_acres} acres exceeds maximum limit of {rules.max_landholding_acres} acres."
                    )
                else:
                    conditions_satisfied.append(
                        f"Landholding of {profile.landholding_acres} acres is within {rules.max_landholding_acres} acres limit."
                    )

    # 6. Residency type (Rural vs Urban)
    if rules.residency != "both":
        if profile.residency_type != rules.residency:
            conditions_failed.append(
                f"Location requirement: scheme requires {rules.residency} residency; applicant resides in an {profile.residency_type} area."
            )
        else:
            conditions_satisfied.append(f"Resides in {profile.residency_type} area as required.")

    # 7. Gender criteria
    if rules.target_genders:
        if profile.gender not in rules.target_genders and profile.gender != "all":
            conditions_failed.append(
                f"Target group: scheme is intended for {', '.join(rules.target_genders)}; applicant gender is {profile.gender}."
            )
        else:
            conditions_satisfied.append(f"Gender requirement satisfied ({profile.gender}).")

    # 8. Disability criteria
    if rules.requires_disability:
        if not profile.disability:
            conditions_failed.append("Scheme requires certified disability.")
        else:
            conditions_satisfied.append("Applicant has verified disability status.")

    # 9. Student criteria
    if rules.requires_student:
        if not profile.is_student:
            conditions_failed.append("Scheme requires active student enrollment.")
        else:
            conditions_satisfied.append("Applicant is an actively enrolled student.")

    # 10. Social category criteria
    if rules.allowed_social_categories:
        if profile.social_category not in rules.allowed_social_categories:
            conditions_failed.append(
                f"Social category restriction: requires {', '.join(rules.allowed_social_categories)}; applicant is {profile.social_category}."
            )
        else:
            conditions_satisfied.append(f"Social category {profile.social_category} is eligible.")

    # Resolve overall eligibility status
    if conditions_failed:
        status = "ineligible"
    elif missing_information:
        status = "insufficient_information"
    elif conditions_unverified or scheme.status == "under_review":
        status = "potentially_eligible"
    else:
        status = "likely_eligible"

    return EligibilityAssessment(
        scheme_id=scheme.scheme_id,
        scheme_name=scheme.name,
        status=status,
        conditions_satisfied=conditions_satisfied,
        conditions_failed=conditions_failed,
        conditions_unverified=conditions_unverified,
        missing_information=missing_information,
        follow_up_questions=follow_up_questions,
        uncertainty_flags=list(scheme.uncertainty_flags),
        verified_benefit=scheme.verified_benefit,
        verified_deadline=scheme.application_window.verified_deadline,
        official_portal_url=scheme.official_portal_url,
        last_verified_at=scheme.last_verified_at,
        disclaimer=DISCLAIMER_TEXT,
    )


def assess_all_schemes(
    profile: CitizenProfile,
    schemes: Optional[List[Scheme]] = None,
) -> List[EligibilityAssessment]:
    """Evaluates citizen against multiple schemes, sorted logically by eligibility tier."""
    if schemes is None:
        from app import db
        schemes = db.list_schemes()

    results: List[EligibilityAssessment] = []
    for s in schemes:
        results.append(assess_scheme_eligibility(profile, s))

    # Priority sort order: likely_eligible -> potentially_eligible -> insufficient_information -> ineligible
    priority_map = {
        "likely_eligible": 0,
        "potentially_eligible": 1,
        "insufficient_information": 2,
        "ineligible": 3,
    }
    results.sort(key=lambda r: priority_map.get(r.status, 99))
    return results
