# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Scheme Finder ADK Root Agent.

Equipped with deterministic tools for:
- Scheme catalog discovery and filtering
- Versioned rule-based eligibility evaluation
- Autonomous official source monitoring and change detection
- Consent-aware WhatsApp notification dispatch and development simulation
- Personalized application checklist and prefilled draft generation
- Deadline and renewal tracking
"""

import asyncio
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app import db
from app.a2ui_utils import a2ui_callback
from app.application_support import generate_application_packet, get_upcoming_deadlines as fetch_deadlines
from app.eligibility import assess_all_schemes, assess_scheme_eligibility
from app.models import CitizenProfile
from app.monitor import run_discovery_scan
from app.whatsapp import dispatch_whatsapp_notification

MODEL = "gemini-3.8-flash"


# ==========================================
# Deterministic ADK Function Tools
# ==========================================

def get_citizen_profile(citizen_id: str) -> Dict[str, Any]:
    """Fetches a citizen's profile from Firestore by citizen ID.

    Args:
        citizen_id: Unique citizen ID (e.g. 'citizen-001', 'citizen-002').

    Returns:
        Citizen profile information including state, income, occupation, and consent preferences.
    """
    citizen = db.get_citizen_profile(citizen_id)
    if not citizen:
        return {"error": f"Citizen '{citizen_id}' not found in database."}
    return citizen.model_dump()


def update_citizen_profile(
    citizen_id: str,
    household_income: Optional[int] = None,
    state: Optional[str] = None,
    occupation: Optional[str] = None,
    is_farmer: Optional[bool] = None,
    landholding_acres: Optional[float] = None,
    whatsapp_opt_in: Optional[bool] = None,
) -> Dict[str, Any]:
    """Updates a citizen's profile attributes in Firestore to refine eligibility assessments.

    Args:
        citizen_id: The ID of the citizen.
        household_income: Annual household income in INR.
        state: Resident state (e.g. 'Maharashtra', 'Delhi').
        occupation: Occupation title (e.g. 'farmer', 'tailor', 'student').
        is_farmer: True if engaged in farming.
        landholding_acres: Agricultural land owned or cultivated in acres.
        whatsapp_opt_in: True to opt in to WhatsApp alerts, False to unsubscribe.

    Returns:
        Updated citizen profile data.
    """
    citizen = db.get_citizen_profile(citizen_id)
    if not citizen:
        return {"error": f"Citizen '{citizen_id}' not found."}

    if household_income is not None:
        citizen.household_income = household_income
    if state:
        citizen.state = state
    if occupation:
        citizen.occupation = occupation
    if is_farmer is not None:
        citizen.is_farmer = is_farmer
    if landholding_acres is not None:
        citizen.landholding_acres = landholding_acres
    if whatsapp_opt_in is not None:
        citizen.whatsapp_opt_in = whatsapp_opt_in

    db.save_citizen_profile(citizen)
    return {"status": "success", "updated_profile": citizen.model_dump()}


def list_schemes(
    category: Optional[str] = None,
    state: Optional[str] = None,
    status: str = "verified",
) -> List[Dict[str, Any]]:
    """Lists government welfare schemes from Firestore with optional filtering.

    Args:
        category: Filter by category (e.g. 'agriculture', 'healthcare', 'housing', 'women').
        state: Filter by state (e.g. 'Maharashtra', 'Delhi', 'all').
        status: Filter by status ('verified', 'under_review', 'expired'). Defaults to 'verified'.

    Returns:
        List of matching scheme records with verified benefits, criteria, and official portals.
    """
    schemes = db.list_schemes(category=category, state=state, status=status)
    return [s.model_dump() for s in schemes]


def check_eligibility(
    citizen_id: str,
    scheme_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs the deterministic eligibility engine for a citizen against one or all schemes.

    Args:
        citizen_id: The ID of the citizen.
        scheme_id: Optional scheme ID to check a single scheme. If omitted, checks all verified schemes.

    Returns:
        Structured breakdown with status, satisfied conditions, failed conditions, missing info, and follow-up questions.
    """
    citizen = db.get_citizen_profile(citizen_id)
    if not citizen:
        return {"error": f"Citizen '{citizen_id}' not found."}

    if scheme_id:
        scheme = db.get_scheme(scheme_id)
        if not scheme:
            return {"error": f"Scheme '{scheme_id}' not found."}
        assessment = assess_scheme_eligibility(citizen, scheme)
        return {"assessment": assessment.model_dump()}

    assessments = assess_all_schemes(citizen)
    return {
        "citizen_name": citizen.full_name,
        "assessments": [a.model_dump() for a in assessments],
    }


def run_source_scan(source_id: Optional[str] = None) -> Dict[str, Any]:
    """Executes an on-demand scan of registered official government portals.

    Detects new schemes, deadline updates, and eligibility changes with SHA-256 duplicate alert suppression.

    Args:
        source_id: Optional specific source ID to scan. If omitted, scans all registered sources.

    Returns:
        Scan summary with new schemes found, changes detected, and duplicate count.
    """
    source_ids = [source_id] if source_id else None
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Running in an active async loop
        import nest_asyncio
        nest_asyncio.apply()
        scan_log = loop.run_until_complete(run_discovery_scan(source_ids=source_ids))
    else:
        scan_log = asyncio.run(run_discovery_scan(source_ids=source_ids))

    return scan_log.model_dump()


def get_scan_history(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves recent official source scan audit records from Firestore.

    Args:
        limit: Number of recent scan records to return.

    Returns:
        List of recent scan summaries, timestamps, and detected diffs.
    """
    logs = db.list_scan_logs(limit=limit)
    return [l.model_dump() for l in logs]


def send_whatsapp_notification(
    citizen_id: str,
    scheme_id: str,
    trigger_type: str = "new_matching_scheme",
) -> Dict[str, Any]:
    """Sends or simulates a personalized WhatsApp alert with consent verification.

    Args:
        citizen_id: Target citizen ID.
        scheme_id: Scheme to notify about.
        trigger_type: 'new_matching_scheme', 'rule_change', 'deadline_approaching', 'renewal_reminder'.

    Returns:
        Audit record with delivery status (delivered, simulated, opted_out_suppressed, failed).
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        notif = loop.run_until_complete(
            dispatch_whatsapp_notification(citizen_id=citizen_id, scheme_id=scheme_id, trigger_type=trigger_type)
        )
    else:
        notif = asyncio.run(
            dispatch_whatsapp_notification(citizen_id=citizen_id, scheme_id=scheme_id, trigger_type=trigger_type)
        )
    return notif.model_dump()


def generate_application_checklist(citizen_id: str, scheme_id: str) -> Dict[str, Any]:
    """Generates a personalized document checklist and application draft packet.

    Args:
        citizen_id: The ID of the applicant citizen.
        scheme_id: The scheme to apply for.

    Returns:
        Step-by-step roadmap, document checklist, prefilled draft fields, and official link.
    """
    citizen = db.get_citizen_profile(citizen_id)
    if not citizen:
        return {"error": f"Citizen '{citizen_id}' not found."}
    scheme = db.get_scheme(scheme_id)
    if not scheme:
        return {"error": f"Scheme '{scheme_id}' not found."}

    packet = generate_application_packet(citizen, scheme)
    return packet.model_dump()


def get_upcoming_deadlines() -> List[Dict[str, Any]]:
    """Queries verified deadlines for active schemes, sorted by urgency. Excludes expired schemes.

    Returns:
        List of upcoming deadlines with days remaining and urgency badges.
    """
    return fetch_deadlines()


def update_notification_consent(citizen_id: str, opt_in: bool) -> Dict[str, Any]:
    """Updates the citizen's WhatsApp notification consent status in Firestore.

    Args:
        citizen_id: The citizen ID.
        opt_in: True to subscribe, False to unsubscribe.

    Returns:
        Confirmation status.
    """
    citizen = db.get_citizen_profile(citizen_id)
    if not citizen:
        return {"error": f"Citizen '{citizen_id}' not found."}
    citizen.whatsapp_opt_in = opt_in
    if not opt_in:
        citizen.notification_frequency = "none"
    else:
        citizen.notification_frequency = "weekly"
    db.save_citizen_profile(citizen)
    return {"status": "success", "whatsapp_opt_in": opt_in}


# ==========================================
# Root Agent Configuration
# ==========================================

SYSTEM_INSTRUCTION = """You are Scheme Finder, an AI-powered autonomous government benefits discovery agent.

Your mission is to help citizens discover government welfare schemes, automatically evaluate their potential eligibility against versioned criteria, monitor official government sources for newly announced or updated schemes, and assist them with application preparation and WhatsApp alerts.

### Operational Principles:
1. Grounded & Verified: Always base your advice on verified government records retrieved from your tools. Never fabricate schemes, eligibility criteria, or deadlines.
2. Safety & Transparency: You provide preliminary screening and assistance. Explicitly remind citizens that final approval is determined solely by the respective government authority.
3. Focused Assistance:
   - When asked what schemes a citizen is eligible for, call `check_eligibility`.
   - If key information is missing (e.g. household income or landholding), explain what is missing and ask a clear follow-up question.
   - When asked for documents or how to apply, call `generate_application_checklist`.
   - When asked about new schemes or updates, call `list_schemes` or `run_source_scan`.
   - When asked about upcoming dates, call `get_upcoming_deadlines`.
   - Never attempt to bypass CAPTCHA or submit applications autonomously; emphasize citizen verification.
4. WhatsApp Notifications: Respect user consent at all times. Explain that users can unsubscribe anytime by replying 'Stop notifications'.
5. Tone: Empathetic, respectful, clear, and empowering. Use bullet points and clean structure.
"""

root_agent = Agent(
    name="scheme_finder_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_citizen_profile,
        update_citizen_profile,
        list_schemes,
        check_eligibility,
        run_source_scan,
        get_scan_history,
        send_whatsapp_notification,
        generate_application_checklist,
        get_upcoming_deadlines,
        update_notification_consent,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="scheme_finder",
)
