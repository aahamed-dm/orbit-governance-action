"""Typed models for the governance Action run."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    orbit_mcp_url: str
    orbit_governance_key: str
    ai_gateway_url: str
    ai_gateway_api_key: str
    ai_gateway_model: str
    fail_on_required: bool
    source: str
    commit_sha: str
    scan_id: str | None = None


class ChangedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    content: str
    truncated: bool = False


class ChangedFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_ref: str
    head_ref: str
    files: list[ChangedFile]
    truncated: bool = False


class ControlEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    findings: list[dict[str, Any]] = Field(default_factory=list)


class NormalizedContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    gov_framework_id: str
    tier: str
    lifecycle: str
    framework_name: str
    controls: list[dict[str, Any]]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_key: str
    passed: bool
    findings: list[dict[str, Any]]


class EvidenceBatchSubmit(BaseModel):
    model_config = ConfigDict(frozen=True)

    gov_framework_id: str
    items: list[EvidenceItem]
    source: str
    evidence_type: str
    commit_sha: str | None = None
    scan_id: str | None = None
