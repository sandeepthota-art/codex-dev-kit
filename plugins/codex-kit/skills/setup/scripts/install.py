#!/usr/bin/env python3
"""Install or remove Codex Kit managed machine files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

BEGIN = "<!-- codex-kit:begin -->"
END = "<!-- codex-kit:end -->"
AGENT_FILES = ("luna_worker.toml", "terra_worker.toml")
RETIRED_AGENT_FILES = ("project_lead.toml", "sol_reviewer.toml")
STATE_VERSION = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    if args.check and (args.dry_run or args.uninstall):
        parser.error("--check cannot be combined with --dry-run or --uninstall")
    return args


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    path = Path(value).expanduser() if value else Path.home() / ".codex"
    return Path(os.path.abspath(path))


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def managed_block() -> str:
    """Build the Codex Kit block for global project guidance.

    Returns:
        The complete managed Markdown block.
    """
    return (
        f"{BEGIN}\n"
        "# Codex Kit\n\n"
        "Use installed Codex Kit skills `setup`, `bootstrap`, `commission`, "
        "`launch`, `portfolio`, `auto-deliver`, and "
        "`auto-route-learnings`.\n\n"
        "Document every callable that Codex creates or materially changes in a "
        "tool or script. Use Google-style docstrings for Python or the standard "
        "equivalent for the language. Do not expand the task to untouched legacy "
        "callables.\n"
        f"{END}\n"
    )


def replace_block(text: str, block: str) -> str:
    if BEGIN not in text and END not in text:
        prefix = text.rstrip()
        return f"{prefix}\n\n{block}" if prefix else block
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("global AGENTS.md has an invalid Codex Kit managed block")
    before, remainder = text.split(BEGIN, 1)
    _, after = remainder.split(END, 1)
    if before.find(END) >= 0 or after.find(BEGIN) >= 0:
        raise ValueError("global AGENTS.md has an invalid Codex Kit managed block")
    return f"{before.rstrip()}\n\n{block}{after.lstrip()}" if before.strip() else f"{block}{after.lstrip()}"


def remove_block(text: str) -> str:
    if BEGIN not in text and END not in text:
        return text
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("global AGENTS.md has an invalid Codex Kit managed block")
    before, remainder = text.split(BEGIN, 1)
    _, after = remainder.split(END, 1)
    if before.find(END) >= 0 or after.find(BEGIN) >= 0:
        raise ValueError("global AGENTS.md has an invalid Codex Kit managed block")
    parts = [part.strip() for part in (before, after) if part.strip()]
    return "\n\n".join(parts) + ("\n" if parts else "")


def symlink_component(home: Path, path: Path) -> Path | None:
    if home.is_symlink():
        return home
    current = home
    for part in path.relative_to(home).parts:
        current /= part
        if current.is_symlink():
            return current
    return None


def validate_managed_path(home: Path, path: Path) -> None:
    link = symlink_component(home, path)
    if link is not None:
        raise ValueError(f"managed path uses a symlink {link}: {path}")
    try:
        path.relative_to(home)
    except ValueError as error:
        raise ValueError(f"managed path escapes CODEX_HOME: {path}") from error


def validate_managed_directory(home: Path, path: Path) -> None:
    validate_managed_path(home, path)
    if path.exists() and not path.is_dir():
        raise ValueError(f"managed directory path is not a directory: {path}")


def validate_managed_file(home: Path, path: Path) -> None:
    validate_managed_path(home, path)
    if path.exists() and not path.is_file():
        raise ValueError(f"managed file path is not a regular file: {path}")


def atomic_write(home: Path, path: Path, content: str) -> None:
    validate_managed_directory(home, path.parent)
    validate_managed_file(home, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"state_version": STATE_VERSION, "profiles": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"invalid managed state: {error}") from error
    if state.get("state_version") != STATE_VERSION or not isinstance(state.get("profiles"), dict):
        raise ValueError("invalid managed state schema")
    return state


def plugin_version(root: Path) -> str:
    path = root / ".codex-plugin" / "plugin.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))["version"]
    except (KeyError, json.JSONDecodeError, OSError) as error:
        raise ValueError(f"cannot read plugin version: {error}") from error
    if not isinstance(value, str) or not value:
        raise ValueError("plugin version is invalid")
    return value


def profile_status(target: Path, source_bytes: bytes, record: object) -> str:
    if not target.exists():
        return "missing"
    target_bytes = target.read_bytes()
    if target_bytes == source_bytes:
        return "current"
    if isinstance(record, dict) and sha256_bytes(target_bytes) == record.get("installed_sha256"):
        return "managed-old"
    return "modified"


def profile_is_owned(target: Path, record: object) -> bool:
    if not target.is_file() or not isinstance(record, dict):
        return False
    return sha256_bytes(target.read_bytes()) == record.get("installed_sha256")


def retired_profile_status(target: Path, record: object) -> str:
    """Classify one profile that the current release no longer installs.

    Args:
        target: The former managed profile path.
        record: The prior managed-state record for the profile.

    Returns:
        One of ``missing``, ``unowned``, ``owned``, or ``modified``.
    """
    if not target.exists():
        return "missing"
    if not isinstance(record, dict):
        return "unowned"
    return "owned" if profile_is_owned(target, record) else "modified"


def desired_state(version: str, sources: dict[str, bytes]) -> dict[str, object]:
    return {
        "state_version": STATE_VERSION,
        "kit_version": version,
        "profiles": {
            name: {"installed_sha256": sha256_bytes(content)}
            for name, content in sources.items()
        },
    }


def state_is_current(state: dict[str, object], version: str, sources: dict[str, bytes]) -> bool:
    return state == desired_state(version, sources)


def state_text(state: dict[str, object]) -> str:
    return json.dumps(state, indent=2, sort_keys=True) + "\n"


def main() -> int:
    args = parse_args()
    root = plugin_root()
    home = codex_home()
    global_agents = home / "AGENTS.md"
    target_agents = home / "agents"
    source_agents = root / "agents"
    state_path = home / "codex-kit" / "managed-state.json"
    block = managed_block()

    try:
        for path in (home, target_agents, state_path.parent):
            validate_managed_directory(home, path)
        for path in (
            global_agents,
            state_path,
            *(
                target_agents / name
                for name in (*AGENT_FILES, *RETIRED_AGENT_FILES)
            ),
        ):
            validate_managed_file(home, path)
        current_global = global_agents.read_text(encoding="utf-8") if global_agents.exists() else ""
        state = load_state(state_path)
        version = plugin_version(root)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    sources: dict[str, bytes] = {}
    statuses: dict[str, str] = {}
    records = state["profiles"]
    assert isinstance(records, dict)
    for name in AGENT_FILES:
        source = source_agents / name
        if not source.is_file():
            print(f"ERROR: agent template is missing: {source}", file=sys.stderr)
            return 2
        sources[name] = source.read_bytes()
        statuses[name] = profile_status(target_agents / name, sources[name], records.get(name))
    retired_statuses = {
        name: retired_profile_status(target_agents / name, records.get(name))
        for name in RETIRED_AGENT_FILES
    }

    try:
        expected_global = replace_block(current_global, block)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.check:
        if current_global != expected_global:
            print(f"ERROR: Codex Kit project guidance is not current: {global_agents}", file=sys.stderr)
            return 1
        for name, status in statuses.items():
            if status != "current":
                print(f"ERROR: installed agent is not current: {target_agents / name}", file=sys.stderr)
                return 1
        for name, status in retired_statuses.items():
            if status in {"owned", "modified"} or name in records:
                print(
                    f"ERROR: retired managed agent state is not current: "
                    f"{target_agents / name}",
                    file=sys.stderr,
                )
                return 1
        if not state_path.is_file() or not state_is_current(state, version, sources):
            print(f"ERROR: Codex Kit managed state is not current: {state_path}", file=sys.stderr)
            return 1
        print("install: ok")
        return 0

    if args.uninstall:
        try:
            updated_global = remove_block(current_global)
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        owned = {name: profile_is_owned(target_agents / name, records.get(name)) for name in AGENT_FILES}
        for name, status in statuses.items():
            if status != "missing" and not owned[name]:
                print(f"ERROR: refusing to remove modified agent file: {target_agents / name}", file=sys.stderr)
                return 2
        for name, status in retired_statuses.items():
            if status == "modified":
                print(f"ERROR: refusing to remove modified agent file: {target_agents / name}", file=sys.stderr)
                return 2
        actions = []
        if updated_global != current_global:
            actions.append(f"REMOVE managed block from {global_agents}")
        actions.extend(f"REMOVE {target_agents / name}" for name in AGENT_FILES if owned[name])
        actions.extend(
            f"REMOVE {target_agents / name}"
            for name, status in retired_statuses.items()
            if status == "owned"
        )
        if state_path.exists():
            actions.append(f"REMOVE {state_path}")
        if args.dry_run:
            print("\n".join(actions) if actions else "NO CHANGES")
            return 0
        if global_agents.exists() and updated_global != current_global:
            atomic_write(home, global_agents, updated_global)
        for name in AGENT_FILES:
            target = target_agents / name
            if owned[name]:
                validate_managed_file(home, target)
                target.unlink()
        for name, status in retired_statuses.items():
            target = target_agents / name
            if status == "owned":
                validate_managed_file(home, target)
                target.unlink()
        if state_path.exists():
            validate_managed_file(home, state_path)
            state_path.unlink()
        print("uninstall: ok")
        return 0

    for name, status in statuses.items():
        if status == "modified":
            print(f"ERROR: refusing to overwrite modified agent file: {target_agents / name}", file=sys.stderr)
            return 2
    for name, status in retired_statuses.items():
        if status == "modified":
            print(f"ERROR: refusing to remove modified agent file: {target_agents / name}", file=sys.stderr)
            return 2

    state_current = state_is_current(state, version, sources)
    wanted = state if state_current else desired_state(version, sources)
    actions = []
    if expected_global != current_global:
        actions.append(f"WRITE {global_agents}")
    actions.extend(
        f"REMOVE {target_agents / name}"
        for name, status in retired_statuses.items()
        if status == "owned"
    )
    for name, status in statuses.items():
        if status in {"missing", "managed-old"}:
            actions.append(f"WRITE {target_agents / name}")
    state_needs_write = not state_path.is_file() or not state_current
    if state_needs_write:
        actions.append(f"WRITE {state_path}")
    if args.dry_run:
        print("\n".join(actions) if actions else "NO CHANGES")
        return 0

    if expected_global != current_global:
        atomic_write(home, global_agents, expected_global)
    for name, status in retired_statuses.items():
        target = target_agents / name
        if status == "owned":
            validate_managed_file(home, target)
            target.unlink()
    validate_managed_directory(home, target_agents)
    target_agents.mkdir(parents=True, exist_ok=True)
    for name, status in statuses.items():
        if status in {"missing", "managed-old"}:
            atomic_write(home, target_agents / name, sources[name].decode("utf-8"))
    if state_needs_write:
        atomic_write(home, state_path, state_text(wanted))
    print("install: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
