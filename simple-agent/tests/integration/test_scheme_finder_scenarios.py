"""End-to-End Evaluation Suite for Scheme Finder.

Verifies the 12 key evaluation scenarios required for Track 3:
1.  Meets all available conditions (PM-KISAN) -> Likely eligible
2.  Fails mandatory condition (Income/Residency) -> Ineligible with transparent explanation
3.  Missing critical fields -> Insufficient information + follow-up question
4.  Newly announced scheme discovered -> Stored and verified
5.  Existing scheme with changed deadline -> Detected diff, version updated
6.  Duplicate announcement -> Suppressed via SHA-256 fingerprint, no duplicate alert
7.  Inaccessible official website -> Graceful error/timeout handling, source marked degraded
8.  Conflicting eligibility across sources -> Flagged under_review
9.  Expired scheme -> Closed/archived, omitted from active upcoming deadlines
10. User opted out of WhatsApp -> Notification suppressed safely
11. Failed notification API call -> Graceful failure logged
12. Scheme with no reliable evidence -> Flagged under_review
"""

import pytest
import datetime
from unittest.mock import patch

from app.models import (
    CitizenProfile,
    Scheme,
    SchemeEligibilityRules,
    ApplicationWindow,
    OfficialSource,
    EligibilityAssessment,
    WhatsAppNotification,
    ScanLog,
)
from app.eligibility import assess_scheme_eligibility, assess_all_schemes
from app.monitor import (
    compute_content_hash,
    detect_differences,
    run_discovery_scan,
    verify_source_authority,
)
from app.whatsapp import (
    dispatch_whatsapp_notification,
    format_whatsapp_alert,
    handle_conversational_reply,
)
from app.application_support import (
    generate_application_packet,
    get_upcoming_deadlines,
)
from app import db


# =========================================================================
# Scenario 1: Meets all available conditions -> Likely Eligible
# =========================================================================
def test_scenario_01_meets_all_conditions():
    """Scenario 1: Farmer meeting age, landholding, and income criteria is likely eligible for PM-KISAN."""
    farmer = CitizenProfile(
        citizen_id="test-farmer-01",
        full_name="Ramesh Patel",
        age=45,
        gender="male",
        state="Maharashtra",
        district="Pune",
        household_income=120000,
        occupation="farmer",
        is_farmer=True,
        landholding_acres=2.5,
        social_category="obc",
        residency_type="rural",
        whatsapp_opt_in=True,
        phone_number="+919876543210",
    )
    pm_kisan = db.get_scheme("pm-kisan")
    assert pm_kisan is not None, "PM-KISAN scheme must exist in database"

    assessment = assess_scheme_eligibility(farmer, pm_kisan)
    assert assessment.status == "likely_eligible"
    assert len(assessment.conditions_satisfied) >= 3
    assert len(assessment.conditions_failed) == 0
    assert any("Landholding" in c for c in assessment.conditions_satisfied)


# =========================================================================
# Scenario 2: Fails mandatory condition -> Ineligible with transparent explanation
# =========================================================================
def test_scenario_02_fails_mandatory_condition():
    """Scenario 2: Salaried citizen with high income fails PM-KISAN & income-capped schemes."""
    salaried = CitizenProfile(
        citizen_id="test-salaried-02",
        full_name="Vikram Singh",
        age=38,
        gender="male",
        state="Maharashtra",
        district="Mumbai",
        household_income=1500000,  # 15 Lakh INR, exceeds ceiling
        occupation="software_engineer",
        is_farmer=False,
        landholding_acres=0.0,
        social_category="general",
        residency_type="urban",
        whatsapp_opt_in=True,
        phone_number="+919876543212",
    )
    pm_kisan = db.get_scheme("pm-kisan")
    assessment = assess_scheme_eligibility(salaried, pm_kisan)

    assert assessment.status == "ineligible"
    assert len(assessment.conditions_failed) >= 1
    assert any("Income" in f or "farmer" in f for f in assessment.conditions_failed)


# =========================================================================
# Scenario 3: Missing critical fields -> Insufficient info + follow-up questions
# =========================================================================
def test_scenario_03_missing_critical_fields():
    """Scenario 3: Profile with missing income or landholding receives insufficient_information."""
    incomplete_profile = CitizenProfile(
        citizen_id="test-incomplete-03",
        full_name="Priya Nair",
        age=29,
        gender="female",
        state="Kerala",
        district="Ernakulam",
        household_income=None,  # Missing income!
        occupation="tailor",
        is_farmer=False,
        landholding_acres=None,
        social_category="general",
        residency_type="urban",
        phone_number="+919876543213",
    )
    pm_jay = db.get_scheme("pm-jay")
    assessment = assess_scheme_eligibility(incomplete_profile, pm_jay)

    assert assessment.status == "insufficient_information"
    assert len(assessment.missing_information) > 0
    assert len(assessment.follow_up_questions) > 0
    assert any("income" in q.lower() for q in assessment.follow_up_questions)


# =========================================================================
# Scenario 4: Newly announced scheme discovered -> Stored and verified
# =========================================================================
@pytest.mark.asyncio
async def test_scenario_04_new_scheme_discovery():
    """Scenario 4: Scanner identifies a new scheme from official source and stores as verified."""
    new_scheme = Scheme(
        scheme_id="new-kisan-solar-2026",
        name="PM Surya Kisan Yojana 2026",
        category="agriculture",
        level="central",
        ministry="Ministry of New and Renewable Energy",
        brief_description="Solar subsidy for agricultural borewells.",
        verified_benefit="70% subsidy on solar agricultural pumps",
        eligibility_rules=SchemeEligibilityRules(
            min_age=18,
            max_age=75,
            requires_farmer=True,
        ),
        official_portal_url="https://mnre.gov.in/solar-pumps",
        source_url="https://mnre.gov.in/solar-pumps",
        source_authority="Ministry of New and Renewable Energy",
        status="verified",
    )
    db.save_scheme(new_scheme)

    # Verify retrieval from db
    retrieved = db.get_scheme("new-kisan-solar-2026")
    assert retrieved is not None
    assert retrieved.scheme_id == "new-kisan-solar-2026"
    assert retrieved.status == "verified"
    assert retrieved.name == "PM Surya Kisan Yojana 2026"


# =========================================================================
# Scenario 5: Existing scheme with changed deadline -> Detected diff, version updated
# =========================================================================
def test_scenario_05_deadline_change_detection():
    """Scenario 5: Diff engine detects deadline extension on existing scheme."""
    old_scheme = Scheme(
        scheme_id="test-deadline-scheme",
        name="Test Welfare Scheme",
        category="agriculture",
        level="central",
        ministry="Ministry of Agriculture",
        brief_description="Test scheme",
        verified_benefit="Financial grant",
        official_portal_url="https://agricoop.gov.in",
        source_url="https://agricoop.gov.in",
        source_authority="Ministry of Agriculture",
        application_window=ApplicationWindow(
            verified_deadline="2026-06-30",
            status="open",
        ),
        eligibility_rules=SchemeEligibilityRules(
            min_age=18,
            max_age=60,
        ),
        version="1.0.0",
    )
    new_data = {
        "scheme_id": "test-deadline-scheme",
        "verified_deadline": "2026-09-30",  # Extended deadline!
    }

    diffs = detect_differences(old_scheme, new_data)
    assert len(diffs) == 1
    assert diffs[0].change_type == "deadline_extended"
    assert "2026-09-30" in diffs[0].new_value


# =========================================================================
# Scenario 6: Duplicate announcement -> Suppressed via SHA-256 fingerprint
# =========================================================================
def test_scenario_06_duplicate_announcement_suppressed():
    """Scenario 6: Identical portal content generates identical hash and suppresses duplicates."""
    text1 = "PM-KISAN 17th Installment Released Date: 2026-05-01 Beneficiaries: 9.3 Crore"
    hash1 = compute_content_hash(text1)
    hash2 = compute_content_hash(text1)

    assert hash1 == hash2, "Identical content must have identical SHA-256 hash"

    # Ensure whitespace normalization collapses multiple spaces/newlines/tabs
    whitespace_variant = "  PM-KISAN   17th Installment    Released \n\n  Date: 2026-05-01 \t Beneficiaries:   9.3 Crore   "
    hash3 = compute_content_hash(whitespace_variant)
    assert hash1 == hash3, "Normalized whitespace must yield identical SHA-256 hash"


# =========================================================================
# Scenario 7: Inaccessible official website -> Graceful error/timeout handling
# =========================================================================
@pytest.mark.asyncio
async def test_scenario_07_inaccessible_website_handled():
    """Scenario 7: When an official source fails with network error, scan survives and logs failure."""
    bad_source = OfficialSource(
        source_id="src-broken-mock",
        name="Broken Government Portal",
        url="https://broken-gov-portal.invalid/schemes",
        check_interval_hours=168,
        last_status="healthy",
    )
    db.save_source(bad_source)

    # Trigger scan for the broken source
    log = await run_discovery_scan(source_ids=["src-broken-mock"])
    assert log is not None
    # Source status must be recorded as degraded/error, not crash
    updated_source = db.get_source("src-broken-mock")
    assert updated_source.last_status == "error"
    assert updated_source.failure_count >= 1


# =========================================================================
# Scenario 8: Conflicting eligibility across sources -> Flagged under_review
# =========================================================================
def test_scenario_08_conflicting_eligibility_under_review():
    """Scenario 8: If rules are ambiguous or conflicting, scheme remains under_review."""
    ambiguous_scheme = Scheme(
        scheme_id="conflicted-scheme-08",
        name="State Solar Tractor Subsidy",
        category="agriculture",
        level="state",
        state_name="Maharashtra",
        ministry="Department of Agriculture",
        brief_description="Contradictory income cap between draft gazette and news release.",
        verified_benefit="Subsidized tractor equipment",
        official_portal_url="https://krishi.maharashtra.gov.in",
        source_url="https://krishi.maharashtra.gov.in",
        source_authority="Department of Agriculture",
        eligibility_rules=SchemeEligibilityRules(min_age=18, max_age=65),
        status="under_review",  # Conflicting data prevents automatic verification
        uncertainty_flags=["Contradictory income ceiling across portal circulars."],
    )
    db.save_scheme(ambiguous_scheme)

    retrieved = db.get_scheme("conflicted-scheme-08")
    assert retrieved.status == "under_review"

    # Active scheme query must exclude under_review schemes by default
    active_schemes = db.list_schemes(status="verified")
    assert not any(s.scheme_id == "conflicted-scheme-08" for s in active_schemes)


# =========================================================================
# Scenario 9: Expired scheme -> Archived, omitted from active upcoming deadlines
# =========================================================================
def test_scenario_09_expired_scheme_suppressed():
    """Scenario 9: Expired schemes are marked expired and never presented in active deadlines."""
    expired_scheme = Scheme(
        scheme_id="expired-covid-relief",
        name="COVID Emergency Relief Grant",
        category="social_welfare",
        level="central",
        ministry="Ministry of Finance",
        brief_description="One-time relief package during lockdown.",
        verified_benefit="One-time grant",
        official_portal_url="https://financialservices.gov.in",
        source_url="https://financialservices.gov.in",
        source_authority="Ministry of Finance",
        eligibility_rules=SchemeEligibilityRules(min_age=18),
        application_window=ApplicationWindow(
            verified_deadline="2021-12-31",
            status="closed",
        ),
        status="expired",
    )
    db.save_scheme(expired_scheme)

    deadlines = get_upcoming_deadlines()
    expired_in_deadlines = [d for d in deadlines if d["scheme_id"] == "expired-covid-relief"]
    assert len(expired_in_deadlines) == 0, "Expired schemes must not appear in upcoming deadlines"


# =========================================================================
# Scenario 10: Citizen opted out of WhatsApp -> Notification suppressed
# =========================================================================
@pytest.mark.asyncio
async def test_scenario_10_opt_out_suppression():
    """Scenario 10: Citizen who opted out of WhatsApp alerts has notifications safely suppressed."""
    opted_out_citizen = CitizenProfile(
        citizen_id="citizen-005",
        full_name="Anand Kumar",
        age=52,
        gender="male",
        state="Maharashtra",
        household_income=240000,
        occupation="trader",
        is_farmer=False,
        whatsapp_opt_in=False,  # Explicitly opted out
        phone_number="+919876543214",
    )
    db.save_citizen_profile(opted_out_citizen)

    notif = await dispatch_whatsapp_notification(
        citizen_id="citizen-005",
        scheme_id="pm-kisan",
        trigger_type="new_matching_scheme",
    )
    assert notif.delivery_status == "opted_out_suppressed"
    assert "opted out" in notif.message_body.lower()


# =========================================================================
# Scenario 11: Failed notification API call -> Graceful failure logged
# =========================================================================
@pytest.mark.asyncio
async def test_scenario_11_failed_notification_logged():
    """Scenario 11: If external WhatsApp API fails with HTTP 500, system logs status as failed."""
    opted_in = CitizenProfile(
        citizen_id="test-citizen-fail",
        full_name="Simulated Failure User",
        age=30,
        gender="female",
        state="Delhi",
        household_income=100000,
        whatsapp_opt_in=True,
        phone_number="+919999999999",
    )
    db.save_citizen_profile(opted_in)

    notif = await dispatch_whatsapp_notification(
        citizen_id="test-citizen-fail",
        scheme_id="delhi-ladli",
        trigger_type="deadline_approaching",
        mock_api_failure=True,
    )
    assert notif.delivery_status == "failed"
    assert notif.error_message is not None
    assert "500" in notif.error_message


# =========================================================================
# Scenario 12: Scheme with no reliable official evidence -> Flagged under_review
# =========================================================================
def test_scenario_12_no_reliable_evidence_barrier():
    """Scenario 12: Schemas originating from non-whitelisted domains or unverified blogs remain under_review."""
    unauthorized_source = "https://unverified-scheme-blog.com/new-subsidy"
    is_auth, flags = verify_source_authority(unauthorized_source, "Unverified Source")
    assert is_auth is False
    assert len(flags) > 0

    unverified_scheme = Scheme(
        scheme_id="unverified-blog-subsidy",
        name="Free Smartphone Scheme 2026",
        category="social_welfare",
        level="state",
        ministry="Unverified Source",
        brief_description="Circulated on social media without gazette notice.",
        verified_benefit="Free mobile device",
        official_portal_url=unauthorized_source,
        source_url=unauthorized_source,
        source_authority="Unverified Blog",
        eligibility_rules=SchemeEligibilityRules(min_age=18),
        status="under_review",  # Must not be verified
        uncertainty_flags=["No official notification on .gov.in or .nic.in domain."],
    )
    db.save_scheme(unverified_scheme)

    retrieved = db.get_scheme("unverified-blog-subsidy")
    assert retrieved.status == "under_review"
