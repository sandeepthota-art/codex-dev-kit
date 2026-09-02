#!/usr/bin/env python3
"""Validate Codex Kit and consuming project structure."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import tomllib

VERSION = "0.6.0"
SKILLS = (
    "setup",
    "bootstrap",
    "commission",
    "launch",
    "portfolio",
    "auto-deliver",
    "auto-route-learnings",
)
HUMAN_SKILLS = ("setup", "bootstrap", "commission", "launch", "portfolio")
AUTO_SKILLS = ("auto-deliver", "auto-route-learnings")
REMOVED_SKILLS = (
    "project",
    "succession",
    "workstream",
    "route-work",
    "deliver-work",
    "route-learnings",
    "project-lead-succession",
    "portfolio-review",
)
AGENTS = {
    "luna_worker.toml": ("luna_worker", "gpt-5.6-luna", None),
    "terra_worker.toml": ("terra_worker", "gpt-5.6-terra", None),
}
REMOVED_AGENTS = ("project_lead.toml", "sol_reviewer.toml")
STE_SCREEN_FORBIDDEN = ("e.g.", "i.e.", "etc.", "please note", "simply")
LEGACY_BOOTSTRAPS = (
    "agentic-cos",
    "agentic-sdlc-kit",
    "agentic-vault",
    "agent-vault/agents/cos-load.md",
    "chief of staff",
    "chief-of-staff",
)
SETUP_ASSUMPTIONS = ("~/valve", "bnadimpalli", "github.com/bnadimpalli")
SETUP_PLACEHOLDERS = (
    "<codex-kit-repository-url>",
)
OPERATOR_COMMANDS = (
    "codex plugin marketplace add <codex-kit-repository-url>",
    "codex plugin marketplace upgrade codex-kit",
    "codex plugin add codex-kit@codex-kit",
    "$codex-kit:setup",
)
LEGACY_OPERATOR_SETUP = (
    "git clone",
    "/path/to/codex-kit",
    "python3 /path/to/codex-kit/tools/install.py",
    "codex plugin marketplace add /path/to/codex-kit",
)
REMOVED_VAULT_MARKERS = ("codex-vault", "vault-memory", "--vault-root", "codex_vault")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit-root", type=Path, default=Path("."))
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--version", action="store_true")
    return parser.parse_args()


def require(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing file: {path}")


def read_yaml_boolean(text: str, section: str, key: str) -> bool | None:
    """Read one unquoted Boolean from a simple top-level YAML section.

    Args:
        text: The YAML source text.
        section: The top-level section name.
        key: The Boolean field name in the section.

    Returns:
        The Boolean value, or ``None`` if the field is missing, duplicated, or
        invalid.
    """
    in_section = False
    section_lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_section = stripped == f"{section}:"
            continue
        if in_section:
            section_lines.append((indent, stripped))

    if not section_lines:
        return None
    direct_indent = min(indent for indent, _ in section_lines)
    values: list[bool] = []
    for indent, stripped in section_lines:
        if indent != direct_indent or ":" not in stripped:
            continue
        field, raw_value = stripped.split(":", 1)
        if field != key:
            continue
        value = raw_value.strip()
        if value == "true":
            values.append(True)
        elif value == "false":
            values.append(False)
        else:
            return None
    return values[0] if len(values) == 1 else None


def check_legacy_bootstraps(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in LEGACY_BOOTSTRAPS:
            if marker in lowered:
                errors.append(f"active legacy bootstrap reference found: {path}: {marker}")


def check_clean_git(root: Path, errors: list[str]) -> None:
    if not (root / ".git").exists():
        errors.append(f"release root is not a Git worktree: {root}")
        return
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        errors.append(f"cannot read Git status for release root: {root}")
    elif result.stdout.strip():
        errors.append(f"release root has uncommitted changes: {root}")


def check_asd_screen(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*.md"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for phrase in STE_SCREEN_FORBIDDEN:
            if phrase in lowered:
                errors.append(f"mechanical ASD-STE100 screen found {phrase!r}: {path}")


def check_removed_vault_references(root: Path, errors: list[str]) -> None:
    allowed_suffixes = {".json", ".md", ".py", ".toml", ".yaml", ".yml"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if ".git" in path.parts or "tests" in path.parts or path == Path(__file__).resolve():
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in REMOVED_VAULT_MARKERS:
            if marker in lowered:
                errors.append(f"removed Vault reference found: {path}: {marker}")


def check_kit(root: Path, errors: list[str]) -> None:
    """Validate the Codex Kit catalog and project-neutral source files.

    Args:
        root: The Codex Kit source root.
        errors: The validation error collector.
    """
    required = (
        "AGENTS.md",
        "README.md",
        ".agents/plugins/marketplace.json",
        "plugins/codex-kit/.codex-plugin/plugin.json",
        "plugins/codex-kit/references/operating-model.md",
        "plugins/codex-kit/references/script-documentation.md",
        "plugins/codex-kit/skills/setup/scripts/install.py",
        "plugins/codex-kit/skills/bootstrap/scripts/project.py",
        "tools/install.py",
        "tools/project.py",
        "tools/doctor.py",
        "tests/release-evaluation.md",
    )
    for relative in required:
        require(root / relative, errors)

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        for value in SETUP_PLACEHOLDERS:
            if value not in readme:
                errors.append(f"README is missing a setup placeholder: {value}")
        for value in OPERATOR_COMMANDS:
            if value not in readme:
                errors.append(f"README is missing an operator command: {value}")
        operator_text = readme.split("## Maintainer development", 1)[0]
        for value in LEGACY_OPERATOR_SETUP:
            if value in operator_text:
                errors.append(f"README operator setup contains a checkout command: {value}")

    manifest_path = root / "plugins/codex-kit/.codex-plugin/plugin.json"
    marketplace_path = root / ".agents/plugins/marketplace.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_version = manifest.get("version", "").split("+", 1)[0]
            if manifest.get("name") != "codex-kit" or manifest_version != VERSION:
                errors.append("plugin manifest name or version is invalid")
            if manifest.get("skills") != "./skills/":
                errors.append("plugin manifest skill path is invalid")
        except (json.JSONDecodeError, OSError) as error:
            errors.append(f"invalid plugin manifest: {error}")
    if marketplace_path.is_file():
        try:
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            if marketplace.get("name") != "codex-kit":
                errors.append("marketplace name must be codex-kit")
            entries = marketplace.get("plugins", [])
            if len(entries) != 1 or entries[0].get("name") != "codex-kit":
                errors.append("marketplace must contain one codex-kit entry")
        except (json.JSONDecodeError, OSError) as error:
            errors.append(f"invalid marketplace: {error}")

    plugin_root = root / "plugins" / "codex-kit"
    for removed_skill in REMOVED_SKILLS:
        if (plugin_root / "skills" / removed_skill).exists():
            errors.append(f"removed skill folder exists: {removed_skill}")
    for skill in SKILLS:
        skill_file = plugin_root / "skills" / skill / "SKILL.md"
        ui_file = plugin_root / "skills" / skill / "agents" / "openai.yaml"
        require(skill_file, errors)
        require(ui_file, errors)
        if skill_file.is_file():
            text = skill_file.read_text(encoding="utf-8")
            if "[TODO:" in text or not re.match(r"^---\nname: [a-z0-9-]+\ndescription: .+\n---\n", text):
                errors.append(f"invalid skill frontmatter or placeholder: {skill_file}")
        if ui_file.is_file():
            ui_text = ui_file.read_text(encoding="utf-8")
            if f"${skill}" not in ui_text:
                errors.append(f"skill UI prompt must name ${skill}: {ui_file}")
            expected_implicit = skill in AUTO_SKILLS
            if read_yaml_boolean(ui_text, "policy", "allow_implicit_invocation") is not expected_implicit:
                errors.append(f"skill invocation policy is invalid: {ui_file}")

    for filename, (name, model, effort) in AGENTS.items():
        path = plugin_root / "agents" / filename
        require(path, errors)
        if not path.is_file():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            errors.append(f"invalid custom agent {path}: {error}")
            continue
        if data.get("name") != name or data.get("model") != model:
            errors.append(f"custom-agent role or model is invalid: {path}")
        if effort is not None and data.get("model_reasoning_effort") != effort:
            errors.append(f"custom-agent effort is invalid: {path}")
        if (
            filename in {"luna_worker.toml", "terra_worker.toml"}
            and "model_reasoning_effort" in data
        ):
            errors.append(f"{name} must accept per-spawn reasoning")
    for filename in REMOVED_AGENTS:
        path = plugin_root / "agents" / filename
        if path.exists():
            errors.append(f"removed custom-agent profile exists: {path}")

    for path in root.rglob("*.md"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for value in SETUP_ASSUMPTIONS:
            if value.lower() in lowered:
                errors.append(f"documentation contains a location-specific setup value: {path}: {value}")
    check_asd_screen(root, errors)
    check_removed_vault_references(root, errors)


def check_project(root: Path, kit_root: Path, errors: list[str]) -> None:
    """Validate a consuming project with the canonical project checker.

    Args:
        root: The consuming project root.
        kit_root: The Codex Kit source root.
        errors: The validation error collector.
    """
    checker = kit_root / "plugins/codex-kit/skills/bootstrap/scripts/project.py"
    if checker.is_file() and root.is_dir():
        result = subprocess.run(
            [sys.executable, str(checker), "--project-root", str(root), "--check"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            errors.append(f"project structure validation failed: {detail}")
            if root.is_symlink():
                return
    else:
        for relative in (
            "AGENTS.md",
            ".agents/project-profile.yaml",
            "docs/codex/project-truth.md",
            "docs/codex/verification.md",
        ):
            require(root / relative, errors)
    check_removed_vault_references(root, errors)


def lexical_absolute(path: Path) -> Path:
    """Return an absolute path without resolving symlinks.

    Args:
        path: The input path.

    Returns:
        The expanded absolute path.
    """
    return Path(os.path.abspath(path.expanduser()))


def main() -> int:
    args = parse_args()
    if args.version:
        print(VERSION)
        return 0
    errors: list[str] = []
    kit_root = args.kit_root.expanduser().resolve()
    check_kit(kit_root, errors)
    checked_roots = [kit_root]
    if args.project_root:
        project_root = lexical_absolute(args.project_root)
        check_project(project_root, kit_root, errors)
        checked_roots.append(project_root)
    if args.release:
        for root in checked_roots:
            check_legacy_bootstraps(root, errors)
            check_clean_git(root, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("doctor: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
