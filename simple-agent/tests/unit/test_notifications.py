"""Unit tests for Scheme Finder WhatsApp notification dispatcher and simulator."""

import pytest
from app import db
from app.models import CitizenProfile, Scheme, SchemeEligibilityRules
from app.whatsapp import (
    dispatch_whatsapp_notification,
    format_whatsapp_alert,
    handle_conversational_reply,
)


@pytest.fixture
def sample_citizen_opted_in() -> CitizenProfile:
    profile = CitizenProfile(
        citizen_id="test-cit-in",
        full_name="Rajesh Farmer",
        phone_number="+919123456780",
        whatsapp_opt_in=True,
        state="Maharashtra",
        age=40,
        household_income=100000,
        is_farmer=True,
        landholding_acres=2.0,
    )
    db.save_citizen_profile(profile)
    return profile


@pytest.fixture
def sample_citizen_opted_out() -> CitizenProfile:
    profile = CitizenProfile(
        citizen_id="test-cit-out",
        full_name="Meena Devi",
        phone_number="+919123456781",
        whatsapp_opt_in=False,
        state="Maharashtra",
        age=32,
        household_income=90000,
    )
    db.save_citizen_profile(profile)
    return profile


@pytest.fixture
def sample_scheme() -> Scheme:
    scheme = Scheme(
        scheme_id="test-pm-kisan-notif",
        name="PM-KISAN Income Support",
        category="agriculture",
        ministry="Ministry of Agriculture",
        brief_description="Support for farmers",
        verified_benefit="₹6,000 per year in 3 installments",
        eligibility_rules=SchemeEligibilityRules(age_min=18, requires_farmer=True),
        required_documents=["Aadhaar Card", "Land Record"],
        official_portal_url="https://pmkisan.gov.in",
        source_url="https://myscheme.gov.in",
        source_authority="Govt of India",
        status="verified",
    )
    db.save_scheme(scheme)
    return scheme


def test_format_whatsapp_alert(sample_citizen_opted_in, sample_scheme):
    """Verifies all required transparency fields are in the formatted alert."""
    body = format_whatsapp_alert(
        profile=sample_citizen_opted_in,
        scheme=sample_scheme,
        trigger_type="new_matching_scheme",
        uncertain_conditions=["Land registry verification pending"],
    )
    assert "PM-KISAN" in body
    assert "₹6,000" in body
    assert "Land registry verification pending" in body
    assert "Aadhaar Card" in body
    assert "https://pmkisan.gov.in" in body
    assert "Stop notifications" in body
    assert "Preliminary autonomous screening" in body


@pytest.mark.asyncio
async def test_opted_out_suppression(sample_citizen_opted_out, sample_scheme):
    """Scenario 10: Citizen opted out of notifications has message suppressed."""
    notif = await dispatch_whatsapp_notification(
        citizen_id=sample_citizen_opted_out.citizen_id,
        scheme_id=sample_scheme.scheme_id,
        trigger_type="new_matching_scheme",
    )
    assert notif.delivery_status == "opted_out_suppressed"
    assert "opted out" in notif.error_message.lower()


@pytest.mark.asyncio
async def test_development_simulator_routing(sample_citizen_opted_in, sample_scheme):
    """In absence of live WhatsApp credentials, simulator records message safely."""
    notif = await dispatch_whatsapp_notification(
        citizen_id=sample_citizen_opted_in.citizen_id,
        scheme_id=sample_scheme.scheme_id,
        trigger_type="new_matching_scheme",
        force_simulate=True,
    )
    assert notif.delivery_mode == "development_simulator"
    assert notif.delivery_status == "simulated"
    assert "PM-KISAN" in notif.message_body


@pytest.mark.asyncio
async def test_failed_notification_call(sample_citizen_opted_in, sample_scheme):
    """Scenario 11: Failed API call logs error without claiming delivery."""
    notif = await dispatch_whatsapp_notification(
        citizen_id=sample_citizen_opted_in.citizen_id,
        scheme_id=sample_scheme.scheme_id,
        trigger_type="new_matching_scheme",
        mock_api_failure=True,
    )
    assert notif.delivery_status == "failed"
    assert notif.delivery_mode == "real_cloud_api"
    assert "500" in notif.error_message or "error" in notif.error_message.lower()


@pytest.mark.asyncio
async def test_conversational_reply_stop():
    """Confirms conversational 'stop notifications' unsubscribes the citizen."""
    citizen = CitizenProfile(
        citizen_id="test-conv-stop",
        full_name="Sunil Rao",
        phone_number="+919888877777",
        whatsapp_opt_in=True,
        state="Maharashtra",
        age=30,
    )
    db.save_citizen_profile(citizen)

    reply = await handle_conversational_reply("+919888877777", "Stop notifications")
    assert "opted out" in reply.lower() or "unsubscribed" in reply.lower()

    updated = db.get_citizen_profile("test-conv-stop")
    assert updated.whatsapp_opt_in is False


@pytest.mark.asyncio
async def test_conversational_find_schemes(sample_citizen_opted_in, sample_scheme):
    """Confirms conversational 'find schemes for me' returns matching schemes."""
    reply = await handle_conversational_reply(
        sample_citizen_opted_in.phone_number,
        "Find schemes for me",
    )
    assert "PM-KISAN" in reply or "Top Verified Schemes" in reply
