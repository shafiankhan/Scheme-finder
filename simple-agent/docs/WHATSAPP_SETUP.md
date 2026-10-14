# WhatsApp Cloud API Configuration & Readiness Guide

Scheme Finder integrates with the **Meta WhatsApp Cloud API (Graph API v21.0)** for personalized welfare benefit alerts and interactive conversational triage.

---

## 1. Operating Modes

| Mode | Environment Condition | Outbound Behavior | Inbound Behavior |
| :--- | :--- | :--- | :--- |
| **Development Simulator** *(Default)* | `WHATSAPP_CLOUD_API_KEY` or `WHATSAPP_PHONE_NUMBER_ID` is unset / empty. | Persists notifications to Google Cloud Firestore with `delivery_mode="development_simulator"` and displays them in the interactive UI simulator. Zero external network calls. | Messages received via `/api/notifications/chat` REST endpoint and processed through conversational engine. |
| **Meta Cloud API Production** | Both `WHATSAPP_CLOUD_API_KEY` and `WHATSAPP_PHONE_NUMBER_ID` are set. | Dispatches HTTPS POST to `https://graph.facebook.com/v21.0/{PHONE_ID}/messages` with Bearer auth token and template/text payload. | Real inbound WhatsApp webhooks received at `https://SERVICE_URL/api/notifications/webhook`. |

> [!IMPORTANT]
> **Safety Guarantee**: In the absence of verified credentials, Scheme Finder **never** attempts network calls to Meta, protecting users against failed invocations, billing charges, and unverified message delivery.

---

## 2. Required Meta Credentials & Environment Variables

To activate live Meta WhatsApp Cloud API delivery, configure the following variables in `.env`:

```bash
# 1. System User Permanent Access Token with permissions:
#    - whatsapp_business_messaging
#    - whatsapp_business_management
WHATSAPP_CLOUD_API_KEY="EAA..."

# 2. 15-digit Phone Number ID assigned by Meta Business Manager
#    Found under: WhatsApp > API Setup > Phone number ID
WHATSAPP_PHONE_NUMBER_ID="106XXXXXXXXXXXX"

# 3. WhatsApp Business Account ID (WABA ID)
WHATSAPP_BUSINESS_ACCOUNT_ID="104XXXXXXXXXXXX"

# 4. Webhook Verification Token (custom string for GET handshake)
WHATSAPP_WEBHOOK_VERIFY_TOKEN="<YOUR_WEBHOOK_VERIFY_TOKEN>"

# 5. Meta App Secret (for HMAC SHA-256 payload verification)
#    Found under: Meta App Settings > Basic > App Secret
WHATSAPP_APP_SECRET="<YOUR_META_APP_SECRET>"
```

---

## 3. Webhook Setup on Meta Developer Portal

### Step 1: Configure Callback URL
In Meta Developer Dashboard -> WhatsApp -> Configuration -> Webhook:
1. **Callback URL**: `https://<YOUR_SERVICE_URL>/api/notifications/webhook`
2. **Verify Token**: Must match `WHATSAPP_WEBHOOK_VERIFY_TOKEN` in your environment.
3. Click **Verify and Save**. Meta sends a `GET` request:
   ```
   GET /api/notifications/webhook?hub.mode=subscribe&hub.challenge=1158201444&hub.verify_token=scheme_finder_secure_webhook_token_2026
   ```
   Scheme Finder verifies the token and immediately returns `1158201444` with HTTP 200.

### Step 2: Subscribe to Webhook Fields
Check the following subscription fields:
- `messages` (inbound citizen messages)
- `message_deliveries` (delivery receipts)
- `message_status` (sent, delivered, read status)

---

## 4. User Consent & Opt-Out Policy

In compliance with WhatsApp Business Messaging Policies and statutory privacy safeguards:
1. **Explicit Opt-In Required**: Notifications are dispatched **only** if the citizen's profile has `whatsapp_opt_in = true`.
2. **Immediate Opt-Out Processing**:
   - Inbound keywords: `STOP`, `UNSUBSCRIBE`, `CANCEL`, `QUIT`, `ROK` (case-insensitive).
   - Scheme Finder automatically sets `whatsapp_opt_in = False` in Firestore and halts all outbound communication.
3. **Audit Logging**: Every opt-out event and suppressed delivery is recorded in Firestore with `delivery_status="opted_out_suppressed"`.
4. **Mandatory Statutory Disclaimer**: Every notification contains the official disclaimer stating that preliminary screening is not an official government approval guarantee.
