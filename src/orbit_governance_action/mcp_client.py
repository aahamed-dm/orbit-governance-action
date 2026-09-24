"""Minimal streamable-HTTP MCP client for dm-orbit-mcp."""

from __future__ import annotations

import json
from typing import Any

import httpx

from orbit_governance_action.config import (
    CLIENT_NAME,
    CLIENT_VERSION,
    MCP_PROTOCOL_VERSION,
)


def parse_sse_json_payloads(text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in text.split("\n\n"):
        data_lines = [
            line[5:].lstrip()
            for line in block.split("\n")
            if line.startswith("data:")
        ]
        if not data_lines:
            continue
        joined = "\n".join(data_lines).strip()
        if not joined or joined == "[DONE]":
            continue
        payloads.append(json.loads(joined))
    return payloads


def read_json_rpc_messages(response: httpx.Response) -> list[dict[str, Any]]:
    content_type = (response.headers.get("content-type") or "").lower()
    text = response.text
    if not text.strip():
        return []
    if (
        "text/event-stream" in content_type
        or "event:" in text
        or "data:" in text
    ):
        return parse_sse_json_payloads(text)
    parsed = json.loads(text)
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    raise ValueError(f"Unexpected MCP response JSON type: {type(parsed).__name__}")


def pick_result_for_id(
    messages: list[dict[str, Any]],
    request_id: int,
) -> Any:
    match = next(
        (
            message
            for message in messages
            if isinstance(message, dict) and message.get("id") == request_id
        ),
        None,
    )
    if match is None:
        raise RuntimeError(f"MCP response missing result for id={request_id}")
    if "error" in match and match["error"] is not None:
        raise RuntimeError(f"MCP JSON-RPC error: {json.dumps(match['error'])}")
    return match.get("result")


def coerce_tool_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        raise RuntimeError("MCP tool string payload did not parse to an object")
    raise RuntimeError(f"Unexpected MCP tool payload type: {type(value).__name__}")


def extract_tool_object(tool_result: Any) -> dict[str, Any]:
    if isinstance(tool_result, dict) and tool_result.get("structuredContent") is not None:
        return coerce_tool_payload(tool_result["structuredContent"])

    content = tool_result.get("content") if isinstance(tool_result, dict) else None
    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ]
        if text_parts:
            return coerce_tool_payload("\n".join(text_parts))

    if isinstance(tool_result, dict):
        return tool_result

    raise RuntimeError(
        f"Unable to parse MCP tool result: {json.dumps(tool_result)[:400]}"
    )


class OrbitMcpClient:
    """One MCP session: initialize once, then call tools."""

    def __init__(self, mcp_url: str, governance_key: str) -> None:
        self.mcp_url = mcp_url
        self.governance_key = governance_key
        self.session_id: str | None = None
        self.next_id = 1
        self.http = httpx.Client(timeout=120.0)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> OrbitMcpClient:
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def initialize(self) -> None:
        request_id = self.next_id
        self.next_id += 1
        messages, session_id = self._post_json_rpc(
            method="initialize",
            params={
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": CLIENT_NAME,
                    "version": CLIENT_VERSION,
                },
            },
            request_id=request_id,
        )
        self.session_id = session_id
        pick_result_for_id(messages, request_id)

        self._post_json_rpc(
            method="notifications/initialized",
            params={},
            request_id=None,
        )

    def call_tool(
        self,
        tool_name: str,
        tool_arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        messages, session_id = self._post_json_rpc(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": tool_arguments or {},
            },
            request_id=request_id,
        )
        if session_id:
            self.session_id = session_id

        result = pick_result_for_id(messages, request_id)
        if isinstance(result, dict) and result.get("isError"):
            raise RuntimeError(
                f"MCP tool {tool_name} returned isError: {json.dumps(result)}"
            )

        payload = extract_tool_object(result)
        if payload.get("error"):
            raise RuntimeError(
                f"MCP tool {tool_name} failed: {json.dumps(payload)}"
            )
        return payload

    def _post_json_rpc(
        self,
        method: str,
        params: dict[str, Any],
        request_id: int | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.governance_key}",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        if request_id is None:
            body: dict[str, Any] = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        else:
            body = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }

        response = self.http.post(self.mcp_url, headers=headers, json=body)
        next_session = response.headers.get("mcp-session-id") or self.session_id

        if response.status_code >= 400:
            raise RuntimeError(
                f"MCP HTTP {response.status_code} for {method}: {response.text[:400]}"
            )

        if request_id is None:
            return [], next_session

        return read_json_rpc_messages(response), next_session
