"""Unit tests for Orbit governance Action helpers."""

from __future__ import annotations

from orbit_governance_action.ai_gateway import normalize_gateway_base_url
from orbit_governance_action.changed_files import is_likely_text_path
from orbit_governance_action.config import CONTROLS_PER_GATEWAY_BATCH, ORBIT_MCP_URL
from orbit_governance_action.evaluate_controls import (
    chunk_controls,
    map_batch_results,
    parse_json_object,
)
from orbit_governance_action.evidence import (
    build_evidence_batch,
    build_evidence_item,
    evidence_batch_to_tool_arguments,
    is_evaluable_control,
    normalize_capability_context,
)
from orbit_governance_action.mcp_client import extract_tool_object, parse_sse_json_payloads
from orbit_governance_action.models import ControlEvaluation


def test_orbit_mcp_url_is_hardcoded() -> None:
    assert ORBIT_MCP_URL == "https://dm-orbit-mcp-444791763526.us-central1.run.app/mcp"


def test_normalize_gateway_base_url_appends_v1() -> None:
    assert (
        normalize_gateway_base_url("https://gateway.example.com")
        == "https://gateway.example.com/v1"
    )


def test_normalize_gateway_base_url_keeps_v1() -> None:
    assert (
        normalize_gateway_base_url("https://gateway.example.com/v1/")
        == "https://gateway.example.com/v1"
    )


def test_normalize_capability_context() -> None:
    context = {
        "gov_framework_id": "33333333-3333-4333-8333-333333333333",
        "tier": "A",
        "lifecycle": "IN_DEVELOPMENT",
        "framework": {"name": "DeepModel AI Governance Framework"},
        "controls": [
            {"control_key": "DEV-01", "applicability": "required"},
            {"control_key": "RUN-02", "applicability": "recommended"},
            {"control_key": "X-99", "applicability": "not_required"},
        ],
    }
    normalized = normalize_capability_context(context)
    assert normalized.gov_framework_id == context["gov_framework_id"]
    assert normalized.framework_name == "DeepModel AI Governance Framework"
    evaluable = [c for c in normalized.controls if is_evaluable_control(c)]
    assert [c["control_key"] for c in evaluable] == ["DEV-01", "RUN-02"]


def test_build_evidence_batch() -> None:
    item = build_evidence_item(
        control={"control_key": "DEV-01", "applicability": "required"},
        evaluation=ControlEvaluation(
            passed=True,
            findings=[{"severity": "info", "message": "ok"}],
        ),
    )
    batch = build_evidence_batch(
        gov_framework_id="33333333-3333-4333-8333-333333333333",
        items=[item],
        source="ci",
        commit_sha="deadbeef",
        scan_id="gha-1",
    )
    assert batch.evidence_type == "orbit-tooled"
    assert batch.commit_sha == "deadbeef"
    args = evidence_batch_to_tool_arguments(batch)
    assert args["gov_framework_id"] == batch.gov_framework_id
    assert args["items"][0]["control_key"] == "DEV-01"
    assert args["commit_sha"] == "deadbeef"


def test_chunk_and_map_batch_results() -> None:
    assert CONTROLS_PER_GATEWAY_BATCH == 10
    controls = [{"control_key": f"C-{index}"} for index in range(12)]
    batches = chunk_controls(controls)
    assert len(batches) == 2
    assert len(batches[0]) == 10
    assert len(batches[1]) == 2

    mapped = map_batch_results(
        {"results": [{"control_key": "DEV-01", "passed": True, "findings": []}]},
        [{"control_key": "DEV-01"}, {"control_key": "DEV-02"}],
    )
    assert mapped["DEV-01"].passed is True
    assert mapped["DEV-02"].passed is False

    mapped_bad = map_batch_results(
        {"results": [{"control_key": "DEV-01", "passed": "false", "findings": []}]},
        [{"control_key": "DEV-01"}],
    )
    assert mapped_bad["DEV-01"].passed is False


def test_parse_json_object_fenced() -> None:
    parsed = parse_json_object('```json\n{"results":[]}\n```')
    assert parsed == {"results": []}


def test_mcp_parsing_helpers() -> None:
    structured = extract_tool_object({"structuredContent": {"tier": "A", "controls": []}})
    assert structured["tier"] == "A"

    text_payload = extract_tool_object({"content": [{"type": "text", "text": '{"tier":"A"}'}]})
    assert text_payload["tier"] == "A"

    messages = parse_sse_json_payloads(
        'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    )
    assert messages[0]["result"]["ok"] is True


def test_is_likely_text_path() -> None:
    assert is_likely_text_path("src/app.py") is True
    assert is_likely_text_path("logo.png") is False
