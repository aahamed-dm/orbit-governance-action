"""GitHub Actions logging and output helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def info(message: str) -> None:
    print(message, flush=True)


def error(message: str) -> None:
    print(f"::error::{message}", flush=True)


def set_failed(message: str) -> None:
    error(message)
    raise SystemExit(1)


def set_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print(f"::notice::GITHUB_OUTPUT unset; {name}={value}", flush=True)
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def eprint(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
