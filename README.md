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

## Smoke test

`scripts/smoke_test.py` boots each backend on a free port and checks:

- the app imports and starts,
- `OPTIONS /` returns 200 with the CORS header,
- `POST /` streams a `text/plain` response,
- the **413 payload-too-large** guard triggers on an oversized body.

```bash
python scripts/smoke_test.py                 # all five
python scripts/smoke_test.py medicine_card   # just one
```

Without AWS credentials the apps still boot and stream an inline `⚠️ Error:`
message; the harness treats a reachable, streaming route as PASS, so it gates on
boot/routing/guards rather than on live Bedrock. The GitHub Actions **`smoke`**
job runs this on every push and the **`deploy`** job depends on it — a boot or
routing regression fails the pipeline before anything is deployed.

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
```
