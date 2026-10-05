"""
Local end-to-end smoke — same path as the GitHub composite Action.

Flow:
  1) MCP health
  2) Load fixture changed files
  3) MCP validate_changed_files → Orbit API (controls + LLM stub/live)

Paste your governance key in SECRETS below, then run:
  python scripts/run_local_action_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# PASTE SECRETS HERE (local test only — do not commit real values)
# ---------------------------------------------------------------------------
SECRETS = {
    "ORBIT_GOVERNANCE_KEY": "",  # Bearer key accepted by Orbit / dm-orbit-mcp
}

FAIL_ON_REQUIRED = "false"
SOURCE = "local"


def _apply_secrets() -> None:
    missing = [name for name, value in SECRETS.items() if not str(value).strip()]
    if missing:
        raise SystemExit(
            "Fill SECRETS in scripts/run_local_action_test.py before running.\n"
            f"Missing: {', '.join(missing)}"
        )

    os.environ["INPUT_ORBIT_GOVERNANCE_KEY"] = SECRETS["ORBIT_GOVERNANCE_KEY"].strip()
    os.environ["INPUT_FAIL_ON_REQUIRED"] = FAIL_ON_REQUIRED
    os.environ["INPUT_SOURCE"] = SOURCE


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_dir = repo_root / "fixtures" / "sample_agent"
    if not fixture_dir.is_dir():
        raise SystemExit(f"Fixture dir missing: {fixture_dir}")

    fixture_files = sorted(p.name for p in fixture_dir.glob("*.py"))
    print(f"Repo: {repo_root}")
    print(f"Fixture changed files ({len(fixture_files)}): {', '.join(fixture_files)}")

    _apply_secrets()

    output_file = Path(tempfile.gettempdir()) / "orbit-action-local-output.txt"
    output_file.write_text("", encoding="utf-8")

    os.environ["GITHUB_SHA"] = "local-smoke-sha"
    os.environ["GITHUB_RUN_ID"] = "local-smoke"
    os.environ["GITHUB_EVENT_NAME"] = "workflow_dispatch"
    os.environ["GITHUB_WORKSPACE"] = str(fixture_dir)
    os.environ["ORBIT_ACTION_FIXTURE_DIR"] = str(fixture_dir)
    os.environ["GITHUB_OUTPUT"] = str(output_file)

    sys.path.insert(0, str(repo_root / "src"))
    from orbit_governance_action.config import ORBIT_MCP_URL
    from orbit_governance_action.runner import run

    print(f"MCP URL: {ORBIT_MCP_URL}")
    print("Running Action runner…")
    run()
    print("GITHUB_OUTPUT:")
    print(output_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
