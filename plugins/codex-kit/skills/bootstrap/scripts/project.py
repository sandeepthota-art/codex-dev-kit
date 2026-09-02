#!/usr/bin/env python3
"""Inspect a project before Codex Kit intake and check final structure."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

REQUIRED_PATHS = (
    "AGENTS.md",
    ".agents/project-profile.yaml",
    "docs/codex/project-truth.md",
    "docs/codex/verification.md",
)
OBSOLETE_PATHS = ("docs/codex/brownfield-classification.md",)

AGENT_FILES = {
    ".cursorrules",
    "agents.md",
    "agents.override.md",
    "claude.md",
    "gemini.md",
}
AGENT_PATHS = (
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
    ".github/instructions",
    ".github/copilot-instructions.md",
)
TRUTH_FILES = {
    "architecture.md",
    "contributing.md",
    "decisions.md",
    "governance.md",
    "roadmap.md",
    "security.md",
}
TRUTH_PATHS = (
    "adr",
    "adrs",
    "decisions",
    "docs/adr",
    "docs/adrs",
    "docs/architecture",
    "docs/codex",
    "docs/decisions",
)
CONFIGURATION_PATHS = (
    ".circleci",
    ".github/workflows",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
)
CONFIGURATION_NAMES = {
    "build.gradle",
    "build.gradle.kts",
    "build.pl",
    "cargo.toml",
    "cdk.json",
    "cmakelists.txt",
    "composer.json",
    "conanfile.py",
    "conanfile.txt",
    "cpanfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "dockerfile",
    "gemfile",
    "go.mod",
    "go.work",
    "gradle.properties",
    "justfile",
    "makefile",
    "makefile.pl",
    "meson.build",
    "mix.exs",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "pytest.ini",
    "requirements.txt",
    "samconfig.toml",
    "serverless.yml",
    "serverless.yaml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    "tsconfig.json",
    "vcpkg.json",
}
CONFIGURATION_SUFFIXES = (
    ".csproj",
    ".fsproj",
    ".sln",
    ".tf",
    ".toml",
    ".vbproj",
    ".yaml",
    ".yml",
)
BENIGN_ROOT_NAMES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    "authors",
    "authors.md",
    "changelog",
    "changelog.md",
    "code_of_conduct.md",
    "copying",
    "license",
    "license.md",
    "notice",
    "notice.md",
}
BENIGN_ROOT_DIRECTORIES = {
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
}
SECRET_SUFFIXES = {
    ".cer",
    ".crt",
    ".der",
    ".env",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
    ".pk8",
    ".pkcs12",
    ".ppk",
}
SECRET_PARTS = {"credential", "credentials", "secret", "secrets", "token", "tokens"}
SECRET_NAMES = {
    ".envrc",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
PLAIN_PROFILE_SCALAR = re.compile(r"[A-Za-z0-9._/-]+")


class IgnoreEvaluationError(ValueError):
    """Report that Git could not apply an existing ignore file."""


def parse_args() -> argparse.Namespace:
    """Parse the project inspector command line.

    Returns:
        The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def lexical_absolute(path: Path) -> Path:
    """Return an absolute path without resolving symlinks.

    Args:
        path: The input path.

    Returns:
        The expanded absolute path.
    """
    return Path(os.path.abspath(path.expanduser()))


def validate_root(root: Path) -> None:
    """Validate the project root without following a symlink.

    Args:
        root: The project root.

    Raises:
        ValueError: The root is missing, is not a directory, or is a symlink.
    """
    if root.is_symlink():
        raise ValueError(f"symlinks are not supported: {root}")
    if not root.exists():
        raise ValueError(f"project root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")


def validate_project_path(root: Path, path: Path) -> None:
    """Validate one project path and each parent below the root.

    Args:
        root: The validated project root.
        path: A path that must remain below the root.

    Raises:
        ValueError: The path escapes the root, uses a symlink, or has a
            non-directory parent.
    """
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"project path is outside the project: {path}") from error
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"symlinks are not supported: {current}")
        if current != path and current.exists() and not current.is_dir():
            raise ValueError(f"project path parent is not a directory: {current}")


def is_secret_path(relative: Path) -> bool:
    """Return whether a path belongs to a protected secret file class.

    Args:
        relative: A project-relative path.

    Returns:
        True when the path must not be inspected or reported.
    """
    name = relative.name.lower()
    if name in SECRET_NAMES or name == ".env" or name.startswith(".env."):
        return True
    if relative.suffix.lower() in SECRET_SUFFIXES:
        return True
    tokens = {token for token in re.split(r"[^a-z0-9]+", name) if token}
    return bool(tokens.intersection(SECRET_PARTS))


def is_configuration(relative: Path) -> bool:
    """Return whether a path is a likely text configuration file.

    Args:
        relative: A project-relative path.

    Returns:
        True when the name or suffix is a known configuration form.
    """
    name = relative.name.lower()
    return name in CONFIGURATION_NAMES or name.endswith(CONFIGURATION_SUFFIXES)


def is_truth_file(relative: Path) -> bool:
    """Return whether a file is a conventional project-truth document.

    Args:
        relative: A project-relative path.

    Returns:
        True when the file is a root README or a known truth document.
    """
    name = relative.name.lower()
    return name.startswith("readme") or name in TRUTH_FILES


def git_command(root: Path) -> tuple[list[str] | None, tempfile.TemporaryDirectory[str] | None]:
    """Build a Git command that evaluates the project ignore rules.

    Args:
        root: The project root that contains an existing ``.gitignore``.

    Returns:
        A command prefix and an optional temporary Git metadata directory. The
        command is ``None`` when Git cannot be used.
    """
    git = shutil.which("git")
    if git is None:
        return None, None
    try:
        probe = subprocess.run(
            [git, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None, None
    if probe.returncode == 0:
        return [git, "-C", str(root)], None
    temporary = tempfile.TemporaryDirectory(prefix="codex-kit-ignore-")
    metadata = Path(temporary.name) / ".git"
    try:
        initialized = subprocess.run(
            [git, "init", "--quiet", temporary.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        temporary.cleanup()
        return None, None
    if initialized.returncode != 0:
        temporary.cleanup()
        return None, None
    return [git, f"--git-dir={metadata}", f"--work-tree={root}"], temporary


def ignored_paths(command: list[str], relatives: list[Path]) -> set[str]:
    """Evaluate Git ignore rules for a group of project-relative paths.

    Args:
        command: The Git command prefix for the project.
        relatives: Project-relative paths to test.

    Returns:
        The POSIX paths that Git reports as ignored.

    Raises:
        ValueError: Git cannot evaluate the ignore rules.
    """
    if not relatives:
        return set()
    encoded = b"\0".join(path.as_posix().encode("utf-8") for path in relatives) + b"\0"
    try:
        result = subprocess.run(
            [*command, "check-ignore", "--no-index", "--stdin", "-z"],
            input=encoded,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise IgnoreEvaluationError(str(error)) from error
    if result.returncode not in {0, 1}:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise IgnoreEvaluationError(detail or "Git could not evaluate .gitignore")
    return {
        value.decode("utf-8")
        for value in result.stdout.split(b"\0")
        if value
    }


def visible_children(root: Path, directory: Path, command: list[str] | None) -> list[Path]:
    """List non-ignored, non-secret children without following symlinks.

    Args:
        root: The project root.
        directory: The directory to list.
        command: The Git ignore command, or ``None`` when no ignore file exists.

    Returns:
        Sorted visible child paths.

    Raises:
        ValueError: A child is a symlink or Git cannot evaluate ignore rules.
    """
    validate_project_path(root, directory)
    if not directory.is_dir():
        return []
    children = sorted(directory.iterdir(), key=lambda path: path.name)
    relatives = [child.relative_to(root) for child in children]
    ignored = ignored_paths(command, relatives) if command is not None else set()
    visible: list[Path] = []
    for child, relative in zip(children, relatives, strict=True):
        if child.is_symlink():
            raise ValueError(f"symlinks are not supported: {child}")
        if relative.parts and relative.parts[0] == ".git":
            continue
        if relative.as_posix() in ignored or is_secret_path(relative):
            continue
        visible.append(child)
    return visible


def walk_conventional(
    root: Path,
    target: Path,
    command: list[str] | None,
) -> Iterator[Path]:
    """Yield files below one conventional evidence path.

    Args:
        root: The project root.
        target: A conventional file or directory below the root.
        command: The Git ignore command, or ``None`` when no ignore file exists.

    Yields:
        Non-ignored and non-secret files below the target.

    Raises:
        ValueError: The path uses a symlink or cannot be inspected safely.
    """
    validate_project_path(root, target)
    if not target.exists():
        return
    if target.is_symlink():
        raise ValueError(f"symlinks are not supported: {target}")
    relative = target.relative_to(root)
    if is_secret_path(relative):
        return
    if command is not None and relative.as_posix() in ignored_paths(command, [relative]):
        return
    if target.is_file():
        yield target
        return
    if not target.is_dir():
        raise ValueError(f"project evidence path is not a regular path: {target}")
    for child in visible_children(root, target, command):
        if child.is_dir():
            yield from walk_conventional(root, child, command)
        elif child.is_file():
            yield child


def collect_conventional(
    root: Path,
    relatives: tuple[str, ...],
    command: list[str] | None,
) -> list[str]:
    """Collect unique files from conventional evidence paths.

    Args:
        root: The project root.
        relatives: Conventional project-relative files or directories.
        command: The Git ignore command, or ``None`` when no ignore file exists.

    Returns:
        Sorted project-relative file paths.
    """
    found: set[str] = set()
    for relative in relatives:
        for path in walk_conventional(root, root / relative, command):
            found.add(path.relative_to(root).as_posix())
    return sorted(found)


def collect_root_skill_markers(root: Path, command: list[str] | None) -> list[str]:
    """Collect shallow project-local skill markers.

    Args:
        root: The project root.
        command: The Git ignore command, or ``None`` when no ignore file exists.

    Returns:
        Sorted ``SKILL.md`` paths at the root of ``skills`` or one directory
        below it. Generic files below ``skills`` are not agent evidence.
    """
    skills = root / "skills"
    validate_project_path(root, skills)
    if not skills.exists():
        return []
    if skills.is_symlink():
        raise ValueError(f"symlinks are not supported: {skills}")
    relative = skills.relative_to(root)
    if command is not None and relative.as_posix() in ignored_paths(command, [relative]):
        return []
    if not skills.is_dir():
        return []
    markers: list[Path] = [skills / "SKILL.md"]
    markers.extend(
        child / "SKILL.md"
        for child in visible_children(root, skills, command)
        if child.is_dir()
    )
    found: list[str] = []
    for marker in markers:
        validate_project_path(root, marker)
        if marker.is_symlink():
            raise ValueError(f"symlinks are not supported: {marker}")
        marker_relative = marker.relative_to(root)
        if command is not None and marker_relative.as_posix() in ignored_paths(
            command,
            [marker_relative],
        ):
            continue
        if marker.is_file():
            found.append(marker_relative.as_posix())
    return sorted(found)


def source_state_hint(
    root_entries: list[dict[str, str]],
    configuration_candidates: list[str],
    agent_candidates: list[str],
    truth_candidates: list[str],
) -> str:
    """Infer whether shallow evidence suggests existing source.

    Args:
        root_entries: The visible root entry records.
        configuration_candidates: The detected configuration paths.
        agent_candidates: The detected agent evidence paths.
        truth_candidates: The detected documentary truth paths.

    Returns:
        ``greenfield``, ``brownfield``, or ``unknown``. Intake must confirm the
        value.
    """
    if configuration_candidates:
        return "brownfield"
    evidence_roots = {
        Path(path).parts[0]
        for path in (*agent_candidates, *truth_candidates)
        if Path(path).parts
    }
    uncertain_directory = False
    for entry in root_entries:
        relative = Path(entry["path"])
        name = relative.name.lower()
        if entry["kind"] == "directory":
            if name in BENIGN_ROOT_DIRECTORIES:
                continue
            if entry["path"] in evidence_roots:
                uncertain_directory = True
                continue
            return "brownfield"
        elif (
            name not in BENIGN_ROOT_NAMES
            and not name.startswith("readme")
            and name not in TRUTH_FILES
            and name not in AGENT_FILES
        ):
            return "brownfield"
    return "unknown" if uncertain_directory else "greenfield"


def inspect_project(root: Path) -> dict[str, object]:
    """Create a read-only, shallow project evidence report.

    Args:
        root: The validated project root.

    Returns:
        A JSON-compatible inspection report. Evidence lists are empty and
        hints are unknown when an existing ``.gitignore`` cannot be applied.

    Raises:
        ValueError: The project contains an unsupported path or Git reports an
            unsafe ignore-evaluation error.
    """
    ignore_file = root / ".gitignore"
    validate_project_path(root, ignore_file)
    command: list[str] | None = None
    temporary: tempfile.TemporaryDirectory[str] | None = None
    ignore_status = "absent"
    if ignore_file.exists():
        if ignore_file.is_symlink() or not ignore_file.is_file():
            raise ValueError(f".gitignore is not a regular file: {ignore_file}")
        command, temporary = git_command(root)
        if command is None:
            return {
                "project_root": str(root),
                "root_entries": [],
                "configuration_candidates": [],
                "agent_footprint_candidates": [],
                "documentary_truth_candidates": [],
                "ignore_status": "unavailable",
                "source_state_hint": "unknown",
                "prior_agent_footprint_hint": "unknown",
                "read_only": True,
            }
        ignore_status = "applied"
    try:
        children = visible_children(root, root, command)
        root_entries = [
            {
                "path": child.relative_to(root).as_posix(),
                "kind": "directory" if child.is_dir() else "file",
            }
            for child in children
            if child.is_dir() or child.is_file()
        ]
        root_configurations = [
            child.relative_to(root).as_posix()
            for child in children
            if child.is_file() and is_configuration(child.relative_to(root))
        ]
        nested_configurations = collect_conventional(root, CONFIGURATION_PATHS, command)
        configurations = sorted(set(root_configurations + nested_configurations))

        root_agents = [
            child.relative_to(root).as_posix()
            for child in children
            if child.is_file() and child.name.lower() in AGENT_FILES
        ]
        agents = sorted(
            set(
                root_agents
                + collect_conventional(root, AGENT_PATHS, command)
                + collect_root_skill_markers(root, command)
            )
        )

        root_truth = [
            child.relative_to(root).as_posix()
            for child in children
            if child.is_file() and is_truth_file(child.relative_to(root))
        ]
        truth = sorted(set(root_truth + collect_conventional(root, TRUTH_PATHS, command)))
        return {
            "project_root": str(root),
            "root_entries": root_entries,
            "configuration_candidates": configurations,
            "agent_footprint_candidates": agents,
            "documentary_truth_candidates": truth,
            "ignore_status": ignore_status,
            "source_state_hint": source_state_hint(
                root_entries,
                configurations,
                agents,
                truth,
            ),
            "prior_agent_footprint_hint": "present" if agents else "not-detected",
            "read_only": True,
        }
    except IgnoreEvaluationError:
        return {
            "project_root": str(root),
            "root_entries": [],
            "configuration_candidates": [],
            "agent_footprint_candidates": [],
            "documentary_truth_candidates": [],
            "ignore_status": "unavailable",
            "source_state_hint": "unknown",
            "prior_agent_footprint_hint": "unknown",
            "read_only": True,
        }
    finally:
        if temporary is not None:
            temporary.cleanup()


def parse_profile(text: str) -> tuple[dict[str, str], list[str]]:
    """Parse conservative top-level scalar fields from the profile.

    Args:
        text: The profile text.

    Returns:
        Parsed top-level values and structural errors. Nested project-owned
        mappings are ignored.
    """
    values: dict[str, str] = {}
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#") or line[0].isspace():
            continue
        if ":" not in line:
            errors.append(f"invalid top-level profile line {line_number}")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key or key in values:
            errors.append(f"invalid or duplicate top-level profile key on line {line_number}")
        elif not value:
            values[key] = ""
        elif value.startswith('"'):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                errors.append(f"invalid quoted profile value on line {line_number}")
            else:
                if isinstance(decoded, str):
                    values[key] = decoded
                else:
                    errors.append(f"profile value must be a string on line {line_number}")
        elif PLAIN_PROFILE_SCALAR.fullmatch(value):
            values[key] = value
        else:
            errors.append(f"invalid plain profile value on line {line_number}")
    return values, errors


def check_project(root: Path) -> int:
    """Check the required final files and version 2 profile structure.

    Args:
        root: The validated project root.

    Returns:
        Zero for a valid structure and one for validation errors.
    """
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        path = root / relative
        validate_project_path(root, path)
        if not path.is_file():
            errors.append(f"missing required project file: {path}")
    for relative in OBSOLETE_PATHS:
        path = root / relative
        validate_project_path(root, path)
        if path.exists():
            errors.append(f"remove obsolete Codex Kit classification: {path}")
    profile_path = root / ".agents/project-profile.yaml"
    if profile_path.is_file():
        values, profile_errors = parse_profile(profile_path.read_text(encoding="utf-8"))
        errors.extend(f"{error}: {profile_path}" for error in profile_errors)
        expected = {
            "version": "2",
            "project": root.name,
            "status": "intake-approved",
        }
        for key, value in expected.items():
            if values.get(key) != value:
                errors.append(f"project profile has invalid {key!r}: {profile_path}")
        if values.get("source_state") not in {"greenfield", "brownfield"}:
            errors.append(f"project profile has invalid 'source_state': {profile_path}")
        if values.get("prior_agent_footprint") not in {"absent", "present"}:
            errors.append(f"project profile has invalid 'prior_agent_footprint': {profile_path}")
        for legacy in ("mode", "profile"):
            if legacy in values:
                errors.append(f"project profile contains obsolete {legacy!r}: {profile_path}")
        allowed_scalars = {
            "version",
            "project",
            "source_state",
            "prior_agent_footprint",
            "status",
        }
        for key, value in values.items():
            if (
                key not in allowed_scalars
                and key not in {"mode", "profile"}
                and value
            ):
                errors.append(
                    f"project profile has unsupported top-level scalar {key!r}: "
                    f"{profile_path}"
                )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("project structure: ok (semantic project truth was not validated)")
    return 0


def main() -> int:
    """Run inspection or structural validation.

    Returns:
        The process exit status.
    """
    args = parse_args()
    root = lexical_absolute(args.project_root)
    try:
        validate_root(root)
        if args.check:
            return check_project(root)
        print(json.dumps(inspect_project(root), indent=2, ensure_ascii=True))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
