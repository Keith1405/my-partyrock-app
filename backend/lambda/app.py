"""SmartMed Cycle — Lambda handlers.

Handler names mirror the frontend service seam
(``frontend/src/js/services/index.js``):

    extractFromPhoto        -> extract_from_photo
    buildMedicineCard       -> build_medicine_card   (IMPLEMENTED: typed entry + Bedrock)
    buildPrecautionsSummary -> build_precautions_summary
    chatRespond             -> chat_respond
    prepareReturnPlan       -> prepare_return_plan

Honesty rules: handlers return structured error envelopes (never a fabricated
success). ``build_medicine_card`` uses the configured Amazon Bedrock text model via
``bedrock_service``; the others remain honest 501 placeholders until their stages.
"""

import json
import logging
import os
import re
import uuid

import schemas
import bedrock_service

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Allowed browser origin for CORS. Set ALLOWED_ORIGIN in the Lambda env (SAM parameter).
# Falls back to "*" ONLY if unset, so local testing works; set it explicitly in deploys.
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


# ---------------------------------------------------------------------------
# Envelope + event helpers
# ---------------------------------------------------------------------------

def _response(status_code, body):
    return {"statusCode": status_code, "headers": dict(_CORS_HEADERS), "body": json.dumps(body)}


def _ok(data, request_id, provenance="liveModel"):
    return _response(200, {
        "ok": True, "status": "success", "data": data,
        "requestId": request_id, "sourceProvenance": provenance,
    })


# Map typed error codes to HTTP status.
_STATUS = {
    "validation": 400,
    "configuration": 503,
    "model_unavailable": 502,
    "rate_limited": 429,
    "timeout": 504,
    "internal": 500,
    "not_implemented": 501,
}


def _err(code, message, request_id, http_status=None):
    status = http_status or _STATUS.get(code, 500)
    return _response(status, {
        "ok": False, "status": "error",
        "error": {"code": code, "message": message},
        "requestId": request_id, "sourceProvenance": "none",
    })


def _request_id(payload):
    rid = payload.get("requestId") if isinstance(payload, dict) else None
    if isinstance(rid, str) and rid.strip():
        return rid.strip()[:64]
    return "req-" + uuid.uuid4().hex[:12]


def _parse_body(event):
    """Return the parsed JSON body from an API Gateway (HTTP API / REST) event."""
    if event is None:
        return {}
    if isinstance(event, dict) and "body" in event:
        raw = event.get("body")
        if raw is None:
            return {}
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None  # signals malformed JSON
    # Allow direct invocation with a plain dict payload (tests).
    if isinstance(event, dict):
        return event
    return None


def _is_preflight(event):
    if not isinstance(event, dict):
        return False
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )
    return method == "OPTIONS"


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text):
    """Parse a JSON object from model text, tolerating code fences / stray prose."""
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    m = _JSON_OBJECT_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Section 1 — Medicine Card (typed entry, real Bedrock)
# ---------------------------------------------------------------------------

def build_medicine_card(event=None, context=None):
    """Build a structured Medicine Card from the patient's TYPED medicine details.

    Empty input never generates anything (validation error). Missing strength/dose/
    frequency/duration stay "Not provided" — never inferred from the name.
    """
    if _is_preflight(event):
        return _response(204, {})

    payload = _parse_body(event)
    if payload is None:
        return _err("validation", "Request body was not valid JSON.", "req-badbody")

    request_id = _request_id(payload)
    details = payload.get("details") if isinstance(payload, dict) else None
    lang = payload.get("lang") if isinstance(payload, dict) else "en"
    if lang not in schemas.LANGUAGES:
        lang = "en"

    # 1) Empty / whitespace-only input must NOT generate anything.
    if not isinstance(details, str) or not details.strip():
        return _err("validation",
                    "Type the medicine name and any label instructions first.",
                    request_id)
    details = details.strip()
    if len(details) > schemas.MAX_DETAILS_CHARS:
        details = details[: schemas.MAX_DETAILS_CHARS]

    # 2) Call the configured Bedrock text model.
    try:
        text = bedrock_service.invoke_text(
            schemas.medicine_card_user_prompt(details, lang),
            system=schemas.medicine_card_system_prompt(),
            max_tokens=bedrock_service.MAX_OUTPUT_TOKENS,
            temperature=0.0,
        )
    except bedrock_service.BedrockConfigError as exc:
        logger.error("Bedrock config error: %s", exc)
        return _err("configuration",
                    "The medicine service is not fully configured. Please try again later.",
                    request_id)
    except bedrock_service.BedrockUnavailable as exc:
        logger.warning("Bedrock unavailable (%s): %s", getattr(exc, "code", "?"), exc)
        return _err(getattr(exc, "code", "model_unavailable"),
                    "The medicine service is temporarily unavailable. Please try again.",
                    request_id)
    except Exception as exc:  # noqa: BLE001 - last-resort guard, no detail leak
        logger.exception("Unexpected error invoking model")
        return _err("internal", "Something went wrong building the Medicine Card.", request_id)

    # 3) Parse + validate the model output into the exact render shape.
    raw = _extract_json_object(text)
    card = schemas.validate_medicine_card(raw) if raw is not None else None
    if card is None:
        logger.warning("Model output failed Medicine Card validation.")
        return _err("internal",
                    "Could not read a Medicine Card from the response. Please try again.",
                    request_id)

    return _ok(card, request_id, provenance="liveModel")


# ---------------------------------------------------------------------------
# Honest placeholders for the services wired in later stages
# ---------------------------------------------------------------------------

def _not_implemented(service_name):
    rid = "req-" + uuid.uuid4().hex[:12]
    return _response(501, {
        "ok": False, "status": "error",
        "error": {"code": "not_implemented",
                  "message": service_name + " is not connected yet."},
        "requestId": rid, "sourceProvenance": "none",
    })


def extract_from_photo(event=None, context=None):
    if _is_preflight(event):
        return _response(204, {})
    return _not_implemented("Medicine photo extraction")


def build_precautions_summary(event=None, context=None):
    if _is_preflight(event):
        return _response(204, {})
    return _not_implemented("Precautions")


def chat_respond(event=None, context=None):
    if _is_preflight(event):
        return _response(204, {})
    return _not_implemented("Chat")


def prepare_return_plan(event=None, context=None):
    if _is_preflight(event):
        return _response(204, {})
    return _not_implemented("Return planning")
