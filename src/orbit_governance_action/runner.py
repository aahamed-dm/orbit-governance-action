"""Orchestrate MCP context → AI evaluation → one batch evidence submit."""

from __future__ import annotations

import os

from orbit_governance_action.changed_files import (
    collect_changed_files,
    format_changed_files_for_prompt,
)
from orbit_governance_action.evaluate_controls import evaluate_controls_with_gateway
from orbit_governance_action.evidence import (
    build_evidence_batch,
    build_evidence_item,
    evidence_batch_to_tool_arguments,
    is_evaluable_control,
    normalize_capability_context,
)
from orbit_governance_action.github_io import info, set_failed, set_output
from orbit_governance_action.inputs import read_run_options
from orbit_governance_action.mcp_client import OrbitMcpClient
from orbit_governance_action.models import ControlEvaluation, EvidenceItem


def run() -> None:
    options = read_run_options()
    info(f"Orbit MCP URL: {options.orbit_mcp_url}")
    info(f"Evidence source={options.source} model={options.ai_gateway_model}")

    with OrbitMcpClient(
        mcp_url=options.orbit_mcp_url,
        governance_key=options.orbit_governance_key,
    ) as mcp:
        info("Calling MCP get_capability_context…")
        raw_context = mcp.call_tool("get_capability_context", {})
        context = normalize_capability_context(raw_context)
        evaluable = [control for control in context.controls if is_evaluable_control(control)]
        info(
            f"Context tier={context.tier} lifecycle={context.lifecycle} "
            f"controls={len(context.controls)} evaluable={len(evaluable)}"
        )
        set_output("tier", context.tier)

        workspace = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
        changed = collect_changed_files(
            workspace=workspace,
            event_name=os.environ.get("GITHUB_EVENT_NAME") or "",
            event_path=os.environ.get("GITHUB_EVENT_PATH"),
            commit_sha=options.commit_sha,
        )
        truncated_note = " (truncated)" if changed.truncated else ""
        info(
            f"Changed files={len(changed.files)} "
            f"range={changed.base_ref or '(none)'}..{changed.head_ref}{truncated_note}"
        )
        changed_files_text = format_changed_files_for_prompt(changed.files)

        info("Evaluating controls via AI gateway (batched)…")
        evaluations = evaluate_controls_with_gateway(
            controls=evaluable,
            changed_files_text=changed_files_text,
            framework_name=context.framework_name,
            tier=context.tier,
            ai_gateway_url=options.ai_gateway_url,
            ai_gateway_api_key=options.ai_gateway_api_key,
            ai_gateway_model=options.ai_gateway_model,
        )

        items: list[EvidenceItem] = []
        required_failed = 0

        for control in evaluable:
            control_key = str(control.get("control_key") or "")
            evaluation = evaluations.get(control_key) or ControlEvaluation(
                passed=False,
                findings=[
                    {"severity": "error", "message": "Missing evaluation result"},
                ],
            )

            applicability = str(control.get("applicability") or "").lower()
            if applicability == "required" and not evaluation.passed:
                required_failed += 1

            items.append(build_evidence_item(control=control, evaluation=evaluation))

        batch = build_evidence_batch(
            gov_framework_id=context.gov_framework_id,
            items=items,
            source=options.source,
            commit_sha=options.commit_sha,
            scan_id=options.scan_id,
        )
        tool_arguments = evidence_batch_to_tool_arguments(batch)

        info(
            f"Submitting batch evidence via MCP "
            f"({len(batch.items)} controls)…"
        )
        submit_result = mcp.call_tool("submit_control_evidence", tool_arguments)
        submitted_count = int(submit_result.get("submitted_count") or len(batch.items))

        set_output("controls_submitted", str(submitted_count))
        set_output("required_failed", str(required_failed))
        info(
            f"Done. submitted={submitted_count} required_failed={required_failed}"
        )

        if options.fail_on_required and required_failed > 0:
            set_failed(
                f"{required_failed} Required control(s) failed evidence checks"
            )
