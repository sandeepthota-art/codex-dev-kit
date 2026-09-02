#!/usr/bin/env python3
"""Run one delegated lane through an enforced read-only Codex CLI process."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence
from typing import TextIO

SANDBOX = "read-only"
APPROVAL_POLICY = "never"


class LaneError(RuntimeError):
    """Report a failure that must block the delegated lane."""


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the fixed read-only lane interface.

    Args:
        arguments: Optional command arguments. The process arguments are used
            when this value is ``None``.

    Returns:
        The required project root, model, and reasoning level.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", required=True)
    return parser.parse_args(arguments)


def read_packet(stream: TextIO) -> str:
    """Read one complete bounded lane packet.

    Args:
        stream: Text input that contains the packet.

    Returns:
        The packet, unchanged.

    Raises:
        LaneError: If the packet is empty.
    """
    packet = stream.read()
    if not packet.strip():
        raise LaneError("the delegated lane packet is empty")
    return packet


def build_command(arguments: argparse.Namespace) -> list[str]:
    """Build the enforced Codex CLI command.

    Args:
        arguments: The project root, model, and reasoning level.

    Returns:
        The complete command argument list.

    Raises:
        LaneError: If ``codex`` is not available on ``PATH``.
    """
    codex = shutil.which("codex")
    if codex is None:
        raise LaneError("codex is not available on PATH")
    return [
        codex,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--strict-config",
        "--disable",
        "multi_agent",
        "--disable",
        "hooks",
        "--sandbox",
        SANDBOX,
        "--model",
        arguments.model,
        "--config",
        f'model_reasoning_effort="{arguments.reasoning}"',
        "--config",
        f'approval_policy="{APPROVAL_POLICY}"',
        "--cd",
        arguments.project_root,
        "--color",
        "never",
        "-",
    ]


def run_lane(command: Sequence[str], packet: str) -> subprocess.CompletedProcess[str]:
    """Run one enforced read-only lane and capture its report.

    Args:
        command: The complete Codex CLI command.
        packet: The bounded lane packet for standard input.

    Returns:
        The successful process result with a nonempty report.

    Raises:
        LaneError: If the process cannot start, exits unsuccessfully, or
            returns no report.
    """
    try:
        result = subprocess.run(
            command,
            input=packet,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
        )
    except OSError as error:
        raise LaneError(f"codex could not start: {error}") from error
    if result.returncode != 0:
        diagnostic = result.stderr.strip() or result.stdout.strip()
        detail = diagnostic or f"codex exited with status {result.returncode}"
        raise LaneError(detail)
    if not result.stdout.strip():
        raise LaneError("codex returned no delegated lane report")
    return result


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the read-only lane command-line workflow.

    Args:
        arguments: Optional command arguments. The process arguments are used
            when this value is ``None``.

    Returns:
        Zero on success or two when enforced execution fails.
    """
    try:
        parsed = parse_arguments(arguments)
        packet = read_packet(sys.stdin)
        result = run_lane(build_command(parsed), packet)
    except LaneError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
