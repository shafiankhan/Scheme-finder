"""Unit tests for Scheme Finder deterministic eligibility engine."""

import pytest
from app.eligibility import assess_scheme_eligibility
from app.models import (
    ApplicationWindow,
    CitizenProfile,
    Scheme,
    SchemeEligibilityRules,
)


@pytest.fixture
def sample_pm_kisan() -> Scheme:
    return Scheme(
        scheme_id="pm-kisan",
        name="Pradhan Mantri Kisan Samman Nidhi",
        category="agriculture",
        ministry="Ministry of Agriculture",
        brief_description="Income support for farmers",
        verified_benefit="₹6,000 per year",
        eligibility_rules=SchemeEligibilityRules(
            age_min=18,
            requires_farmer=True,
            max_landholding_acres=5.0,
            income_max=300000,
        ),
        official_portal_url="https://pmkisan.gov.in",
        source_url="https://myscheme.gov.in",
        source_authority="Govt of India",
        application_window=ApplicationWindow(status="open"),
        status="verified",
    )


@pytest.fixture
def sample_delhi_ladli() -> Scheme:
    return Scheme(
        scheme_id="delhi-ladli",
        name="Delhi Ladli Scheme",
        category="women",
        level="state",
        state_name="Delhi",
        ministry="WCD Delhi",
        brief_description="Girl child assistance",
        verified_benefit="₹10,000 grant",
        eligibility_rules=SchemeEligibilityRules(
            age_max=18,
            income_max=100000,
            allowed_states=["Delhi"],
            target_genders=["female"],
        ),
        official_portal_url="https://wcd.delhi.gov.in",
        source_url="https://edistrict.delhigovt.nic.in",
        source_authority="Govt of NCT Delhi",
        application_window=ApplicationWindow(status="open", verified_deadline="2026-10-31"),
        status="verified",
    )


def test_eligible_citizen(sample_pm_kisan):
    """Scenario 1: Citizen meets all conditions."""
    profile = CitizenProfile(
        citizen_id="c1",
        full_name="Ramesh Farmer",
        phone_number="+919999999999",
        state="Maharashtra",
        age=45,
        household_income=120000,
        is_farmer=True,
        landholding_acres=2.5,
    )
    result = assess_scheme_eligibility(profile, sample_pm_kisan)
    assert result.status == "likely_eligible"
    assert len(result.conditions_failed) == 0
    assert len(result.conditions_satisfied) >= 3
    assert "₹6,000" in result.verified_benefit


def test_ineligible_due_to_income(sample_pm_kisan):
    """Scenario 2: Citizen fails mandatory income condition."""
    profile = CitizenProfile(
        citizen_id="c2",
        full_name="Rich Farmer",
        phone_number="+919999999999",
        state="Maharashtra",
        age=45,
        household_income=900000,  # Exceeds 300,000
        is_farmer=True,
        landholding_acres=3.0,
    )
    result = assess_scheme_eligibility(profile, sample_pm_kisan)
    assert result.status == "ineligible"
    assert any("exceeds limit" in c for c in result.conditions_failed)


def test_ineligible_due_to_state(sample_delhi_ladli):
    """Citizen resides in different state than allowed."""
    profile = CitizenProfile(
        citizen_id="c3",
        full_name="Pooja",
        phone_number="+919999999999",
        state="Haryana",  # Not Delhi
        age=12,
        gender="female",
        household_income=80000,
    )
    result = assess_scheme_eligibility(profile, sample_delhi_ladli)
    assert result.status == "ineligible"
    assert any("requires state in Delhi" in c for c in result.conditions_failed)


def test_insufficient_information_missing_income(sample_pm_kisan):
    """Scenario 3: Profile missing income triggers follow-up question."""
    profile = CitizenProfile(
        citizen_id="c4",
        full_name="Unknown Income Farmer",
        phone_number="+919999999999",
        state="Maharashtra",
        age=35,
        household_income=None,  # Missing
        is_farmer=True,
        landholding_acres=2.0,
    )
    result = assess_scheme_eligibility(profile, sample_pm_kisan)
    assert result.status == "insufficient_information"
    assert "household_income" in result.missing_information
    assert len(result.follow_up_questions) > 0
    assert "income" in result.follow_up_questions[0].lower()


def test_expired_scheme_ineligible():
    """Scenario 9: Expired scheme must not be presented as open."""
    expired_scheme = Scheme(
        scheme_id="old-relief",
        name="Past Relief Scheme",
        category="social_welfare",
        ministry="Ministry of Finance",
        brief_description="Emergency expired grant",
        verified_benefit="₹10,000",
        eligibility_rules=SchemeEligibilityRules(age_min=18),
        official_portal_url="https://finmin.gov.in",
        source_url="https://pib.gov.in",
        source_authority="Govt of India",
        application_window=ApplicationWindow(status="expired", verified_deadline="2021-12-31"),
        status="expired",
    )
    profile = CitizenProfile(
        citizen_id="c5",
        full_name="Eligible User",
        phone_number="+919999999999",
        state="Delhi",
        age=30,
        household_income=50000,
    )
    result = assess_scheme_eligibility(profile, expired_scheme)
    assert result.status == "ineligible"
    assert any("expired" in c for c in result.conditions_failed)
