"""Pydantic data models for Scheme Finder.

Defines schemas for citizen profiles, versioned government schemes,
eligibility assessments, official source registries, scan logs,
WhatsApp notifications, and application checklists.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CitizenProfile(BaseModel):
    """Citizen demographic and socioeconomic profile for scheme discovery."""
    citizen_id: str
    full_name: str
    phone_number: str
    whatsapp_opt_in: bool = True
    notification_frequency: str = "weekly"  # immediate, weekly, daily
    state: str  # e.g., "Maharashtra", "Delhi", "Uttar Pradesh"
    district: str = ""
    residency_type: str = "rural"  # rural, urban, both
    age: int
    gender: str = "all"  # male, female, other, all
    household_income: Optional[int] = None  # annual income in INR
    household_size: int = 1
    occupation: str = ""  # farmer, student, construction_worker, small_business, unemployed, salaried
    is_farmer: bool = False
    landholding_acres: Optional[float] = None  # cultivable land in acres
    social_category: str = "general"  # general, obc, sc, st, minority
    disability: bool = False
    disability_percentage: Optional[int] = None
    is_student: bool = False
    education_level: str = ""  # school, undergraduate, postgraduate
    current_enrollments: List[str] = Field(default_factory=list)
    application_history: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class SchemeEligibilityRules(BaseModel):
    """Structured and versioned criteria for scheme evaluation."""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    income_max: Optional[int] = None
    allowed_states: Optional[List[str]] = None  # None indicates all states eligible
    residency: str = "both"  # rural, urban, both
    occupations: Optional[List[str]] = None  # None or empty indicates any occupation
    requires_farmer: bool = False
    max_landholding_acres: Optional[float] = None
    target_genders: Optional[List[str]] = None  # None indicates all genders
    requires_disability: bool = False
    requires_student: bool = False
    allowed_social_categories: Optional[List[str]] = None  # sc, st, obc, etc.


class ApplicationWindow(BaseModel):
    """Current application window and verified deadlines."""
    status: str = "open"  # open, rolling, closed, expired
    verified_deadline: Optional[str] = None  # YYYY-MM-DD
    deadline_verified_date: Optional[str] = None
    renewal_required: bool = False
    renewal_window_days: Optional[int] = None


class Scheme(BaseModel):
    """Versioned government welfare scheme record."""
    scheme_id: str
    name: str
    version: str = "1.0.0"
    category: str  # agriculture, healthcare, housing, education, social_welfare, women
    level: str = "central"  # central, state
    state_name: Optional[str] = None
    ministry: str
    brief_description: str
    verified_benefit: str
    benefit_amount_annual: Optional[float] = None
    eligibility_rules: SchemeEligibilityRules
    required_documents: List[str] = Field(default_factory=list)
    application_window: ApplicationWindow = Field(default_factory=ApplicationWindow)
    official_portal_url: str
    source_url: str
    source_authority: str
    last_verified_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    uncertainty_flags: List[str] = Field(default_factory=list)
    status: str = "verified"  # verified, under_review, expired, draft


class EligibilityAssessment(BaseModel):
    """Deterministic assessment result for a citizen against a scheme."""
    scheme_id: str
    scheme_name: str
    status: str  # likely_eligible, potentially_eligible, ineligible, insufficient_information
    conditions_satisfied: List[str] = Field(default_factory=list)
    conditions_failed: List[str] = Field(default_factory=list)
    conditions_unverified: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)
    verified_benefit: str = ""
    verified_deadline: Optional[str] = None
    official_portal_url: str = ""
    last_verified_at: str = ""
    disclaimer: str = (
        "This is an autonomous preliminary screening based on available versioned criteria. "
        "It is not an official government determination or guarantee of approval. "
        "Final eligibility is determined exclusively by the respective government authority."
    )


class OfficialSource(BaseModel):
    """Approved official government source registry entry."""
    source_id: str
    name: str
    url: str
    source_type: str = "webpage"  # rss, api, webpage, sitemap
    level: str = "central"  # central, state
    state: str = "central"
    check_interval_hours: int = 168  # 7 days
    last_scanned_at: Optional[str] = None
    last_status: str = "healthy"  # healthy, error, degraded
    last_content_hash: Optional[str] = None
    failure_count: int = 0


class DetectedChange(BaseModel):
    """Change diff detected during source scanning."""
    scheme_id: str
    scheme_name: str
    change_type: str  # new_scheme, deadline_extended, eligibility_updated, benefit_changed, status_changed
    field_changed: str
    old_value: Any
    new_value: Any
    evidence_snippet: str
    verified: bool = True
    needs_review: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ScanLog(BaseModel):
    """Record of an automated or manual source scan run."""
    scan_id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    sources_scanned: List[str] = Field(default_factory=list)
    new_schemes_found: List[Dict[str, Any]] = Field(default_factory=list)
    changes_detected: List[DetectedChange] = Field(default_factory=list)
    duplicate_suppressed_count: int = 0
    verification_status: str = "verified"
    summary: str = ""


class WhatsAppNotification(BaseModel):
    """Audit record for a personalized WhatsApp notification."""
    notification_id: str
    citizen_id: str
    phone_number: str
    scheme_id: str
    scheme_name: str
    trigger_type: str  # new_matching_scheme, rule_change, deadline_approaching, renewal_reminder, follow_up_info
    message_body: str
    delivery_mode: str = "development_simulator"  # real_cloud_api, development_simulator
    delivery_status: str = "simulated"  # delivered, simulated, opted_out_suppressed, failed
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ApplicationStep(BaseModel):
    """Single step in the official application process."""
    step_number: int
    title: str
    instructions: str
    portal_section: str = ""
    is_online: bool = True


class DocumentChecklistItem(BaseModel):
    """Item in a personalized document checklist."""
    document_name: str
    description: str
    is_provided: bool = False
    verification_source: str = ""
    notes: str = ""


class ApplicationChecklist(BaseModel):
    """Complete application preparation packet."""
    application_id: str
    citizen_id: str
    scheme_id: str
    scheme_name: str
    official_portal_url: str
    steps: List[ApplicationStep] = Field(default_factory=list)
    required_documents: List[DocumentChecklistItem] = Field(default_factory=list)
    prefilled_draft: Dict[str, Any] = Field(default_factory=dict)
    conflicts_or_warnings: List[str] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)
    user_confirmed_submission: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
