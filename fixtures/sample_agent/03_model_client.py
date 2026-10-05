# Fixture 3/3 — DLP, approved gateway/model, secrets (DEV-02, RUN-01, IAM-04, MOD-01).
from __future__ import annotations

import os
import re
from typing import Any

import urllib.request

# Approved model gateway — no direct provider calls (RUN-01, MOD-01).
MODEL_GATEWAY_URL = os.environ.get(
    "AI_GATEWAY_URL",
    "https://dm-litellm-service.example.run.app/v1/chat/completions",
)
APPROVED_MODELS = {"gemini/gemini-2.0-flash", "openai/gpt-4o-mini"}
DEFAULT_MODEL = "gemini/gemini-2.0-flash"

# Secrets come from the enterprise secret manager / env injection (IAM-04).
# Never hardcode keys in source; never put secrets into prompts.
def load_gateway_api_key() -> str:
    key = os.environ.get("AI_GATEWAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("AI_GATEWAY_API_KEY missing from secret manager / env")
    return key


RESTRICTED_PATTERNS = [
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),  # crude PAN-like
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
    re.compile(r"(?i)sk-[a-z0-9]{10,}"),  # api key-like
]


def pre_model_dlp(text: str) -> str:
    """Deterministic pre-model filtering before gateway invoke (DEV-02)."""
    redacted = text
    for pattern in RESTRICTED_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    if "[REDACTED]" in redacted and redacted.count("[REDACTED]") > 3:
        raise ValueError("Request blocked by pre-model DLP policy")
    return redacted


def call_model(messages: list[dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    if model not in APPROVED_MODELS:
        raise ValueError(f"Model '{model}' is not in APPROVED_MODELS")

    sanitized_messages: list[dict[str, str]] = []
    for message in messages:
        content = message.get("content", "")
        role = message.get("role", "user")
        if role == "system":
            sanitized_messages.append({"role": role, "content": content})
        else:
            sanitized_messages.append(
                {"role": role, "content": pre_model_dlp(content)}
            )

    body = _encode_chat_body(model=model, messages=sanitized_messages)
    request = urllib.request.Request(
        MODEL_GATEWAY_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {load_gateway_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _encode_chat_body(model: str, messages: list[dict[str, str]]) -> bytes:
    # Minimal JSON encoder kept local for the fixture (no third-party deps).
    parts: list[str] = []
    for message in messages:
        role = _json_str(message["role"])
        content = _json_str(message["content"])
        parts.append(f'{{"role":{role},"content":{content}}}')
    joined = ",".join(parts)
    return (
        f'{{"model":{_json_str(model)},"messages":[{joined}]}}'
    ).encode("utf-8")


def _json_str(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


# Optional kill-switch hook (RUN-04 signal in code; still incomplete vs full ops evidence).
CAPABILITY_ENABLED = os.environ.get("SALES_ASSIST_ENABLED", "true").lower() == "true"


def assert_capability_enabled() -> None:
    if not CAPABILITY_ENABLED:
        raise RuntimeError("Sales Assist suspended via SALES_ASSIST_ENABLED=false")
