"""REST API router for Scheme Finder 9-section dashboard.

Provides endpoints for citizen profiles, scheme discovery, deterministic eligibility,
autonomous official source monitoring, WhatsApp notification dispatch, document
checklists, and direct conversational interaction.
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app import db
from app.application_support import generate_application_packet, get_upcoming_deadlines
from app.eligibility import assess_all_schemes, assess_scheme_eligibility
from app.models import CitizenProfile
from app.monitor import ScanInProgressError, run_discovery_scan
from app.whatsapp import (
    dispatch_whatsapp_notification,
    handle_conversational_reply,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Scheme Finder API"])


class UpdateCitizenRequest(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None
    household_income: Optional[int] = None
    occupation: Optional[str] = None
    is_farmer: Optional[bool] = None
    landholding_acres: Optional[float] = None
    whatsapp_opt_in: Optional[bool] = None
    age: Optional[int] = None


class AssessRequest(BaseModel):
    citizen_id: str
    scheme_id: Optional[str] = None


class SendNotificationRequest(BaseModel):
    citizen_id: str
    scheme_id: str
    trigger_type: str = "new_matching_scheme"


class WhatsAppChatRequest(BaseModel):
    phone_number: str
    message: str


class GenerateAppRequest(BaseModel):
    citizen_id: str
    scheme_id: str


class ChatMessageRequest(BaseModel):
    message: str
    citizen_id: Optional[str] = "citizen-001"


# ==========================================
# Health & Overview
# ==========================================

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": "scheme-finder",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


# ==========================================
# Citizen Profiles
# ==========================================

@router.get("/citizens")
def list_citizens():
    profiles = db.list_citizen_profiles()
    return [p.model_dump() for p in profiles]


@router.get("/citizens/{citizen_id}")
def get_citizen(citizen_id: str):
    profile = db.get_citizen_profile(citizen_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Citizen '{citizen_id}' not found")
    return profile.model_dump()


@router.put("/citizens/{citizen_id}")
def update_citizen(citizen_id: str, req: UpdateCitizenRequest):
    profile = db.get_citizen_profile(citizen_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Citizen '{citizen_id}' not found")

    if req.state is not None:
        profile.state = req.state
    if req.district is not None:
        profile.district = req.district
    if req.household_income is not None:
        profile.household_income = req.household_income
    if req.occupation is not None:
        profile.occupation = req.occupation
    if req.is_farmer is not None:
        profile.is_farmer = req.is_farmer
    if req.landholding_acres is not None:
        profile.landholding_acres = req.landholding_acres
    if req.whatsapp_opt_in is not None:
        profile.whatsapp_opt_in = req.whatsapp_opt_in
        profile.notification_frequency = "weekly" if req.whatsapp_opt_in else "none"
    if req.age is not None:
        profile.age = req.age

    profile.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.save_citizen_profile(profile)
    return profile.model_dump()


# ==========================================
# Schemes Catalog
# ==========================================

@router.get("/schemes")
def list_schemes(
    category: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    status: Optional[str] = Query("verified"),
):
    schemes = db.list_schemes(category=category, state=state, status=status)
    return [s.model_dump() for s in schemes]


@router.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: str):
    scheme = db.get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")
    return scheme.model_dump()


# ==========================================
# Eligibility Assessment
# ==========================================

@router.post("/eligibility/assess")
def assess_eligibility(req: AssessRequest):
    citizen = db.get_citizen_profile(req.citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail=f"Citizen '{req.citizen_id}' not found")

    if req.scheme_id:
        scheme = db.get_scheme(req.scheme_id)
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme '{req.scheme_id}' not found")
        assessment = assess_scheme_eligibility(citizen, scheme)
        return {"assessment": assessment.model_dump()}

    assessments = assess_all_schemes(citizen)
    return {
        "citizen_id": citizen.citizen_id,
        "citizen_name": citizen.full_name,
        "assessments": [a.model_dump() for a in assessments],
    }


# ==========================================
# Deadlines
# ==========================================

@router.get("/deadlines")
def list_deadlines():
    return get_upcoming_deadlines()


# ==========================================
# Official Sources & Scanning
# ==========================================

@router.get("/sources")
def list_sources():
    sources = db.list_sources()
    return [s.model_dump() for s in sources]


@router.post("/sources/scan")
async def trigger_scan():
    try:
        log = await run_discovery_scan()
        return log.model_dump()
    except ScanInProgressError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"A discovery scan is already active: {str(exc)}"
        )


@router.get("/sources/logs")
def get_scan_logs(limit: int = Query(10)):
    logs = db.list_scan_logs(limit=limit)
    return [l.model_dump() for l in logs]


# ==========================================
# WhatsApp Notifications & Inbound Chat
# ==========================================

@router.get("/notifications")
def get_notifications(citizen_id: Optional[str] = Query(None), limit: int = Query(30)):
    notifs = db.list_notifications(citizen_id=citizen_id, limit=limit)
    return [n.model_dump() for n in notifs]


@router.post("/notifications/send")
async def send_notification(req: SendNotificationRequest):
    try:
        notif = await dispatch_whatsapp_notification(
            citizen_id=req.citizen_id,
            scheme_id=req.scheme_id,
            trigger_type=req.trigger_type,
        )
        return notif.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/notifications/chat")
async def whatsapp_chat_webhook(req: WhatsAppChatRequest):
    """Simulates or receives an inbound conversational WhatsApp reply."""
    reply_text = await handle_conversational_reply(
        phone_number=req.phone_number,
        incoming_text=req.message,
    )
    return {
        "from": req.phone_number,
        "reply": reply_text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@router.get("/notifications/webhook")
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Handles the Meta WhatsApp Cloud API GET challenge verification."""
    expected_token = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "scheme_finder_verify_token")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        if hub_challenge:
            return PlainTextResponse(content=hub_challenge, status_code=200)
        return PlainTextResponse(content="OK", status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/notifications/webhook")
async def receive_meta_webhook(payload: Dict[str, Any]):
    """Receives inbound messages or status updates from Meta WhatsApp Cloud API."""
    replies = []
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from")
                    text_obj = msg.get("text", {})
                    body = text_obj.get("body", "")
                    if sender and body:
                        reply = await handle_conversational_reply(sender, body)
                        replies.append({"to": sender, "reply": reply})
    except Exception as exc:
        logger.error("Error processing Meta webhook payload: %s", exc)

    return {"status": "success", "processed": len(replies), "replies": replies}


# ==========================================
# Application Checklists
# ==========================================

@router.post("/applications/generate")
def generate_application(req: GenerateAppRequest):
    citizen = db.get_citizen_profile(req.citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail=f"Citizen '{req.citizen_id}' not found")
    scheme = db.get_scheme(req.scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{req.scheme_id}' not found")

    packet = generate_application_packet(citizen, scheme)
    return packet.model_dump()


@router.get("/applications")
def list_applications(citizen_id: Optional[str] = Query(None)):
    apps = db.list_applications(citizen_id=citizen_id)
    return [a.model_dump() for a in apps]


# ==========================================
# Assistant Direct Chat
# ==========================================

@router.post("/chat")
async def assistant_chat(req: ChatMessageRequest):
    """Processes chat queries directly using the Scheme Finder agent logic."""
    citizen = db.get_citizen_profile(req.citizen_id or "citizen-001")
    user_query = req.message.strip().lower()

    # Fast intent router grounded in deterministic tools
    if "eligible" in user_query or "schemes for me" in user_query or "what can i get" in user_query:
        if not citizen:
            return {"response": "Please select a citizen profile to assess eligibility."}
        assessments = assess_all_schemes(citizen)
        likely = [a for a in assessments if a.status == "likely_eligible"]
        potential = [a for a in assessments if a.status == "potentially_eligible"]
        missing = [a for a in assessments if a.status == "insufficient_information"]

        lines = [f"### 🎯 Eligibility Summary for **{citizen.full_name}** ({citizen.occupation.capitalize()}, {citizen.state})\n"]
        if likely:
            lines.append("#### ✅ Likely Eligible:")
            for a in likely:
                lines.append(f"- **{a.scheme_name}**: {a.verified_benefit} ([Official Portal]({a.official_portal_url}))")
        if potential:
            lines.append("\n#### ⚠️ Potentially Eligible (Verification Required):")
            for a in potential:
                lines.append(f"- **{a.scheme_name}**: {'; '.join(a.conditions_unverified)}")
        if missing:
            lines.append("\n#### ℹ️ Missing Information Needed:")
            for a in missing:
                lines.append(f"- **{a.scheme_name}**: {a.follow_up_questions[0] if a.follow_up_questions else 'Additional data required'}")

        lines.append("\n> **Important Disclaimer:** This is an autonomous preliminary screening based on available versioned criteria. It is not an official government determination or guarantee of approval.")
        return {"response": "\n".join(lines)}

    if "document" in user_query or "apply" in user_query:
        schemes = db.list_schemes(status="verified")
        # Match scheme name
        target_scheme = None
        for s in schemes:
            if s.scheme_id in user_query or s.name.lower() in user_query or s.category in user_query:
                target_scheme = s
                break
        if not target_scheme:
            target_scheme = schemes[0] if schemes else None

        if target_scheme and citizen:
            packet = generate_application_packet(citizen, target_scheme)
            lines = [
                f"### 📋 Application Preparation: **{target_scheme.name}**\n",
                f"**Official Application Portal:** [{target_scheme.official_portal_url}]({target_scheme.official_portal_url})\n",
                "#### Required Document Checklist:",
            ]
            for doc in packet.required_documents:
                status_icon = "✅ (Ready in profile)" if doc.is_provided else "⚠️ (Action required)"
                lines.append(f"- **{doc.document_name}** {status_icon}: {doc.description}")

            lines.append("\n#### Step-by-Step Submission Roadmap:")
            for step in packet.steps:
                lines.append(f"{step.step_number}. **{step.title}**: {step.instructions}")

            lines.append("\n⚠️ *Review Required: Scheme Finder never submits applications autonomously or bypasses Aadhaar OTP verification.*")
            return {"response": "\n".join(lines)}

    if "scan" in user_query or "new scheme" in user_query or "new this week" in user_query:
        logs = db.list_scan_logs(limit=1)
        if logs and logs[0].new_schemes_found:
            found = "\n".join([f"- **{item['name']}**: {item.get('verified_benefit', 'See portal')}" for item in logs[0].new_schemes_found])
            return {"response": f"### 🆕 Recently Discovered Schemes from Official Scan:\n{found}"}
        return {"response": "All 4 registered official portals (myScheme, PIB, Delhi e-District, Maharashtra DBT) are healthy. No new unlisted schemes announced this week."}

    if "deadline" in user_query or "last date" in user_query:
        deadlines = get_upcoming_deadlines()
        lines = ["### ⏰ Upcoming Verified Scheme Deadlines:\n"]
        for d in deadlines:
            lines.append(f"- **{d['scheme_name']}**: Deadline {d['verified_deadline']} ({d['badge_label']}) - [Portal]({d['official_portal_url']})")
        return {"response": "\n".join(lines)}

    # Fallback to general guidance
    return {
        "response": (
            f"Hello {citizen.full_name if citizen else 'Citizen'}! I am **Scheme Finder**, your autonomous benefits discovery assistant.\n\n"
            "I can help you with:\n"
            "- Discovering welfare schemes tailored to your state, age, and occupation\n"
            "- Checking your deterministic eligibility with full condition breakdowns\n"
            "- Preparing document checklists and prefilled application drafts\n"
            "- Tracking application deadlines and setting up WhatsApp alerts\n\n"
            "What would you like to explore today?"
        )
    }
