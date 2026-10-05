"""Unit tests for Orbit governance Action helpers."""

from __future__ import annotations

from orbit_governance_action.changed_files import is_likely_text_path
from orbit_governance_action.config import ORBIT_MCP_URL
from orbit_governance_action.mcp_client import extract_tool_object, parse_sse_json_payloads


def test_orbit_mcp_url_is_hardcoded() -> None:
    assert ORBIT_MCP_URL == "https://dm-orbit-mcp-444791763526.us-central1.run.app/mcp"


def test_is_likely_text_path() -> None:
    assert is_likely_text_path("src/agent.py") is True
    assert is_likely_text_path("logo.png") is False


def test_parse_sse_json_payloads() -> None:
    payloads = parse_sse_json_payloads('data: {"id": 1, "result": {"ok": true}}\n\n')
    assert payloads[0]["id"] == 1


def test_extract_tool_object_from_text_content() -> None:
    result = extract_tool_object(
        {"content": [{"type": "text", "text": '{"status": "ok"}'}]}
    )
    assert result["status"] == "ok"
