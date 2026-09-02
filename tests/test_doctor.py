from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "doctor.py"
SPEC = importlib.util.spec_from_file_location("codex_kit_doctor", TOOL)
assert SPEC is not None and SPEC.loader is not None
DOCTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCTOR)


class DoctorTests(unittest.TestCase):
    def make_project(self, root: Path, profile: str | None = None) -> None:
        if profile is None:
            profile = f'''version: 2
project: "{root.name}"
source_state: greenfield
prior_agent_footprint: absent
status: intake-approved
'''
        files = {
            "AGENTS.md": "# Project Instructions\n",
            ".agents/project-profile.yaml": profile,
            "docs/codex/project-truth.md": "# Project Truth\n",
            "docs/codex/verification.md": "# Verification\n",
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_kit_is_valid(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--kit-root", str(ROOT)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("doctor: ok", result.stdout)

    def test_version(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0.6.0")

    def test_rejects_retired_sol_reviewer_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "kit"
            shutil.copytree(
                ROOT,
                root,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
            profile = root / "plugins/codex-kit/agents/sol_reviewer.toml"
            profile.write_text("name = 'sol_reviewer'\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOL), "--kit-root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("removed custom-agent profile exists", result.stderr)

    def test_luna_profile_accepts_per_spawn_reasoning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "kit"
            shutil.copytree(
                ROOT,
                root,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
            profile = root / "plugins/codex-kit/agents/luna_worker.toml"
            profile.write_text(
                profile.read_text(encoding="utf-8")
                + '\nmodel_reasoning_effort = "medium"\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(TOOL), "--kit-root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("luna_worker must accept per-spawn reasoning", result.stderr)

    def test_invocation_policy_ignores_comment_text(self) -> None:
        text = (
            "policy:\n"
            "  allow_implicit_invocation: true # allow_implicit_invocation: false\n"
        )
        self.assertIs(
            DOCTOR.read_yaml_boolean(text, "policy", "allow_implicit_invocation"),
            True,
        )

    def test_invocation_policy_rejects_nested_key(self) -> None:
        text = "policy:\n  nested:\n    allow_implicit_invocation: false\n"
        self.assertIsNone(
            DOCTOR.read_yaml_boolean(text, "policy", "allow_implicit_invocation")
        )

    def test_rejects_location_specific_setup_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Install under ~/valve.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOL), "--kit-root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("location-specific setup value", result.stderr)

    def test_release_requires_a_clean_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = subprocess.run(
                [sys.executable, str(TOOL), "--kit-root", str(root), "--release"],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a Git worktree", result.stderr)

    def test_release_rejects_active_legacy_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "notes.md").write_text("Load agentic-cos.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOL), "--kit-root", str(root), "--release"],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("active legacy bootstrap reference", result.stderr)

    def test_rejects_removed_vault_reference_in_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.make_project(
                project,
                f'''version: 2
project: "{project.name}"
source_state: brownfield
prior_agent_footprint: present
status: intake-approved
codex_vault: /old/path
''',
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--kit-root",
                    str(ROOT),
                    "--project-root",
                    str(project),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("removed Vault reference", result.stderr)

    def test_project_check_requires_profile_version_2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.make_project(project, "version: 1\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--kit-root",
                    str(ROOT),
                    "--project-root",
                    str(project),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("project structure validation failed", result.stderr)

    def test_project_check_rejects_symlinked_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / "project"
            self.make_project(project)
            linked = base / "linked-project"
            linked.symlink_to(project, target_is_directory=True)
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--kit-root",
                    str(ROOT),
                    "--project-root",
                    str(linked),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinks are not supported", result.stderr)

    def test_removed_vault_argument_is_rejected(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--vault-root", "/old/path"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
