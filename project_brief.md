# My agent: Scheme Finder
One-liner: A conversational agent that helps citizens discover government welfare schemes, automatically assess potential eligibility, monitor official government portals for newly announced or updated benefits, and receive personalized notifications through WhatsApp.

Tool coverage:
- Memory: Citizen demographic profile, voluntary circumstances (household income, landholding, age, occupation, caste category, disability), consent preferences, notification history, application checklists, and prior enrolled benefits.
- Tools: 
  - Firestore scheme and profile storage (schemes, versioned criteria, profiles, scan records, notifications)
  - Autonomous source discovery and change detection engine (checking official RSS feeds, myScheme, PIB, state portals)
  - Deterministic eligibility evaluation engine (rule-based matching against versioned criteria)
  - WhatsApp Business Cloud API dispatcher with safety-first development simulator fallback
  - Application checklist & draft preparation assistant
  - Deadline and renewal tracking tool
- Catalog/UI: Catalog of verified central and state government schemes (e.g., PM-KISAN, Ayushman Bharat PM-JAY, PM Awas Yojana, Delhi Ladli, Maharashtra PMKSY), rendered as rich A2UI cards in ADK and structured views across a 9-section dashboard.
- Image gen: Visual infographic badges and document requirement guides generated for citizens.
- Sandbox: Deterministic eligibility criteria calculation, landholding/income threshold checking, and source content diffing.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Official government source monitoring with SHA-256 duplicate suppression, WhatsApp Business Cloud API with development simulator fallback, deterministic versioned eligibility engine, and a complete 9-section citizen dashboard.
