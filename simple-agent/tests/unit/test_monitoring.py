"""Unit tests for Scheme Finder source monitor, change detection, and verification."""

import pytest
from app import db
from app.models import OfficialSource, Scheme, SchemeEligibilityRules
from app.monitor import (
    compute_content_hash,
    detect_differences,
    fetch_source_content,
    run_discovery_scan,
    verify_source_authority,
)


@pytest.mark.asyncio
async def test_compute_content_hash_normalization():
    """Confirms whitespace normalization produces identical SHA-256 fingerprints."""
    text1 = "Government extends PM-KISAN deadline to Nov 30."
    text2 = "  Government   extends   PM-KISAN   deadline  to  Nov 30.  \n"
    assert compute_content_hash(text1) == compute_content_hash(text2)


@pytest.mark.asyncio
async def test_inaccessible_source_graceful_handling():
    """Scenario 7: Inaccessible official website handles timeout/failure gracefully."""
    source = OfficialSource(
        source_id="mock-broken-source",
        name="Broken Government Server",
        url="https://invalid-official-domain-404-timeout.gov.in/feed.rss",
        source_type="rss",
        level="central",
        state="central",
    )
    status, content, error_msg = await fetch_source_content(source)
    assert status == "error"
    assert content is None
    assert "timeout" in error_msg.lower() or "failure" in error_msg.lower()


def test_verify_source_authority():
    """Validates approved government domain rules."""
    valid, flags = verify_source_authority("https://wcd.delhi.gov.in/scheme", "Govt of Delhi")
    assert valid is True
    assert len(flags) == 0

    invalid, flags = verify_source_authority("https://unverified-blog.com/schemes", "Unofficial Blog")
    assert invalid is False
    assert len(flags) > 0


def test_detect_differences_deadline():
    """Scenario 5: Detects changed deadline and produces structured diff."""
    scheme = Scheme(
        scheme_id="test-scheme-diff",
        name="Test Scheme",
        category="agriculture",
        ministry="Ministry of Agriculture",
        brief_description="Test",
        verified_benefit="Test benefit",
        eligibility_rules=SchemeEligibilityRules(age_min=18),
        official_portal_url="https://gov.in",
        source_url="https://myscheme.gov.in",
        source_authority="Govt of India",
    )
    scheme.application_window.verified_deadline = "2026-10-15"

    update_payload = {
        "verified_deadline": "2026-11-30",
        "evidence_snippet": "Official Gazette: Application window extended to November 30, 2026.",
    }
    diffs = detect_differences(scheme, update_payload)
    assert len(diffs) == 1
    assert diffs[0].change_type == "deadline_extended"
    assert diffs[0].old_value == "2026-10-15"
    assert diffs[0].new_value == "2026-11-30"


@pytest.mark.asyncio
async def test_discovery_new_scheme_and_duplicate_suppression():
    """Scenario 4 & 6: Newly announced scheme is stored; duplicate announcement is suppressed."""
    db.delete_scheme("test-pm-vishwakarma")

    announcement = {
        "scheme_id": "test-pm-vishwakarma",
        "name": "PM Vishwakarma Scheme",
        "category": "social_welfare",
        "level": "central",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "brief_description": "End-to-end support for traditional artisans and craftspeople.",
        "verified_benefit": "Collateral-free enterprise credit up to ₹3,00,000 at concessional 5% interest.",
        "benefit_amount_annual": 300000.0,
        "age_min": 18,
        "source_url": "https://pmvishwakarma.gov.in",
        "source_authority": "Ministry of MSME, Govt. of India",
        "raw_text": "PM Vishwakarma Scheme launched with collateral free credit.",
    }

    # First scan: discover new scheme
    log1 = await run_discovery_scan(source_ids=[], simulated_announcements=[announcement])
    assert len(log1.new_schemes_found) == 1
    assert log1.new_schemes_found[0]["scheme_id"] == "test-pm-vishwakarma"

    stored = db.get_scheme("test-pm-vishwakarma")
    assert stored is not None
    assert stored.status == "verified"

    # Second scan with duplicate announcement and recorded hash:
    announcement_dup = dict(announcement)
    announcement_dup["last_content_hash"] = compute_content_hash(announcement["raw_text"])

    log2 = await run_discovery_scan(source_ids=[], simulated_announcements=[announcement_dup])
    assert log2.duplicate_suppressed_count >= 1
    assert len(log2.new_schemes_found) == 0


@pytest.mark.asyncio
async def test_conflicting_eligibility_flagged_for_review():
    """Scenario 8 & 12: Scheme with conflicting information is flagged for review."""
    db.delete_scheme("conflicting-subsidy-test")

    announcement = {
        "scheme_id": "conflicting-subsidy-test",
        "name": "Conflicting Electric Pump Subsidy",
        "category": "agriculture",
        "level": "central",
        "ministry": "Ministry of Agriculture",
        "brief_description": "Subsidized electric pumps.",
        "verified_benefit": "Subsidy amount conflicting.",
        "has_conflicting_info": True,
        "source_url": "https://agricoop.gov.in/draft",
        "source_authority": "Ministry of Agriculture",
        "raw_text": "Draft notice with conflicting subsidy criteria.",
    }
    log = await run_discovery_scan(source_ids=[], simulated_announcements=[announcement])
    assert len(log.new_schemes_found) == 1
    scheme_found = log.new_schemes_found[0]
    assert scheme_found["status"] == "under_review"
    assert any("conflicting" in flag.lower() for flag in scheme_found["uncertainty_flags"])
