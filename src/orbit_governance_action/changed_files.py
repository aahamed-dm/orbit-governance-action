"""Collect capped changed files for the current GitHub event."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from orbit_governance_action.config import (
    MAX_CHANGED_FILES,
    MAX_FILE_BYTES,
    MAX_TOTAL_DIFF_BYTES,
)
from orbit_governance_action.models import ChangedFile, ChangedFilesResult

BLOCKED_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".lock",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)


def run_git(args: list[str], cwd: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def is_likely_text_path(file_path: str) -> bool:
    lower = file_path.lower()
    return not any(lower.endswith(ext) for ext in BLOCKED_EXTENSIONS)


def resolve_diff_range(
    event_name: str,
    event_path: str | None,
    commit_sha: str,
    workspace: str,
) -> tuple[str, str]:
    head_ref = commit_sha or "HEAD"

    if event_path and Path(event_path).is_file():
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        if event_name == "pull_request":
            pull_request = event.get("pull_request") or {}
            base = pull_request.get("base") or {}
            base_sha = base.get("sha")
            if base_sha:
                return str(base_sha), head_ref
        if event_name == "push":
            before = event.get("before")
            if before and not set(str(before)) <= {"0"}:
                return str(before), head_ref

    try:
        run_git(["rev-parse", "HEAD~1"], workspace)
        return "HEAD~1", "HEAD"
    except subprocess.CalledProcessError:
        return "", head_ref


def list_changed_paths(workspace: str, base_ref: str, head_ref: str) -> list[str]:
    if not base_ref:
        stdout = run_git(["ls-files"], workspace)
    else:
        stdout = run_git(
            ["diff", "--name-only", "--diff-filter=ACMRT", base_ref, head_ref],
            workspace,
        )
    paths = [line.strip() for line in stdout.splitlines() if line.strip()]
    return paths[:MAX_CHANGED_FILES]


def collect_from_fixture_dir(fixture_dir: str) -> ChangedFilesResult:
    """Local/dev: treat every text file under fixture_dir as the change set."""
    root = Path(fixture_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"fixture dir not found: {fixture_dir}")

    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if is_likely_text_path(relative):
            paths.append(relative)
        if len(paths) >= MAX_CHANGED_FILES:
            break

    return _read_paths_as_changed_files(
        workspace=str(root),
        paths=paths,
        base_ref="fixture",
        head_ref="local",
    )


def _read_paths_as_changed_files(
    workspace: str,
    paths: list[str],
    base_ref: str,
    head_ref: str,
) -> ChangedFilesResult:
    files: list[ChangedFile] = []
    total_bytes = 0
    truncated = False
    workspace_root = Path(workspace).resolve()

    for relative_path in paths:
        if ".." in Path(relative_path).parts:
            continue
        absolute_path = (workspace_root / relative_path).resolve()
        try:
            absolute_path.relative_to(workspace_root)
        except ValueError:
            continue
        if absolute_path.is_symlink():
            continue
        if not is_likely_text_path(relative_path):
            continue
        try:
            content = absolute_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        file_truncated = False
        encoded_size = len(content.encode("utf-8"))
        if encoded_size > MAX_FILE_BYTES:
            content = content.encode("utf-8")[:MAX_FILE_BYTES].decode(
                "utf-8",
                errors="ignore",
            )
            file_truncated = True
            truncated = True

        next_total = total_bytes + len(content.encode("utf-8"))
        if next_total > MAX_TOTAL_DIFF_BYTES:
            truncated = True
            break

        total_bytes = next_total
        files.append(
            ChangedFile(
                path=relative_path,
                content=content,
                truncated=file_truncated,
            )
        )

    return ChangedFilesResult(
        base_ref=base_ref,
        head_ref=head_ref,
        files=files,
        truncated=truncated,
    )


def collect_changed_files(
    workspace: str,
    event_name: str,
    event_path: str | None,
    commit_sha: str,
) -> ChangedFilesResult:
    fixture_dir = (os.environ.get("ORBIT_ACTION_FIXTURE_DIR") or "").strip()
    if fixture_dir:
        return collect_from_fixture_dir(fixture_dir)

    base_ref, head_ref = resolve_diff_range(
        event_name=event_name,
        event_path=event_path,
        commit_sha=commit_sha,
        workspace=workspace,
    )
    paths = list_changed_paths(workspace, base_ref, head_ref)
    return _read_paths_as_changed_files(
        workspace=workspace,
        paths=paths,
        base_ref=base_ref,
        head_ref=head_ref,
    )
