#!/usr/bin/env python3
"""Run the canonical project inspector from the Codex Kit plugin source."""

from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "codex-kit"
    / "skills"
    / "bootstrap"
    / "scripts"
    / "project.py"
)

runpy.run_path(str(SCRIPT), run_name="__main__")
