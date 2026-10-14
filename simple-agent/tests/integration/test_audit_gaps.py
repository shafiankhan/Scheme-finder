"""Integration and edge-case tests addressing the technical audit gaps.

Covers:
1. Source-fetch failures (HTTP 500, network timeouts)
2. Malformed HTML / messy response payload handling
3. Stale data detection and freshness threshold verification
4. Repeated scheduler triggers and concurrency locking (HTTP 409)
5. Incomplete scheme criteria and uncertainty handling
6. Meta WhatsApp webhook GET handshake verification and security barrier
7. Meta WhatsApp webhook inbound payload ingestion
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx

from app import db
from app.api_routes import router
from app.eligibility import assess_scheme_eligibility
from app.fast_api_app import app
from app.models import (
    ApplicationWindow,
    CitizenProfile,
    OfficialSource,
    Scheme,
    SchemeEligibilityRules,
)
from app.monitor import (
    ScanInProgressError,
    _scan_lock,
    check_source_freshness,
    compute_content_hash,
    fetch_source_content,
    run_discovery_scan,
)

client = TestClient(app)


# =========================================================================
# 1. Source Fetch Failures: HTTP 500 & Network Timeouts
# =========================================================================

@pytest.mark.asyncio
async def test_source_fetch_failure_http500():
    """Verify that a source returning HTTP 500 is marked degraded and handled without crashing."""
    source = OfficialSource(
        source_id="mock-500-source",
        name="Mock Failing Portal",
        url="https://mock-failing-portal.gov.in/schemes",
        authority_level="state",
        check_interval_hours=24,
    )

    mock_resp = httpx.Response(status_code=500, request=httpx.Request("GET", source.url))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        status, content, err = await fetch_source_content(source)

        assert status == "degraded"
        assert content is None
        assert "HTTP 500" in err


@pytest.mark.asyncio
async def test_source_fetch_network_timeout():
    """Verify that a network timeout raises no unhandled exception and reports error status."""
    source = OfficialSource(
        source_id="mock-timeout-source",
        name="Mock Timing Out Portal",
        url="https://slow-server.gov.in/feed.rss",
        authority_level="central",
        check_interval_hours=48,
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Read timed out after 5.0s")
        status, content, err = await fetch_source_content(source)

        assert status == "error"
        assert content is None
        assert "Network exception: Read timed out" in err


# =========================================================================
# 2. Malformed Responses & Raw HTML Fingerprinting
# =========================================================================

def test_malformed_html_response_hash():
    """Verify that malformed or empty payloads yield stable, normalized SHA-256 fingerprints."""
    # Empty payload
    empty_hash = compute_content_hash("")
    assert isinstance(empty_hash, str) and len(empty_hash) == 64

    # Broken markup with unpredictable whitespace
    messy_html_1 = "<div><p>  Scheme   Deadline:   2026-12-31 \n\n </p></div>"
    messy_html_2 = "<div><p> Scheme Deadline: 2026-12-31 </p></div>"
    assert compute_content_hash(messy_html_1) == compute_content_hash(messy_html_2)


# =========================================================================
# 3. Stale Data Detection
# =========================================================================

def test_stale_data_detection():
    """Verify that sources exceeding their check interval are flagged as stale."""
    now = datetime.now(timezone.utc)
    
    # Fresh source: scanned 2 hours ago against a 24-hour interval
    fresh_source = OfficialSource(
        source_id="fresh-src",
        name="Fresh Source",
        url="https://fresh.gov.in",
        last_scanned_at=(now - timedelta(hours=2)).isoformat(),
        check_interval_hours=24,
    )
    assert check_source_freshness(fresh_source) is True

    # Stale source: scanned 48 hours ago against a 24-hour interval
    stale_source = OfficialSource(
        source_id="stale-src",
        name="Stale Source",
        url="https://stale.gov.in",
        last_scanned_at=(now - timedelta(hours=48)).isoformat(),
        check_interval_hours=24,
    )
    assert check_source_freshness(stale_source) is False

    # Unscanned source
    unscanned_source = OfficialSource(
        source_id="unscanned-src",
        name="Unscanned Source",
        url="https://unscanned.gov.in",
        last_scanned_at=None,
    )
    assert check_source_freshness(unscanned_source) is False


# =========================================================================
# 4. Repeated Scheduler Triggers & Concurrency Locking
# =========================================================================

@pytest.mark.asyncio
async def test_repeated_triggers_concurrency_lock():
    """Verify that overlapping or simultaneous scan invocations are blocked by the lock."""
    # Ensure lock is free before test
    if _scan_lock.locked():
        _scan_lock.release()

    # Simulate an active scan holding the lock
    async with _scan_lock:
        with pytest.raises(ScanInProgressError) as exc_info:
            await run_discovery_scan()
        assert "A discovery scan is already active" in str(exc_info.value)


def test_api_trigger_scan_returns_409_when_locked():
    """Verify the REST endpoint returns HTTP 409 Conflict when a scan is in progress."""
    async def simulate_locked_call():
        async with _scan_lock:
            # While the lock is acquired, call the API endpoint synchronously via TestClient
            response = client.post("/api/sources/scan")
            assert response.status_code == 409
            data = response.json()
            assert "A discovery scan is already active" in data["detail"]

    asyncio.run(simulate_locked_call())


# =========================================================================
# 5. Incomplete Scheme Criteria & Uncertainty Handling
# =========================================================================

def test_incomplete_scheme_criteria_handling():
    """Verify that a scheme with unstated/incomplete criteria returns uncertainty flags."""
    incomplete_scheme = Scheme(
        scheme_id="incomplete-pilot-scheme",
        name="Pilot Incomplete Scheme",
        version="0.1.0",
        category="agriculture",
        level="central",
        ministry="Ministry of Agriculture",
        brief_description="Draft scheme with unverified criteria.",
        verified_benefit="Pending final gazette publication.",
        eligibility_rules=SchemeEligibilityRules(
            age_min=None,
            age_max=None,
            income_max=None,
            requires_farmer=True,
            allowed_states=None,
        ),
        required_documents=["Aadhaar Card"],
        official_portal_url="https://gov.in",
        source_url="https://myscheme.gov.in/schemes/pilot",
        source_authority="Government of India",
        uncertainty_flags=["Income limit and age criteria not yet gazetted."],
        status="under_review",
    )

    citizen = CitizenProfile(
        citizen_id="citizen-eval-incomplete",
        full_name="Mohan Lal",
        phone_number="+919876543210",
        age=40,
        state="Haryana",
        household_income=150000,
        is_farmer=True,
        landholding_acres=2.5,
    )

    assessment = assess_scheme_eligibility(citizen, incomplete_scheme)
    # Status should be under review / potentially eligible, carrying the uncertainty flag
    assert len(assessment.uncertainty_flags) >= 1
    assert "Income limit and age criteria not yet gazetted." in assessment.uncertainty_flags
    assert assessment.status in ("potentially_eligible", "likely_eligible")


# =========================================================================
# 6. Meta WhatsApp Webhook Handshake & Verification
# =========================================================================

def test_meta_webhook_get_handshake_success():
    """Verify GET challenge handshake succeeds with the correct verify token."""
    verify_token = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "scheme_finder_verify_token")
    response = client.get(
        "/api/notifications/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": verify_token,
            "hub.challenge": "1948209123",
        },
    )
    assert response.status_code == 200
    assert response.text == "1948209123"


def test_meta_webhook_get_handshake_invalid_token():
    """Verify GET handshake returns HTTP 403 on invalid verify token."""
    response = client.get(
        "/api/notifications/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "invalid_wrong_token_12345",
            "hub.challenge": "1948209123",
        },
    )
    assert response.status_code == 403
    assert "Verification token mismatch" in response.json()["detail"]


def test_meta_webhook_inbound_message_processing():
    """Verify POST webhook properly extracts and processes inbound conversational message."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "104928392",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550239482",
                                "phone_number_id": "1062948201",
                            },
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.HBgLMTE...",
                                    "timestamp": "1728800000",
                                    "text": {"body": "help"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = client.post("/api/notifications/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed"] == 1
    assert len(data["replies"]) == 1
    assert "Scheme Finder" in data["replies"][0]["reply"]
