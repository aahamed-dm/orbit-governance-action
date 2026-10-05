"""Read Action inputs from INPUT_* env vars (composite wiring)."""

from __future__ import annotations

import os

from orbit_governance_action.config import ORBIT_MCP_URL
from orbit_governance_action.models import RunOptions


def _require_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _parse_bool(raw: str, default: bool) -> bool:
    text = (raw or "").strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw!r}")


def read_run_options() -> RunOptions:
    orbit_governance_key = _require_env("INPUT_ORBIT_GOVERNANCE_KEY")
    fail_on_required = _parse_bool(os.environ.get("INPUT_FAIL_ON_REQUIRED", "true"), True)
    source = (os.environ.get("INPUT_SOURCE") or "ci").strip().lower()
    commit_sha = (os.environ.get("GITHUB_SHA") or "").strip()
    run_id = (os.environ.get("GITHUB_RUN_ID") or "").strip()
    scan_id = f"gha-{run_id}" if run_id else None

    if source not in {"ci", "local"}:
        raise ValueError(f"Invalid source '{source}' (expected ci|local)")
    if source == "ci" and not commit_sha:
        raise ValueError("GITHUB_SHA is required when source is ci")

    return RunOptions(
        orbit_mcp_url=ORBIT_MCP_URL,
        orbit_governance_key=orbit_governance_key,
        fail_on_required=fail_on_required,
        source=source,
        commit_sha=commit_sha,
        scan_id=scan_id,
    )
