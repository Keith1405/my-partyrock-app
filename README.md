# 💊 SmartMed Cycle

A deployable AWS version of the SmartMed Cycle PartyRock app — a medicine
preparation tool for patients. **It is a preparation tool only, not a substitute
for pharmacist or prescriber advice.**

Built with **AWS Lambda + Lambda Function URLs + Amazon Bedrock (Claude Haiku 4.5)
+ S3 static hosting + GitHub Actions**. All AI panels stream token-by-token.

---

## Architecture

```
Browser (S3 static site, frontend/index.html)
   │  fetch() + ReadableStream  (POST JSON, text/plain stream back)
   ▼
5 × Lambda Function URL  (RESPONSE_STREAM, AuthType NONE)
   │  Flask app + AWS Lambda Web Adapter layer
   ▼
Amazon Bedrock — converse_stream
   global.anthropic.claude-haiku-4-5-20251001-v1:0  (global inference profile)
```

| Panel | Lambda folder | Inputs sent |
|---|---|---|
| Extract from Photo | `backend/extract_from_photo` | photo (base64) |
| Medicine Card | `backend/medicine_card` | typed details, extracted draft, photo, language |
| My Medicine Summary | `backend/my_medicine_summary` | medicine card, age, other meds, allergies, language |
| My Return Plan | `backend/my_return_plan` | return details, location, photo, language |
| SmartMed Help (chat) | `backend/smartmed_help` | message, history, medicine card, summary, language |

> **Note on Bedrock API:** the Lambdas use the Bedrock **Converse Stream** API
> (`converse_stream`), which cleanly handles multimodal image/document blocks and
> the global cross-region inference profile. The IAM policy still grants both
> `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`, which cover
> the Converse family.

---

## Repository layout

```
frontend/index.html                single-page app (URLs injected by CI)
backend/<widget>/app.py             Flask streaming app
backend/<widget>/run.sh             startup script (python app.py)
backend/<widget>/requirements.txt   flask + boto3
infra/template.yaml                 AWS SAM template
scripts/patient_regression.py       offline patient safety regression suite
scripts/smoke_test.py               local + CI smoke test harness
.github/workflows/deploy.yml        CI/CD pipeline (smoke → deploy)
```

---

## Pre-deployment checklist

1. **Enable Bedrock model access** in region **`ap-southeast-1`**:
   - Model: `global.anthropic.claude-haiku-4-5-20251001-v1:0`
     (Claude Haiku 4.5 — global cross-region inference profile)
   - AWS Console → **Bedrock → Model access** → request access.
   - First-time accounts must submit the use-case form before access is granted.
   - The `global.` profile routes worldwide for throughput, so the IAM policy
     uses `*` for the region in the Bedrock resource ARNs.

2. **Create an S3 bucket for SAM artifacts** (any name), in `ap-southeast-1`.
   This is the `SAM_DEPLOY_BUCKET` secret below (not the website bucket — that
   one is created by the stack).

3. **Add GitHub repository secrets** (Settings → Secrets and variables → Actions):
   | Secret | Value |
   |---|---|
   | `AWS_ACCESS_KEY_ID` | IAM user/role access key |
   | `AWS_SECRET_ACCESS_KEY` | matching secret key |
   | `SAM_DEPLOY_BUCKET` | the SAM artifact bucket from step 2 |

   The deploy credentials need permission to run CloudFormation and create IAM
   roles, Lambda functions, Function URLs, and the S3 website bucket.

---

## Deploy

Push to `main` (or run the workflow manually via **Actions → Deploy SmartMed
Cycle → Run workflow**). The pipeline:

1. `sam build --template infra/template.yaml`
2. `sam deploy` to stack **`smartmed-cycle`** in `ap-southeast-1`
3. Reads the Function URL outputs and `sed`-injects them into
   `frontend/index.html` (replacing the `__URL_*__` placeholders)
4. `aws s3 sync frontend/` to the website bucket with `--cache-control no-cache`
5. Prints the website URL

Open the **`WebsiteUrl`** output (also printed at the end of the run) in a browser.

---

## Local backend test (optional)

```bash
cd backend/medicine_card
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py        # serves on http://localhost:8080
```

Requires local AWS credentials with Bedrock access. POST JSON to `/`:

```bash
curl -N -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"preferred_language":"English","medicine_details":"Metformin 500 mg — one tablet twice daily with meals"}'
```

---

## Automated tests & CI/CD verification

The CI/CD pipeline runs two automated test suites before deploying:

1. **Patient safety regressions (`scripts/patient_regression.py`):**  
   Offline test suite that validates input guards, dosage validations, drug interaction triggers (e.g. Warfarin + Aspirin), allergy alerts (e.g. Penicillin + Amoxicillin), and 999 emergency triggers without making external network calls.
2. **Smoke & routing tests (`scripts/smoke_test.py`):**  
   Boots each backend on a free port and checks:
   - the app imports and starts,
   - `OPTIONS /` returns 200 with CORS headers,
   - `POST /` streams a `text/plain` response,
   - the **413 payload-too-large** guard triggers on an oversized body.

```bash
# Run safety regression tests
python scripts/patient_regression.py

# Run smoke tests
python scripts/smoke_test.py                 # all five
python scripts/smoke_test.py medicine_card   # just one
```

The GitHub Actions **`smoke`** job runs these tests on every push. If any test fails, deployment is aborted before anything reaches AWS.

---

## Notes & guardrails

- Every AI prompt treats inputs as **data only** and never follows instructions
  inside them, never reproduces patient names/IDs/addresses, and never invents
  dose schedules or source URLs.
- Function URLs are `AuthType: NONE` (public) so the static site can call them
  directly. Each Lambda adds **best-effort abuse guards**: an 8 MB payload cap
  (HTTP 413) and a per-instance sliding-window rate limit of 30 requests / 60 s
  (HTTP 429). Tune via the `MAX_BODY_BYTES`, `RATE_MAX`, and `RATE_WINDOW`
  environment variables. These are per-warm-instance and best-effort — for
  stronger protection put **CloudFront + AWS WAF** (rate-based rules) in front,
  which is the recommended production posture for public Function URLs.
- `samconfig.toml` is intentionally **absent** (and git-ignored) — it can cause
  version-key errors in CI; all deploy settings are passed as CLI flags.

---

## 🛠️ Operations Runbook (Production Readiness & Maintenance)

### 1. Monitoring & Alarms
- **CloudWatch Alarms:**
  - `SmartMedCycle-Lambda-HighErrorRate`: Triggers if Lambda functions experience sustained 5xx errors (Threshold: >= 5 errors in 5 min).
  - `SmartMedCycle-Lambda-HighLatency`: Triggers if average response streaming duration exceeds 15 seconds.
- **Cost Ceiling & Budget Alert:**
  - An AWS Budget alarm is configured with a **$20.00 USD hard ceiling** per month. If projected spend exceeds 80% ($16.00), automatic email notifications alert administrators.
- **AI Response Signals:**
  - Refusal rates, token counts, and HTTP 429 throttling are logged to CloudWatch Logs for continuous quality inspection.

### 2. User Feedback & Clinical Triage Loop
- A visible **🚩 Report Issue / Feedback** mechanism is embedded under every AI-generated card on the frontend.
- Patients and clinicians can flag:
  - Incorrect dosage or frequency instructions
  - Missing warnings or drug interactions
  - Unclear or ambiguous wording
  - Incorrect active ingredient identification
- **Triage Process:** Flagged submissions are reviewed and converted into offline regression test cases inside `scripts/patient_regression.py` to prevent regressions before redeploying.

### 3. Incident Response Procedures
- **Incident A: AI producing incorrect or concerning output:**
  1. Inspect the flagged inputs in the triage queue.
  2. Add the test case into `scripts/patient_regression.py`.
  3. Refine the specific prompt rule in `backend/<feature>/app.py`.
  4. Run `python scripts/patient_regression.py` to confirm no regressions.
  5. Push to `main` — GitHub Actions tests and redeploys in ~2 minutes.
- **Incident B: Sudden traffic spike or cost anomaly:**
  1. Tighten the sliding-window rate limit via `RATE_MAX` (e.g. drop from 30 to 10 requests/min).
  2. CloudFront WAF rate-based rules throttle offending client IPs automatically.
- **Incident C: AWS regional outage or Bedrock throttling:**
  1. The global cross-region inference profile (`global.anthropic.claude-haiku-4-5-20251001-v1:0`) automatically routes requests across multiple AWS regions to bypass local capacity limits.
  2. If upstream Bedrock fails, the frontend displays an inline reassuring message: *"Service busy — please try again in a moment."*

### 4. Rollback Procedure
If a regression slips into production:
```bash
git revert HEAD
git push origin main
```
GitHub Actions automatically builds and redeploys the previous known-good state in ~2 minutes without downtime.

### 5. Model Deprecation & Migration Plan
- The foundation model is pinned to an immutable snapshot: `global.anthropic.claude-haiku-4-5-20251001-v1:0` (never floating `:latest`).
- When Anthropic announces deprecation of a snapshot:
  1. Update `MODEL_ID` in `infra/template.yaml` (1-line change).
  2. Run the offline test suite `python scripts/patient_regression.py` and smoke tests.
  3. Deploy to a staging stack, verify trilingual prompt adherence, and promote to `main`.

### 6. Safe Decommissioning / Shutdown Procedure
To cleanly tear down the entire application and avoid recurring charges:
```bash
sam delete --stack-name smartmed-cycle --region ap-southeast-1
```

