# 🎙️ Scheme Finder: 5-Minute Hackathon Demo Script & Judge's Walkthrough

> **Track 3**: Autonomous Agent-First Applications on Google Cloud  
> **Core Mission**: Discover government welfare benefits, perform transparent deterministic eligibility screening, monitor official gazettes for scheme updates, and notify citizens via consent-aware WhatsApp alerts.

---

## ⏱️ At-A-Glance 5-Minute Pitch Outline

| Timeline | Stage | Key Actions & Focus Points | Live Feature / Tool Demonstrated |
| :--- | :--- | :--- | :--- |
| **0:00 - 1:00** | **The Hook & Profile Screening** | Introduce the problem: billions in welfare go unclaimed because citizens don't know eligibility criteria or miss deadlines. Select **Ramesh Patel** (Farmer, ₹1.2L income). Run instant deterministic assessment. | `assess_scheme_eligibility`<br>`app/eligibility.py`<br>Section 1 & 4 of Dashboard |
| **1:00 - 2:00** | **Consent-Aware WhatsApp Simulator** | Demonstrate WhatsApp alert dispatch with clear condition breakdown. Demonstrate inbound citizen triage ("Find schemes for me") and instant "STOP" opt-out suppression. | `dispatch_whatsapp_notification`<br>`handle_conversational_reply`<br>Section 5 of Dashboard |
| **2:00 - 3:00** | **Autonomous Source Monitor & Change Detection** | Simulate official circular scan. Demonstrate SHA-256 duplicate alert suppression, detection of extended deadline from June 30 to Sept 30, and domain authority verification barrier. | `run_discovery_scan`<br>`compute_content_hash`<br>Section 3 & 8 of Dashboard |
| **3:00 - 4:00** | **Application Packets & Deadline Tracker** | Generate an end-to-end application packet with verified documents, fee breakdown, and statutory caveats. View upcoming renewals and countdown badges. | `generate_application_packet`<br>`get_upcoming_deadlines`<br>Section 6 & 7 of Dashboard |
| **4:00 - 5:00** | **ADK Agent & A2UI Native Display** | Query the Root ADK Agent via natural language. Observe tool orchestration and rich A2UI card generation directly rendered in chat. Closing architecture summary. | `scheme_finder_agent`<br>`a2ui_callback`<br>Section 9 of Dashboard |

---

## 👥 Synthetic Citizen Persona Catalog

These test citizens are pre-seeded in Cloud Firestore:

1. **`citizen-001` — Ramesh Patel**
   - **Profile**: 45 years old, male, Pune, Maharashtra. Marginal farmer (2.5 acres), ₹1,20,000 annual income, OBC, rural. WhatsApp opted in (`+919876543210`).
   - **Outcome**: Likely eligible for **PM-KISAN** (₹6,000/yr), **PM-JAY Ayushman Bharat** (₹5,00,000 health cover), and **PMFBY Crop Insurance**. Total annual entitlement value: **₹5,18,000+**.
2. **`citizen-002` — Sunita Sharma**
   - **Profile**: 32 years old, female, Delhi. Urban self-employed tailor, ₹85,000 annual income, general category. WhatsApp opted in (`+919876543211`).
   - **Outcome**: Likely eligible for **Delhi Ladli Scheme** and **PM-JAY Health Cover**.
3. **`citizen-003` — Vikram Singh**
   - **Profile**: 38 years old, male, Mumbai, Maharashtra. Software engineer, ₹15,00,000 annual income, urban, general.
   - **Outcome**: **Ineligible** for welfare schemes due to income cap (> ₹2.5L limit) and non-farming status. Demonstrates transparent refusal with exact condition citations.
4. **`citizen-004` — Priya Nair**
   - **Profile**: 29 years old, female, Ernakulam, Kerala. Self-employed, income and landholding unstated.
   - **Outcome**: Status is **`insufficient_information`**. System asks follow-up questions: *"What is your annual household income?"*
5. **`citizen-005` — Anand Kumar**
   - **Profile**: 52 years old, male, Maharashtra. Trader, ₹2,40,000 income, explicitly WhatsApp **opted out**.
   - **Outcome**: Notifications are safely suppressed (`opted_out_suppressed`), strictly respecting user consent.

---

## 🎬 Minute-by-Minute Live Demo Walkthrough

### Minute 0:00 – 1:00: The Problem & Deterministic Eligibility

1. **Speaker Pitch**:
   > *"Every year, millions of low-income families miss out on government welfare benefits simply because eligibility rules are opaque, spread across fragmented portals, or deadlines pass silently. Today, we present **Scheme Finder**, an autonomous agent-first application powered by Google ADK and Google Cloud."*

2. **Action**:
   - Open the web dashboard at `http://localhost:8000/dashboard`.
   - On the top header, switch citizen persona to **Ramesh Patel (`citizen-001`)**.
   - Point to the **My Benefits Overview**: 3 eligible schemes yielding **₹5,18,000+** in annual benefit value.
   - Scroll to **Section 4: Eligibility Assessment Engine**.
   - Show the breakdown for **PM-KISAN**:
     - ✅ Age 45 is within statutory range [18–100].
     - ✅ Landholding 2.5 acres is within 5.0 acres ceiling.
     - ✅ Household income ₹1,20,000 is under ₹2,00,000 limit.
     - ⚠️ Notice the bold statutory disclaimer: *"Preliminary screening only. Official sanction remains subject to verification by the Competent Authority."*

---

### Minute 1:00 – 2:00: Consent-Aware WhatsApp Integration

1. **Speaker Pitch**:
   > *"Web portals don't reach rural citizens—WhatsApp does. But spam destroys trust. Scheme Finder implements strict consent management, explicit opt-ins, and conversational triage."*

2. **Action**:
   - Scroll to **Section 5: WhatsApp Notifications & Inbound Simulator**.
   - Click **"Simulate WhatsApp Push Alert"** for PM-KISAN.
   - Watch the interactive mobile phone mockup on the right light up:
     - Clear scheme details, deadline, verified benefit.
     - Transparent note explaining why Ramesh matched.
     - Actionable official portal link (`pmkisan.gov.in`).
     - Footer: *"Reply HELP for guidance, STOP to unsubscribe."*
   - In the interactive phone chat input, type: `find schemes for me` and hit Send.
   - Watch the instant automated response triage Ramesh's profile and recommend matching schemes.
   - Type: `STOP` and hit Send.
   - Observe the response: *"You have been unsubscribed from Scheme Finder alerts."*
   - Switch persona to **Anand Kumar (`citizen-005`)** and click **Simulate Alert**.
   - Observe the system notification banner: *"Alert safely suppressed: Citizen has opted out of WhatsApp updates."*

---

### Minute 2:00 – 3:00: Autonomous Monitoring & SHA-256 Change Detection

1. **Speaker Pitch**:
   > *"Schemes are not static: deadlines extend, guidelines change, and fake announcements proliferate. Scheme Finder runs background monitoring across official .gov.in endpoints with SHA-256 fingerprinting."*

2. **Action**:
   - Scroll to **Section 8: Official Source Monitoring**.
   - Point out the 4 registered official portals: *MyScheme Portal*, *PIB Welfare Gazette*, *Maharashtra DBT*, and *Delhi e-District*.
   - Click **"Trigger Manual Discovery Scan"**.
   - Scroll up to **Section 3: New Announcements & Changes**:
     - See the live audit log showing SHA-256 content hashes.
     - Notice that scanning an unchanged portal suppresses duplicate alerts (no duplicate spam sent to citizens).
     - Notice detected diff: e.g., an application deadline extension from June 30 to September 30 automatically updates the database and increments the version to `1.1.0`.
     - Point out the security barrier: any announcement originating outside `.gov.in` / `.nic.in` or missing authoritative evidence is flagged as `under_review`, never presented as verified.

---

### Minute 3:00 – 4:00: Application Packets & Deadline Tracking

1. **Speaker Pitch**:
   > *"Finding a scheme is only half the battle. Citizens struggle with paperwork. Scheme Finder generates personalized, actionable document packets."*

2. **Action**:
   - Scroll to **Section 6: Required Documents & Application Packets**.
   - Click **"Generate Complete Packet"** for Ramesh Patel under PM-KISAN.
   - Inspect the generated packet:
     - Step-by-step submission instructions with the exact portal link.
     - Document checklist with verification notes (Aadhaar Card, Land Record 7/12 Extract, Bank Passbook with NPCI Aadhaar seeding).
     - Statutory fee schedule (₹0 official fee, nominal CSC kiosk fee).
   - Scroll to **Section 7: Deadlines & Renewal Tracker**.
   - Highlight the color-coded urgency badges (`URGENT < 15 days`, `UPCOMING`, `ROLLING`).
   - Point out that closed and expired schemes (like expired COVID relief) are automatically omitted from the calendar.

---

### Minute 4:00 – 5:00: ADK Root Agent with A2UI Cards & Architecture

1. **Speaker Pitch**:
   > *"Finally, Scheme Finder embeds Google ADK (Agent Development Kit) with full A2UI rich visual cards."*

2. **Action**:
   - Scroll to **Section 9: AI Scheme Assistant**.
   - Type: `"What agricultural schemes can Ramesh Patel apply for right now?"`
   - Observe the agent orchestrating:
     - Tool call: `get_citizen_profile(citizen_id="citizen-001")`
     - Tool call: `check_eligibility(citizen_id="citizen-001", scheme_id="pm-kisan")`
     - Response rendered via **A2UI**: A structured, color-coded visual card displaying scheme name, verified annual payout (₹6,000/yr), status badge, and official portal action button.
   - Close with the architectural slide / diagram:
     - **Cloud Firestore**: Real-time serverless persistence.
     - **Vertex AI Gemini 3.8 Flash**: Core reasoning and natural language extraction.
     - **ADK 10 Function Tools**: Pure deterministic business logic coexisting with agent intelligence.
     - **Meta WhatsApp Cloud API**: High-impact delivery channel.

---

## 🛠️ Reproduction & Testing Commands for Judges

To verify the entire system locally in under 60 seconds:

```bash
# 1. Enter the project directory
cd /config/Desktop/BuildWithGemini/simple-agent

# 2. Run the complete 38-test evaluation suite
GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-04-54fac5b784e7 uv run pytest \
  tests/unit/ \
  tests/integration/test_scheme_finder_scenarios.py \
  tests/integration/test_api_endpoints.py -v

# 3. Launch the local FastAPI server with the live 9-section dashboard
GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-04-54fac5b784e7 uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000

# 4. Open in browser:
# http://localhost:8000/dashboard
```

---

## 🏆 Key Differentiators for Hackathon Judges

1. **100% Deterministic Legal Rules**: Financial and legal eligibility is never left to LLM hallucination. Rules are evaluated by pure Python logic with transparent statutory citations.
2. **Autonomous Freshness & Integrity**: Official sources are monitored autonomously with SHA-256 fingerprinting to eliminate duplicate notifications while catching deadline extensions.
3. **Respect for Citizen Consent**: Full GDPR/DPDP compliant opt-out handling with automated suppression.
4. **Rich Multi-Channel Presentation**: Responsive web dashboard with native A2UI visual cards, interactive simulated WhatsApp triage, and downloadable application checklists.
