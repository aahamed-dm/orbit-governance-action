# Fixture 2/3 — tool allowlist, schemas, human approval (DEV-03, DEV-04, DEV-05, DEV-06).
from __future__ import annotations

from typing import Any

# Explicit tool allowlist (DEV-03).
ALLOWED_TOOLS = {
    "draft_email": {
        "requires_human_approval": False,
        "input_schema": {"to": "str", "subject": "str", "body": "str"},
        "output_schema": {"status": "str", "draft_id": "str"},
    },
    "lookup_crm_notes": {
        "requires_human_approval": False,
        "input_schema": {"account_id": "str"},
        "output_schema": {"notes": "list"},
    },
    "send_email": {
        "requires_human_approval": True,
        "input_schema": {"to": "str", "subject": "str", "body": "str", "approval_id": "str"},
        "output_schema": {"status": "str", "message_id": "str"},
    },
}

# Approved enterprise context sources only (DEV-06).
APPROVED_DATA_SOURCES = [
    "crm://salesforce/accounts",
    "kb://deepmodel/sales-playbook",
]


class AuthorizationError(Exception):
    pass


class SchemaError(Exception):
    pass


def _validate_schema(payload: dict[str, Any], schema: dict[str, str]) -> None:
    missing = [key for key in schema if key not in payload]
    if missing:
        raise SchemaError(f"Missing required fields: {missing}")


def require_human_approval(tool_name: str, payload: dict[str, Any]) -> None:
    """Human authorization is enforced outside the model (DEV-05)."""
    tool = ALLOWED_TOOLS[tool_name]
    if not tool["requires_human_approval"]:
        return
    approval_id = str(payload.get("approval_id") or "").strip()
    if not approval_id.startswith("APPROVAL-"):
        raise AuthorizationError(
            f"{tool_name} blocked: missing verified human approval_id"
        )


def run_tool(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Deterministic tool boundary with allowlist + schema checks (DEV-03/04)."""
    if name not in ALLOWED_TOOLS:
        raise AuthorizationError(f"Tool '{name}' is not on ALLOWED_TOOLS")

    tool = ALLOWED_TOOLS[name]
    _validate_schema(payload, tool["input_schema"])
    require_human_approval(name, payload)

    if name == "draft_email":
        return {"status": "drafted", "draft_id": "draft-123"}
    if name == "lookup_crm_notes":
        return {"notes": ["QBR scheduled", "Champion engaged"]}
    if name == "send_email":
        return {"status": "sent", "message_id": "msg-456"}
    raise AuthorizationError(f"Unhandled allowlisted tool: {name}")
