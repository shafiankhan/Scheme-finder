"""Firestore persistence layer for Scheme Finder.

Provides methods to persist and retrieve citizen profiles, government schemes,
official sources, scan records, notifications, and application checklists.
Supports both live Google Cloud Firestore and an in-memory test store.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from google.cloud import firestore

from app.models import (
    ApplicationChecklist,
    CitizenProfile,
    OfficialSource,
    ScanLog,
    Scheme,
    WhatsAppNotification,
)

# Project ID from environment
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-54fac5b784e7")
USE_IN_MEMORY_DB = os.environ.get("USE_IN_MEMORY_DB", "").lower() in ("true", "1")


class InMemoryDatabase:
    """Mock database for isolated testing and offline fallback."""
    def __init__(self):
        self.schemes: Dict[str, Dict[str, Any]] = {}
        self.citizens: Dict[str, Dict[str, Any]] = {}
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.scan_logs: List[Dict[str, Any]] = []
        self.notifications: List[Dict[str, Any]] = []
        self.applications: Dict[str, Dict[str, Any]] = {}

    def clear(self):
        self.schemes.clear()
        self.citizens.clear()
        self.sources.clear()
        self.scan_logs.clear()
        self.notifications.clear()
        self.applications.clear()


_in_memory_instance: Optional[InMemoryDatabase] = None


def get_in_memory_db() -> InMemoryDatabase:
    global _in_memory_instance
    if _in_memory_instance is None:
        _in_memory_instance = InMemoryDatabase()
    return _in_memory_instance


_firestore_client: Optional[firestore.Client] = None


def get_db_client() -> Optional[firestore.Client]:
    """Retrieve initialized Firestore client if configured and accessible."""
    global _firestore_client
    if USE_IN_MEMORY_DB:
        return None
    if _firestore_client is None:
        try:
            _firestore_client = firestore.Client(project=PROJECT_ID)
        except Exception as exc:
            # Fallback to in-memory mode if Firestore cannot be reached
            return None
    return _firestore_client


# ==========================================
# Schemes Collection
# ==========================================

def save_scheme(scheme: Scheme) -> None:
    client = get_db_client()
    data = scheme.model_dump()
    if client:
        client.collection("schemes").document(scheme.scheme_id).set(data)
    else:
        get_in_memory_db().schemes[scheme.scheme_id] = data


def get_scheme(scheme_id: str) -> Optional[Scheme]:
    client = get_db_client()
    if client:
        doc = client.collection("schemes").document(scheme_id).get()
        if doc.exists:
            return Scheme(**doc.to_dict())
        return None
    data = get_in_memory_db().schemes.get(scheme_id)
    return Scheme(**data) if data else None


def delete_scheme(scheme_id: str) -> None:
    client = get_db_client()
    if client:
        client.collection("schemes").document(scheme_id).delete()
    else:
        get_in_memory_db().schemes.pop(scheme_id, None)


def list_schemes(
    category: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Scheme]:
    client = get_db_client()
    schemes_data: List[Dict[str, Any]] = []
    if client:
        col = client.collection("schemes")
        query = col
        if status:
            query = query.where("status", "==", status)
        if category:
            query = query.where("category", "==", category)
        for doc in query.stream():
            schemes_data.append(doc.to_dict())
    else:
        schemes_data = list(get_in_memory_db().schemes.values())
        if status:
            schemes_data = [s for s in schemes_data if s.get("status") == status]
        if category:
            schemes_data = [s for s in schemes_data if s.get("category") == category]

    schemes = [Scheme(**s) for s in schemes_data]
    if state and state.lower() != "all":
        schemes = [
            s for s in schemes
            if s.level == "central" or (s.state_name and s.state_name.lower() == state.lower())
        ]
    return schemes


# ==========================================
# Citizen Profiles Collection
# ==========================================

def save_citizen_profile(profile: CitizenProfile) -> None:
    client = get_db_client()
    data = profile.model_dump()
    if client:
        client.collection("citizens").document(profile.citizen_id).set(data)
    else:
        get_in_memory_db().citizens[profile.citizen_id] = data


def get_citizen_profile(citizen_id: str) -> Optional[CitizenProfile]:
    client = get_db_client()
    if client:
        doc = client.collection("citizens").document(citizen_id).get()
        if doc.exists:
            return CitizenProfile(**doc.to_dict())
        return None
    data = get_in_memory_db().citizens.get(citizen_id)
    return CitizenProfile(**data) if data else None


def list_citizen_profiles() -> List[CitizenProfile]:
    client = get_db_client()
    profiles_data = []
    if client:
        for doc in client.collection("citizens").stream():
            profiles_data.append(doc.to_dict())
    else:
        profiles_data = list(get_in_memory_db().citizens.values())
    return [CitizenProfile(**p) for p in profiles_data]


# ==========================================
# Official Sources Collection
# ==========================================

def save_source(source: OfficialSource) -> None:
    client = get_db_client()
    data = source.model_dump()
    if client:
        client.collection("sources").document(source.source_id).set(data)
    else:
        get_in_memory_db().sources[source.source_id] = data


def get_source(source_id: str) -> Optional[OfficialSource]:
    client = get_db_client()
    if client:
        doc = client.collection("sources").document(source_id).get()
        if doc.exists:
            return OfficialSource(**doc.to_dict())
        return None
    data = get_in_memory_db().sources.get(source_id)
    return OfficialSource(**data) if data else None


def list_sources() -> List[OfficialSource]:
    client = get_db_client()
    sources_data = []
    if client:
        for doc in client.collection("sources").stream():
            sources_data.append(doc.to_dict())
    else:
        sources_data = list(get_in_memory_db().sources.values())
    return [OfficialSource(**s) for s in sources_data]


# ==========================================
# Scan Logs Collection
# ==========================================

def save_scan_log(scan_log: ScanLog) -> None:
    client = get_db_client()
    data = scan_log.model_dump()
    if client:
        client.collection("scan_logs").document(scan_log.scan_id).set(data)
    else:
        get_in_memory_db().scan_logs.insert(0, data)


def list_scan_logs(limit: int = 10) -> List[ScanLog]:
    client = get_db_client()
    logs_data = []
    if client:
        docs = (
            client.collection("scan_logs")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        for doc in docs:
            logs_data.append(doc.to_dict())
    else:
        logs_data = get_in_memory_db().scan_logs[:limit]
    return [ScanLog(**lg) for lg in logs_data]


# ==========================================
# WhatsApp Notifications Collection
# ==========================================

def save_notification(notification: WhatsAppNotification) -> None:
    client = get_db_client()
    data = notification.model_dump()
    if client:
        client.collection("whatsapp_notifications").document(notification.notification_id).set(data)
    else:
        get_in_memory_db().notifications.insert(0, data)


def list_notifications(
    citizen_id: Optional[str] = None,
    limit: int = 30,
) -> List[WhatsAppNotification]:
    client = get_db_client()
    items = []
    if client:
        query = client.collection("whatsapp_notifications")
        if citizen_id:
            query = query.where("citizen_id", "==", citizen_id)
        docs = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        for doc in docs:
            items.append(doc.to_dict())
    else:
        raw = get_in_memory_db().notifications
        if citizen_id:
            raw = [n for n in raw if n.get("citizen_id") == citizen_id]
        items = raw[:limit]
    return [WhatsAppNotification(**n) for n in items]


# ==========================================
# Application Checklists Collection
# ==========================================

def save_application(application: ApplicationChecklist) -> None:
    client = get_db_client()
    data = application.model_dump()
    if client:
        client.collection("applications").document(application.application_id).set(data)
    else:
        get_in_memory_db().applications[application.application_id] = data


def get_application(application_id: str) -> Optional[ApplicationChecklist]:
    client = get_db_client()
    if client:
        doc = client.collection("applications").document(application_id).get()
        if doc.exists:
            return ApplicationChecklist(**doc.to_dict())
        return None
    data = get_in_memory_db().applications.get(application_id)
    return ApplicationChecklist(**data) if data else None


def list_applications(citizen_id: Optional[str] = None) -> List[ApplicationChecklist]:
    client = get_db_client()
    apps_data = []
    if client:
        query = client.collection("applications")
        if citizen_id:
            query = query.where("citizen_id", "==", citizen_id)
        for doc in query.stream():
            apps_data.append(doc.to_dict())
    else:
        apps_data = list(get_in_memory_db().applications.values())
        if citizen_id:
            apps_data = [a for a in apps_data if a.get("citizen_id") == citizen_id]
    return [ApplicationChecklist(**a) for a in apps_data]
