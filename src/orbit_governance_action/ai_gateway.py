"""OpenAI-compatible chat client for customer LiteLLM / AI gateway."""

from __future__ import annotations

import json
from typing import Any

import httpx


def normalize_gateway_base_url(gateway_url: str) -> str:
    base = (gateway_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("ai_gateway_url is empty")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


def chat_completion(
    ai_gateway_url: str,
    ai_gateway_api_key: str,
    ai_gateway_model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> str:
    base = normalize_gateway_base_url(ai_gateway_url)
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {
        "model": ai_gateway_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ai_gateway_api_key}",
            },
            json=payload,
        )

    text = response.text
    try:
        body = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"AI gateway returned non-JSON (status {response.status_code}): {text[:300]}"
        ) from exc

    if response.status_code >= 400:
        raise RuntimeError(
            "AI gateway chat.completions failed "
            f"({response.status_code}): {json.dumps(body)[:500]}"
        )

    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("AI gateway returned empty choices")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI gateway returned empty message content")
    return content
