"""Seed authoritative demonstration records for Scheme Finder.

Populates Firestore with verified central and state government schemes,
official source registries, and synthetic citizen profiles for hackathon
demonstration and reproducible evaluation.
"""

from __future__ import annotations

from typing import List
from app import db
from app.models import (
    ApplicationWindow,
    CitizenProfile,
    OfficialSource,
    Scheme,
    SchemeEligibilityRules,
)


def get_seed_schemes() -> List[Scheme]:
    return [
        Scheme(
            scheme_id="pm-kisan",
            name="Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
            version="1.0.0",
            category="agriculture",
            level="central",
            state_name=None,
            ministry="Ministry of Agriculture and Farmers Welfare",
            brief_description="Direct income support of ₹6,000 per year for all landholding farmer families across India.",
            verified_benefit="₹6,000 per year distributed in three equal four-monthly installments of ₹2,000 directly transferred into Aadhaar-linked bank accounts via DBT.",
            benefit_amount_annual=6000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=18,
                requires_farmer=True,
                max_landholding_acres=5.0,
                residency="both",
                income_max=300000,
            ),
            required_documents=[
                "Aadhaar Card",
                "Land Ownership Record / Khatauni / RoR",
                "Bank Account Passbook with IFSC",
                "Aadhaar-seeded Mobile Number",
            ],
            application_window=ApplicationWindow(
                status="rolling",
                verified_deadline=None,
                deadline_verified_date="2026-10-01",
                renewal_required=True,
                renewal_window_days=365,
            ),
            official_portal_url="https://pmkisan.gov.in",
            source_url="https://www.myscheme.gov.in/schemes/pm-kisan",
            source_authority="Government of India / Ministry of Agriculture",
            uncertainty_flags=[
                "Income limit is an empirical screening proxy: statutory PM-KISAN exclusion applies to income-tax payers in the last assessment year rather than a flat numerical ceiling.",
                "Landholding limit of 5.0 acres reflects the original Feb 2019 scheme definition; the Cabinet expanded coverage in June 2019 to all landholding farmer families regardless of acreage.",
            ],
            status="verified",
        ),
        Scheme(
            scheme_id="pm-jay",
            name="Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
            version="1.1.0",
            category="healthcare",
            level="central",
            state_name=None,
            ministry="Ministry of Health and Family Welfare / National Health Authority",
            brief_description="World's largest government-funded health assurance scheme providing ₹5 lakh health cover per family per year.",
            verified_benefit="Cashless and paperless inpatient secondary and tertiary hospital care up to ₹500,000 per family per year at public and empaneled private hospitals.",
            benefit_amount_annual=500000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=0,
                income_max=250000,
                residency="both",
            ),
            required_documents=[
                "Aadhaar Card or Government Photo ID",
                "Ration Card",
                "Proof of Family Identity / PM-JAY Family Letter",
            ],
            application_window=ApplicationWindow(
                status="open",
                verified_deadline="2026-12-31",
                deadline_verified_date="2026-10-01",
            ),
            official_portal_url="https://pmjay.gov.in",
            source_url="https://www.myscheme.gov.in/schemes/pmjay",
            source_authority="National Health Authority, Govt. of India",
            uncertainty_flags=[
                "Statutory PM-JAY eligibility is based on SECC 2011 deprivation criteria (D1–D7) and NFSA cards; the ₹250,000 income ceiling is an empirical screening proxy.",
                "Universal expansion: Since September 2024, all senior citizens aged 70+ in India are eligible for PM-JAY regardless of family income.",
            ],
            status="verified",
        ),
        Scheme(
            scheme_id="pm-awas-gramin",
            name="Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)",
            version="1.0.0",
            category="housing",
            level="central",
            state_name=None,
            ministry="Ministry of Rural Development",
            brief_description="Financial assistance to rural houseless households and those living in kutcha/dilapidated houses to build a pucca house.",
            verified_benefit="Financial unit assistance of ₹120,000 in plains and ₹130,000 in hilly/hilly states, plus 90-95 days of unskilled labor wages under MGNREGS and ₹12,000 for toilet construction.",
            benefit_amount_annual=120000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=18,
                income_max=180000,
                residency="rural",
            ),
            required_documents=[
                "Aadhaar Card",
                "Bank Account Details / Passbook",
                "Swachh Bharat Mission (SBM) Registration Number",
                "MGNREGA Job Card Number",
                "Land / Homestead Site Ownership Certificate",
            ],
            application_window=ApplicationWindow(
                status="open",
                verified_deadline="2026-11-30",
                deadline_verified_date="2026-09-15",
            ),
            official_portal_url="https://pmayg.nic.in",
            source_url="https://www.myscheme.gov.in/schemes/pmay-g",
            source_authority="Ministry of Rural Development, Govt. of India",
            uncertainty_flags=[
                "Statutory selection uses SECC 2011 houselessness criteria and Awaas+ list (0, 1, or 2 kutcha rooms) with 13 exclusions; the ₹180,000 income ceiling is an empirical screening proxy.",
            ],
            status="verified",
        ),
        Scheme(
            scheme_id="pm-ujjwala",
            name="Pradhan Mantri Ujjwala Yojana (PMUY 2.0)",
            version="2.0.0",
            category="women",
            level="central",
            state_name=None,
            ministry="Ministry of Petroleum and Natural Gas",
            brief_description="Deposit-free LPG cylinder connection for adult women belonging to low-income households.",
            verified_benefit="Free LPG connection with financial aid of ₹1,600, free first LPG cylinder refill, and free hotplate/stove.",
            benefit_amount_annual=1600.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=18,
                income_max=200000,
                target_genders=["female"],
                residency="both",
            ),
            required_documents=[
                "Aadhaar Card of Female Applicant",
                "BPL / Low Income Ration Card",
                "Bank Account Passbook / IFSC",
                "14-Point Supplementary Affidavit / Declaration",
            ],
            application_window=ApplicationWindow(
                status="open",
                verified_deadline="2026-12-31",
                deadline_verified_date="2026-08-01",
            ),
            official_portal_url="https://pmuy.gov.in",
            source_url="https://www.myscheme.gov.in/schemes/pmuy",
            source_authority="Ministry of Petroleum and Natural Gas, Govt. of India",
            uncertainty_flags=[
                "Requires applicant household to have no existing active LPG cylinder connection in any member's name.",
                "Statutory eligibility requires SECC/BPL/Antyodaya cards or certified priority socio-economic categories; ₹200,000 income limit is an empirical screening proxy.",
            ],
            status="verified",
        ),
        Scheme(
            scheme_id="delhi-ladli",
            name="Delhi Ladli Scheme",
            version="1.0.0",
            category="women",
            level="state",
            state_name="Delhi",
            ministry="Department of Women and Child Development, Govt. of NCT of Delhi",
            brief_description="Financial assistance in the name of the girl child to promote education and prevent female foeticide in Delhi.",
            verified_benefit="Financial deposit of ₹10,000 for institutional delivery and ₹5,000 upon admission to each milestone class (I, VI, IX, X, XII) deposited with SBI Life Insurance until age 18.",
            benefit_amount_annual=10000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_max=18,
                income_max=100000,
                allowed_states=["Delhi"],
                target_genders=["female"],
                residency="both",
            ),
            required_documents=[
                "Proof of 3 Years Residence in Delhi (Ration Card/Voter ID/Electricity Bill)",
                "Birth Certificate of Girl Child issued by MCD/NDMC",
                "Income Certificate of Parents (Annual Income under ₹100,000)",
                "School Admission Certificate",
            ],
            application_window=ApplicationWindow(
                status="open",
                verified_deadline="2026-10-31",
                deadline_verified_date="2026-09-01",
            ),
            official_portal_url="https://wcd.delhi.gov.in",
            source_url="https://edistrict.delhigovt.nic.in/",
            source_authority="Government of NCT of Delhi",
            uncertainty_flags=[
                "Maturity amount is held in trust with SBI Life Insurance until the girl child reaches 18 years and completes Class X as a regular student.",
            ],
            status="verified",
        ),
        Scheme(
            scheme_id="mh-mjpjay",
            name="Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
            version="2.0.0",
            category="healthcare",
            level="state",
            state_name="Maharashtra",
            ministry="Public Health Department, Government of Maharashtra",
            brief_description="Flagship cashless health insurance scheme for vulnerable families in Maharashtra.",
            verified_benefit="Cashless hospitalization and surgical procedures coverage up to ₹500,000 per family per year in empaneled hospitals across Maharashtra.",
            benefit_amount_annual=500000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=0,
                income_max=250000,
                allowed_states=["Maharashtra"],
                residency="both",
            ),
            required_documents=[
                "Yellow or Orange Ration Card / Antyodaya Anna Yojana Card",
                "Aadhaar Card",
                "Maharashtra Domicile Certificate or Proof of Residence",
            ],
            application_window=ApplicationWindow(
                status="open",
                verified_deadline="2026-12-31",
                deadline_verified_date="2026-09-01",
            ),
            official_portal_url="https://www.jeevandayee.gov.in",
            source_url="https://mahadbt.maharashtra.gov.in/",
            source_authority="State Health Assurance Society, Govt. of Maharashtra",
            uncertainty_flags=[
                "Scheme coverage was revised in 2023-2024 to ₹500,000 and expanded to all Maharashtra domicile ration card holders.",
            ],
            status="verified",
        ),
        # Test Scheme: Expired scheme (Evaluation Scenario 9)
        Scheme(
            scheme_id="covid-relief-2021",
            name="National Emergency COVID-19 Ex-Gratia Relief 2021",
            version="1.0.0",
            category="social_welfare",
            level="central",
            state_name=None,
            ministry="National Disaster Management Authority",
            brief_description="Ex-gratia emergency relief assistance for pandemic-affected households.",
            verified_benefit="One-time ex-gratia payment of ₹50,000.",
            benefit_amount_annual=50000.0,
            eligibility_rules=SchemeEligibilityRules(
                age_min=18,
                residency="both",
            ),
            required_documents=["Aadhaar Card", "COVID-19 Death/Medical Certificate"],
            application_window=ApplicationWindow(
                status="expired",
                verified_deadline="2021-12-31",
                deadline_verified_date="2021-12-31",
            ),
            official_portal_url="https://ndma.gov.in",
            source_url="https://pib.gov.in/expired-scheme",
            source_authority="Government of India / NDMA",
            status="expired",
        ),
        # Test Scheme: Under review / ambiguous criteria (Evaluation Scenario 8 & 12)
        Scheme(
            scheme_id="solar-tractor-subsidy-draft",
            name="National Solar Tractor Pilot Subsidy (Draft)",
            version="0.1.0",
            category="agriculture",
            level="central",
            state_name=None,
            ministry="Ministry of New and Renewable Energy",
            brief_description="Proposed subsidy for small farmers adopting solar-powered agricultural tractors.",
            verified_benefit="Unverified: reports vary between 40% and 60% capital subsidy.",
            benefit_amount_annual=None,
            eligibility_rules=SchemeEligibilityRules(
                requires_farmer=True,
                residency="rural",
            ),
            required_documents=["Land Records"],
            application_window=ApplicationWindow(
                status="closed",
                verified_deadline=None,
            ),
            official_portal_url="https://mnre.gov.in",
            source_url="https://mnre.gov.in/draft-solar-tractor",
            source_authority="MNRE (Draft Announcement)",
            uncertainty_flags=[
                "Official gazette notification pending",
                "Conflicting subsidy percentages across ministry draft papers",
                "Eligibility income ceiling currently undefined",
            ],
            status="under_review",
        ),
    ]


def get_seed_sources() -> List[OfficialSource]:
    return [
        OfficialSource(
            source_id="myscheme-portal",
            name="MyScheme National Government Services Portal",
            url="https://www.myscheme.gov.in/api/v1/schemes",
            source_type="api",
            level="central",
            state="central",
            check_interval_hours=168,
            last_status="healthy",
        ),
        OfficialSource(
            source_id="pib-welfare",
            name="Press Information Bureau (PIB) Agriculture & Social Welfare",
            url="https://pib.gov.in/RssRelease.aspx?MinistryId=2",
            source_type="rss",
            level="central",
            state="central",
            check_interval_hours=168,
            last_status="healthy",
        ),
        OfficialSource(
            source_id="delhi-edistrict",
            name="Delhi e-District Welfare Portal",
            url="https://edistrict.delhigovt.nic.in/schemes",
            source_type="webpage",
            level="state",
            state="Delhi",
            check_interval_hours=168,
            last_status="healthy",
        ),
        OfficialSource(
            source_id="maharashtra-dbt",
            name="Maharashtra Aaple Sarkar DBT Portal",
            url="https://mahadbt.maharashtra.gov.in/schemes",
            source_type="webpage",
            level="state",
            state="Maharashtra",
            check_interval_hours=168,
            last_status="healthy",
        ),
        # Broken/inaccessible source for Scenario 7 test
        OfficialSource(
            source_id="inaccessible-test-portal",
            name="Inaccessible Regional Welfare Server (Test Endpoint)",
            url="https://invalid-official-domain-404-timeout.gov.in/feed.rss",
            source_type="rss",
            level="state",
            state="Goa",
            check_interval_hours=168,
            last_status="degraded",
            failure_count=1,
        ),
    ]


def get_seed_citizens() -> List[CitizenProfile]:
    return [
        CitizenProfile(
            citizen_id="citizen-001",
            full_name="Ramesh Patel",
            phone_number="+919876543210",
            whatsapp_opt_in=True,
            notification_frequency="weekly",
            state="Maharashtra",
            district="Pune",
            residency_type="rural",
            age=46,
            gender="male",
            household_income=120000,
            household_size=4,
            occupation="farmer",
            is_farmer=True,
            landholding_acres=2.5,
            social_category="obc",
            disability=False,
            is_student=False,
            current_enrollments=[],
        ),
        CitizenProfile(
            citizen_id="citizen-002",
            full_name="Sunita Sharma",
            phone_number="+919876543211",
            whatsapp_opt_in=True,
            notification_frequency="weekly",
            state="Delhi",
            district="East Delhi",
            residency_type="urban",
            age=34,
            gender="female",
            household_income=80000,
            household_size=3,
            occupation="tailor",
            is_farmer=False,
            landholding_acres=None,
            social_category="general",
            disability=False,
            is_student=False,
            current_enrollments=[],
        ),
        CitizenProfile(
            citizen_id="citizen-003",
            full_name="Vikram Singh",
            phone_number="+919876543212",
            whatsapp_opt_in=True,
            notification_frequency="weekly",
            state="Maharashtra",
            district="Mumbai",
            residency_type="urban",
            age=38,
            gender="male",
            household_income=1500000,  # High income -> Ineligible for subsidized welfare
            household_size=3,
            occupation="salaried",
            is_farmer=False,
            landholding_acres=None,
            social_category="general",
            disability=False,
            is_student=False,
            current_enrollments=[],
        ),
        CitizenProfile(
            citizen_id="citizen-004",
            full_name="Priya Nair",
            phone_number="+919876543213",
            whatsapp_opt_in=True,
            notification_frequency="weekly",
            state="Maharashtra",
            district="Nashik",
            residency_type="rural",
            age=29,
            gender="female",
            household_income=None,  # Missing income -> Insufficient Information
            household_size=2,
            occupation="farmer",
            is_farmer=True,
            landholding_acres=None,  # Missing landholding -> Insufficient Information
            social_category="general",
            disability=False,
            is_student=False,
            current_enrollments=[],
        ),
        CitizenProfile(
            citizen_id="citizen-005",
            full_name="Anand Kumar",
            phone_number="+919876543214",
            whatsapp_opt_in=False,  # Explicitly Opted-Out of WhatsApp
            notification_frequency="none",
            state="Maharashtra",
            district="Nagpur",
            residency_type="rural",
            age=50,
            gender="male",
            household_income=110000,
            household_size=4,
            occupation="farmer",
            is_farmer=True,
            landholding_acres=3.0,
            social_category="sc",
            disability=False,
            is_student=False,
            current_enrollments=[],
        ),
    ]


def seed_all() -> None:
    """Populates Firestore with all seed records."""
    for scheme in get_seed_schemes():
        db.save_scheme(scheme)
    for source in get_seed_sources():
        db.save_source(source)
    for citizen in get_seed_citizens():
        db.save_citizen_profile(citizen)


if __name__ == "__main__":
    seed_all()
    print("Successfully seeded demonstration schemes, sources, and citizen profiles into Firestore.")
