"""Map MCP capability-context payloads to batch submit_control_evidence args."""

from __future__ import annotations

from typing import Any

from orbit_governance_action.config import EVIDENCE_TYPE
from orbit_governance_action.models import (
    ControlEvaluation,
    EvidenceItem,
    EvidenceBatchSubmit,
    NormalizedContext,
)


def normalize_capability_context(context: dict[str, Any]) -> NormalizedContext:
    if not isinstance(context, dict):
        raise ValueError("capability context is missing")

    gov_framework_id = str(context.get("gov_framework_id") or "").strip()
    if not gov_framework_id:
        raise ValueError("capability context missing gov_framework_id")

    controls = context.get("controls")
    if not isinstance(controls, list):
        controls = []

    framework = context.get("framework")
    if isinstance(framework, dict) and isinstance(framework.get("name"), str):
        framework_name = framework["name"]
    else:
        framework_name = "unknown"

    return NormalizedContext(
        gov_framework_id=gov_framework_id,
        tier=str(context.get("tier") or ""),
        lifecycle=str(context.get("lifecycle") or ""),
        framework_name=framework_name,
        controls=controls,
    )


def is_evaluable_control(control: dict[str, Any]) -> bool:
    applicability = str(control.get("applicability") or "").lower()
    return applicability in {"required", "recommended"}


def build_evidence_item(
    control: dict[str, Any],
    evaluation: ControlEvaluation,
) -> EvidenceItem:
    control_key = str(control.get("control_key") or "").strip()
    if not control_key:
        raise ValueError("control_key is required for evidence submit")
    return EvidenceItem(
        control_key=control_key,
        passed=bool(evaluation.passed),
        findings=list(evaluation.findings),
    )


def build_evidence_batch(
    gov_framework_id: str,
    items: list[EvidenceItem],
    source: str,
    commit_sha: str,
    scan_id: str | None,
) -> EvidenceBatchSubmit:
    if not items:
        raise ValueError("evidence batch requires at least one item")
    resolved_commit = commit_sha if source == "ci" else (commit_sha or None)
    return EvidenceBatchSubmit(
        gov_framework_id=gov_framework_id,
        items=items,
        source=source,
        evidence_type=EVIDENCE_TYPE,
        commit_sha=resolved_commit,
        scan_id=scan_id,
    )


def evidence_batch_to_tool_arguments(batch: EvidenceBatchSubmit) -> dict[str, Any]:
    tool_arguments: dict[str, Any] = {
        "gov_framework_id": batch.gov_framework_id,
        "evidence_type": batch.evidence_type,
        "source": batch.source,
        "items": [
            {
                "control_key": item.control_key,
                "passed": item.passed,
                "findings": item.findings,
            }
            for item in batch.items
        ],
    }
    if batch.commit_sha:
        tool_arguments["commit_sha"] = batch.commit_sha
    if batch.scan_id:
        tool_arguments["scan_id"] = batch.scan_id
    return tool_arguments
