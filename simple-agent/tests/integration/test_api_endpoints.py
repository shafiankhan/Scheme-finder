"""Integration tests for Scheme Finder REST APIs and Dashboard routes."""

import pytest
from fastapi.testclient import TestClient

from app.fast_api_app import app
from app import db


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_health_endpoint(client):
    """GET /api/health returns 200 OK and healthy status."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "scheme-finder"


def test_api_citizens_endpoints(client):
    """GET /api/citizens and GET /api/citizens/{id} return valid citizen data."""
    resp = client.get("/api/citizens")
    assert resp.status_code == 200
    citizens = resp.json()
    assert len(citizens) >= 1
    assert any(c["full_name"] == "Ramesh Patel" for c in citizens)

    # Specific citizen
    r2 = client.get("/api/citizens/citizen-001")
    assert r2.status_code == 200
    assert r2.json()["full_name"] == "Ramesh Patel"


def test_api_schemes_endpoints(client):
    """GET /api/schemes returns verified schemes with benefits."""
    resp = client.get("/api/schemes")
    assert resp.status_code == 200
    schemes = resp.json()
    assert len(schemes) >= 5
    assert any(s["scheme_id"] == "pm-kisan" for s in schemes)


def test_api_eligibility_assessment(client):
    """POST /api/eligibility/assess returns deterministic assessment and statutory disclaimer."""
    resp = client.post(
        "/api/eligibility/assess",
        json={"citizen_id": "citizen-001", "scheme_id": "pm-kisan"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "assessment" in data
    assessment = data["assessment"]
    assert assessment["status"] == "likely_eligible"
    assert "preliminary screening" in assessment["disclaimer"].lower()
    assert len(assessment["conditions_satisfied"]) >= 1


def test_api_deadlines_endpoint(client):
    """GET /api/deadlines returns active upcoming deadlines, excluding expired schemes."""
    resp = client.get("/api/deadlines")
    assert resp.status_code == 200
    deadlines = resp.json()
    assert isinstance(deadlines, list)
    # Ensure expired covid relief is not present
    assert not any(d["scheme_id"] == "expired-covid-relief" for d in deadlines)


def test_api_sources_and_logs(client):
    """GET /api/sources and GET /api/sources/logs return valid official tracking data."""
    r_sources = client.get("/api/sources")
    assert r_sources.status_code == 200
    assert len(r_sources.json()) >= 1

    r_logs = client.get("/api/sources/logs")
    assert r_logs.status_code == 200
    assert isinstance(r_logs.json(), list)


def test_api_notifications_and_chat_simulator(client):
    """POST /api/notifications/chat handles inbound WhatsApp simulated replies."""
    payload = {
        "phone_number": "+919876543210",
        "message": "find schemes for me",
    }
    resp = client.post("/api/notifications/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_dashboard_html_served(client):
    """GET /dashboard serves the comprehensive 9-section HTML UI."""
    r_dash = client.get("/dashboard")
    assert r_dash.status_code == 200
    assert "Scheme Finder" in r_dash.text
    assert "A2UI" in r_dash.text
    assert "Ramesh Patel" in r_dash.text
