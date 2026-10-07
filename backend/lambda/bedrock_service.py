"""SmartMed Cycle — Amazon Bedrock client wrapper.

The single seam through which model calls flow. Region, model id, timeouts, retry
bounds and token limits are configured here once; they never leak into handler logic
or the frontend. Credentials come from the Lambda execution role via the standard
credential chain — never from committed values or the browser.

Uses the Bedrock **Converse** API, which is model-agnostic: the configured model id
(``BEDROCK_TEXT_MODEL_ID``) selects Claude / Nova / etc. without code changes. Bedrock
does NOT browse the internet; this wrapper performs no retrieval.
"""

import os
import json
import logging

logger = logging.getLogger()

# Env var NAMES only (values injected at deploy time via SAM parameters / Lambda env).
ENV_REGION = "AWS_REGION"               # reserved Lambda runtime variable (always set on Lambda)
ENV_BEDROCK_REGION = "BEDROCK_REGION"   # optional override if Bedrock lives in another region
ENV_TEXT_MODEL = "BEDROCK_TEXT_MODEL_ID"
ENV_VISION_MODEL = "BEDROCK_VISION_MODEL_ID"

# App limits (ours, not AWS facts). Tuned to stay within the synchronous API GW/Lambda deadline.
MAX_OUTPUT_TOKENS = 1024
READ_TIMEOUT_SECONDS = 25
CONNECT_TIMEOUT_SECONDS = 5
MAX_ATTEMPTS = 2  # one retry on transient failure; never retry auth/validation errors.


class BedrockConfigError(Exception):
    """Raised when required Bedrock configuration is missing."""


class BedrockUnavailable(Exception):
    """Raised when the model cannot be invoked (transient/service/throttling)."""
    def __init__(self, message, code="model_unavailable"):
        super().__init__(message)
        self.code = code


_client = None


def get_config():
    """Resolve region + model ids from the environment (one place)."""
    region = os.environ.get(ENV_BEDROCK_REGION) or os.environ.get(ENV_REGION)
    return {
        "region": region,
        "textModelId": os.environ.get(ENV_TEXT_MODEL),
        "visionModelId": os.environ.get(ENV_VISION_MODEL),
    }


def get_client():
    """Return a cached bedrock-runtime client built from the execution-role creds."""
    global _client
    if _client is not None:
        return _client

    cfg = get_config()
    if not cfg["region"]:
        raise BedrockConfigError("No AWS region configured (AWS_REGION/BEDROCK_REGION).")

    try:
        import boto3  # imported lazily so unit tests can run without boto3 installed
        from botocore.config import Config as BotoConfig
    except Exception as exc:  # pragma: no cover - import guard
        raise BedrockConfigError("boto3 is not available in the runtime: %s" % exc)

    boto_cfg = BotoConfig(
        region_name=cfg["region"],
        read_timeout=READ_TIMEOUT_SECONDS,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        retries={"max_attempts": 1, "mode": "standard"},  # we handle retry ourselves
    )
    _client = boto3.client("bedrock-runtime", config=boto_cfg)
    return _client


def invoke_text(prompt, *, system=None, max_tokens=MAX_OUTPUT_TOKENS, temperature=0.0):
    """Invoke the configured text model via the Converse API and return the text output.

    `prompt` and `system` are treated purely as DATA. Transient failures are retried once;
    throttling and service errors raise BedrockUnavailable; missing config raises
    BedrockConfigError. The caller maps these to typed API errors.
    """
    cfg = get_config()
    model_id = cfg["textModelId"]
    if not model_id:
        raise BedrockConfigError("No BEDROCK_TEXT_MODEL_ID configured.")

    client = get_client()

    kwargs = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": int(max_tokens), "temperature": float(temperature)},
    }
    if system:
        kwargs["system"] = [{"text": system}]

    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = client.converse(**kwargs)
            return _extract_text(resp)
        except Exception as exc:  # noqa: BLE001 - we classify below
            name = exc.__class__.__name__
            # Do NOT retry client-side errors (bad creds, access denied, validation).
            non_retryable = (
                "AccessDenied", "UnrecognizedClient", "ValidationException",
                "ResourceNotFound", "AuthFailure",
            )
            if any(n in name for n in non_retryable):
                raise BedrockUnavailable(
                    "Model access/validation error: %s" % name,
                    code="configuration" if "Access" in name or "Unrecognized" in name else "model_unavailable",
                )
            # Throttling / transient: retry once, then give up.
            last_exc = exc
            logger.warning("Bedrock converse attempt %d failed: %s", attempt, name)
            if attempt >= MAX_ATTEMPTS:
                code = "rate_limited" if "Throttl" in name else "model_unavailable"
                raise BedrockUnavailable("Model invocation failed: %s" % name, code=code)
    # Unreachable, but keep mypy/readers happy.
    raise BedrockUnavailable("Model invocation failed: %s" % last_exc)


def _extract_text(resp):
    """Pull the concatenated text out of a Converse response."""
    try:
        content = resp["output"]["message"]["content"]
        parts = [b.get("text", "") for b in content if isinstance(b, dict)]
        text = "".join(parts).strip()
    except Exception:  # pragma: no cover - defensive
        text = ""
    if not text:
        raise BedrockUnavailable("Model returned an empty response.", code="model_unavailable")
    return text


def invoke_vision(image_bytes, prompt, *, media_type=None, max_tokens=MAX_OUTPUT_TOKENS):
    """Vision/label extraction (separate stage). Not used by typed Medicine Card entry."""
    raise BedrockUnavailable("Vision extraction is not enabled in this stage.", code="model_unavailable")
