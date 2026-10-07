# SmartMed Cycle — Backend (Stage 1 placeholders)

These files are **declared, non-deploying placeholders**. Nothing here runs in
Stage 1.

## What this is

`app.py` contains Python Lambda handler **stubs**. Their names mirror the
frontend service seam in `frontend/src/js/services/index.js` one-to-one:

| Frontend service (`frontend/src/js/services/index.js`) | Backend stub (`app.py`) |
| ---------------------------------------------- | ---------------------------- |
| `extractFromPhoto`                             | `extract_from_photo`         |
| `buildMedicineCard`                            | `build_medicine_card`        |
| `buildPrecautionsSummary`                      | `build_precautions_summary`  |
| `chatRespond`                                  | `chat_respond`               |
| `prepareReturnPlan`                            | `prepare_return_plan`        |

Each stub returns a clearly-marked `not_implemented` response (HTTP 501) with a
note that real inference arrives in **Stage 3** behind the same handler name.

## Stage 1 facts

- **Not executed in Stage 1.** The local Python install is broken (fails to
  launch), and there is no deploy. These stubs are not run, imported, or
  validated locally.
- **No live AWS / Bedrock, no network.** The stubs make no calls. `boto3` is
  listed in `requirements.txt` for the Stage 3 runtime but is **not imported**
  by the Stage 1 stubs.
- **No secrets.** No account IDs, ARNs, keys, or credentials appear in any
  backend file.

## Honesty, kept consistent with the demo frontend

The stubs never pretend work was done. A placeholder is openly a placeholder:
no real OCR, no "safe"/"no interactions found" claims (absence of a note is not
a safety clearance), and no live directory search for return facilities.

## Stage 3 (later)

Stage 3 will implement real inference (AWS Lambda + Amazon Bedrock) behind
these exact handler names, wired through the SAM template in
`infra/template.yaml` and the service seam in
`frontend/src/js/services/index.js`. The shared request/response shapes live in
`schemas.py`; the Bedrock client wrapper lives in `bedrock_service.py` (both are
Stage 1 placeholders).
