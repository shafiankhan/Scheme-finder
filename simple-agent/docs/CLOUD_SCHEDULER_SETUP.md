# Google Cloud Scheduler Setup for Scheme Finder Weekly Monitoring

This guide describes how to configure Google Cloud Scheduler to trigger the autonomous government source discovery scan reliably on an external schedule without depending on an in-process daemon.

---

## 1. Architecture Overview

```
+--------------------------+
|  Google Cloud Scheduler  |  Trigger: Every Monday 00:00 UTC ("0 0 * * 1")
+------------+-------------+  Target: POST /api/sources/scan
             |
             | Authenticated with Google-signed OIDC Bearer Token
             v
+--------------------------+
|  Scheme Finder Service   |  1. Verifies caller identity
|       (Cloud Run)        |  2. Acquires asyncio scan lock (guards against overlap)
+------------+-------------+  3. Probes registered official sources
             |                4. Detects updates / notifies matching citizens
             v
+--------------------------+
|   Google Cloud Firestore |  Persists ScanLog, updated Schemes & Notifications
+--------------------------+
```

---

## 2. Authentication & Identity Setup

Google Cloud Run services deployed with `--no-allow-unauthenticated` require callers to supply an OIDC ID token signed by Google.

### Step 1: Create Dedicated Service Account
```bash
# Create service account specifically for scheduler invocations
gcloud iam service-accounts create scheme-finder-scheduler \
    --display-name="Scheme Finder Cloud Scheduler Service Account" \
    --description="Used by Cloud Scheduler to trigger weekly welfare scheme discovery scans"
```

### Step 2: Grant Cloud Run Invoker Role
```bash
# Allow scheduler service account to invoke the Scheme Finder Cloud Run service
gcloud run services add-iam-policy-binding scheme-finder \
    --region=us-central1 \
    --member="serviceAccount:scheme-finder-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

---

## 3. Provisioning the Cloud Scheduler Job

### Command-line Provisioning (`gcloud`)
```bash
export SERVICE_URL=$(gcloud run services describe scheme-finder --region=us-central1 --format='value(status.url)')
export SCHEDULER_SA="scheme-finder-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud scheduler jobs create http scheme-finder-weekly-scan \
    --location=us-central1 \
    --schedule="0 0 * * 1" \
    --time-zone="UTC" \
    --uri="${SERVICE_URL}/api/sources/scan" \
    --http-method=POST \
    --oidc-service-account-email="${SCHEDULER_SA}" \
    --oidc-token-audience="${SERVICE_URL}" \
    --max-retry-attempts=3 \
    --min-backoff="10s" \
    --max-backoff="300s" \
    --description="Autonomous weekly welfare scheme discovery scan for Scheme Finder"
```

---

## 4. Concurrency Guard & Duplicate Scan Prevention

Scheme Finder guards the `/api/sources/scan` endpoint using an internal `asyncio.Lock()` in `app/monitor.py`:
- If an existing scan is executing when Cloud Scheduler triggers a new request, Scheme Finder immediately rejects the second request with **HTTP 409 Conflict**:
  ```json
  {
    "detail": "A discovery scan is already active: A discovery scan is already active. Concurrent scans are prevented."
  }
  ```
- This guarantees that two scheduler triggers, or a manual dashboard button click coinciding with the scheduled cron, will **never run overlapping scans**, preventing duplicate Firestore records and redundant WhatsApp alerts.

---

## 5. Manual Testing and Verification

To trigger the Cloud Scheduler job out-of-band:
```bash
gcloud scheduler jobs run scheme-finder-weekly-scan --location=us-central1
```

To view execution logs:
```bash
gcloud scheduler jobs describe scheme-finder-weekly-scan --location=us-central1
```
