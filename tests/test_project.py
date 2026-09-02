from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/project.py"
PLUGIN_TOOL = ROOT / "plugins/codex-kit/skills/bootstrap/scripts/project.py"


class ProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(
        self,
        project: Path,
        *arguments: str,
        tool: Path = TOOL,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(tool), "--project-root", str(project), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )

    def load_plugin_tool(self) -> ModuleType:
        spec = importlib.util.spec_from_file_location("codex_kit_project_tool", PLUGIN_TOOL)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def report(self, project: Path, *, tool: Path = TOOL) -> dict[str, object]:
        result = self.run_tool(project, tool=tool)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIsInstance(value, dict)
        return value

    def write(self, project: Path, relative: str, content: str = "evidence\n") -> Path:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_structure(
        self,
        project: Path,
        *,
        source_state: str = "greenfield",
        prior_agent_footprint: str = "absent",
    ) -> None:
        self.write(project, "AGENTS.md", "# Project instructions\n")
        project_value = json.dumps(project.name, ensure_ascii=True)
        self.write(
            project,
            ".agents/project-profile.yaml",
            f"""version: 2
project: {project_value}
source_state: {source_state}
prior_agent_footprint: {prior_agent_footprint}
status: intake-approved
commands:
  owner: project
""",
        )
        self.write(project, "docs/codex/project-truth.md", "Accepted project truth.\n")
        self.write(project, "docs/codex/verification.md", "Run the accepted checks.\n")

    def test_empty_and_readme_only_projects_are_greenfield(self) -> None:
        for name, readme in (("empty", False), ("readme-only", True)):
            with self.subTest(name=name):
                project = self.base / name
                project.mkdir()
                if readme:
                    self.write(project, "README.md", "# Purpose\n")
                report = self.report(project)
                self.assertEqual(report["source_state_hint"], "greenfield")
                self.assertEqual(report["prior_agent_footprint_hint"], "not-detected")
                self.assertEqual(report["ignore_status"], "absent")
                self.assertTrue(report["read_only"])

    def test_empty_source_with_old_agent_footprint_is_greenfield_b(self) -> None:
        project = self.base / "empty-agent"
        project.mkdir()
        self.write(project, "AGENTS.md", "# Old agent rules\n")
        self.write(project, ".claude/skills/local/SKILL.md", "# Local workflow\n")
        report = self.report(project)
        self.assertEqual(report["source_state_hint"], "greenfield")
        self.assertEqual(report["prior_agent_footprint_hint"], "present")
        self.assertIn("AGENTS.md", report["agent_footprint_candidates"])
        self.assertIn(
            ".claude/skills/local/SKILL.md",
            report["agent_footprint_candidates"],
        )

    def test_polyglot_root_evidence_informs_brownfield_a(self) -> None:
        project = self.base / "polyglot"
        files = (
            "pyproject.toml",
            "Makefile.PL",
            "CMakeLists.txt",
            "package.json",
            "tsconfig.json",
            "pom.xml",
            "cdk.json",
            ".github/workflows/test.yml",
        )
        for relative in files:
            self.write(project, relative)
        for directory in ("src", "tests", "web", "infra"):
            (project / directory).mkdir()
        report = self.report(project)
        self.assertEqual(report["source_state_hint"], "brownfield")
        self.assertEqual(report["prior_agent_footprint_hint"], "not-detected")
        for relative in files:
            self.assertIn(relative, report["configuration_candidates"])
        root_paths = {entry["path"] for entry in report["root_entries"]}
        self.assertTrue({"src", "tests", "web", "infra"}.issubset(root_paths))

    def test_foreign_and_current_kit_files_are_brownfield_b_evidence(self) -> None:
        project = self.base / "agent-evidence"
        for relative in (
            "CLAUDE.md",
            ".agents/project-profile.yaml",
            ".codex/skills/shared-copy/SKILL.md",
            "skills/unique-workflow/SKILL.md",
            ".githooks/pre-commit",
            "docs/codex/project-truth.md",
            "docs/codex/verification.md",
            "architecture.md",
        ):
            self.write(project, relative)
        report = self.report(project)
        self.assertEqual(report["prior_agent_footprint_hint"], "present")
        for relative in (
            "CLAUDE.md",
            ".agents/project-profile.yaml",
            ".codex/skills/shared-copy/SKILL.md",
            "skills/unique-workflow/SKILL.md",
        ):
            self.assertIn(relative, report["agent_footprint_candidates"])
        self.assertNotIn(
            ".githooks/pre-commit",
            report["agent_footprint_candidates"],
        )
        for relative in (
            "docs/codex/project-truth.md",
            "docs/codex/verification.md",
            "architecture.md",
        ):
            self.assertIn(relative, report["documentary_truth_candidates"])

    def test_gitignore_filters_root_agent_truth_and_config_evidence(self) -> None:
        project = self.base / "ignored"
        self.write(
            project,
            ".gitignore",
            "package.json\nAGENTS.md\ndocs/codex/\n.env\ncredentials.json\n",
        )
        for relative in (
            "package.json",
            "AGENTS.md",
            "docs/codex/project-truth.md",
            ".env",
            "credentials.json",
            "README.md",
        ):
            self.write(project, relative)
        report = self.report(project)
        self.assertEqual(report["ignore_status"], "applied")
        serialized = json.dumps(report)
        for excluded in (
            "package.json",
            "AGENTS.md",
            "project-truth.md",
            ".env",
            "credentials.json",
        ):
            self.assertNotIn(excluded, serialized)
        self.assertIn("README.md", serialized)

    def test_nested_ignore_and_negation_rules_are_applied(self) -> None:
        project = self.base / "negation"
        self.write(
            project,
            ".gitignore",
            ".github/workflows/*\n!.github/workflows/keep.yml\n",
        )
        self.write(project, ".agents/.gitignore", "drop.md\n")
        for relative in (
            ".agents/drop.md",
            ".agents/keep.md",
            ".github/workflows/drop.yml",
            ".github/workflows/keep.yml",
        ):
            self.write(project, relative)
        report = self.report(project)
        self.assertIn(".agents/keep.md", report["agent_footprint_candidates"])
        self.assertNotIn(".agents/drop.md", report["agent_footprint_candidates"])
        self.assertIn(".github/workflows/keep.yml", report["configuration_candidates"])
        self.assertNotIn(".github/workflows/drop.yml", report["configuration_candidates"])

    def test_generic_hooks_and_product_skills_are_not_agent_evidence(self) -> None:
        project = self.base / "generic-skills"
        self.write(project, ".husky/pre-commit")
        self.write(project, "hooks/release.sh")
        self.write(project, "skills/payments/handler.js")
        report = self.report(project)
        self.assertEqual(report["prior_agent_footprint_hint"], "not-detected")
        self.assertEqual(report["agent_footprint_candidates"], [])
        self.assertEqual(report["source_state_hint"], "brownfield")

    def test_generic_docs_and_skills_make_source_hint_brownfield(self) -> None:
        for name, relative in (
            ("docs-site", "docs/site/index.html"),
            ("product-skill", "skills/alexa/app.js"),
        ):
            with self.subTest(name=name):
                project = self.base / name
                self.write(project, relative)
                report = self.report(project)
                self.assertEqual(report["source_state_hint"], "brownfield")

    def test_mixed_truth_or_skill_roots_make_source_hint_unknown(self) -> None:
        for name, files in (
            (
                "mixed-docs",
                ("docs/codex/project-truth.md", "docs/site/index.html"),
            ),
            (
                "mixed-skills",
                ("skills/agent/SKILL.md", "skills/product/handler.js"),
            ),
        ):
            with self.subTest(name=name):
                project = self.base / name
                for relative in files:
                    self.write(project, relative)
                report = self.report(project)
                self.assertEqual(report["source_state_hint"], "unknown")

    def test_non_git_folder_uses_temporary_git_metadata(self) -> None:
        project = self.base / "not-a-worktree"
        self.write(project, ".gitignore", "package.json\n")
        self.write(project, "package.json")
        before = sorted(path.relative_to(project) for path in project.rglob("*"))
        report = self.report(project)
        after = sorted(path.relative_to(project) for path in project.rglob("*"))
        self.assertEqual(report["ignore_status"], "applied")
        self.assertNotIn("package.json", report["configuration_candidates"])
        self.assertEqual(before, after)
        self.assertFalse((project / ".git").exists())

    def test_unavailable_git_skips_automated_discovery(self) -> None:
        project = self.base / "no-git"
        self.write(project, ".gitignore", "ignored.md\n")
        self.write(project, "package.json")
        module = self.load_plugin_tool()
        with mock.patch.object(module.shutil, "which", return_value=None):
            report = module.inspect_project(project.resolve())
        self.assertEqual(report["ignore_status"], "unavailable")
        self.assertEqual(report["source_state_hint"], "unknown")
        self.assertEqual(report["prior_agent_footprint_hint"], "unknown")
        self.assertEqual(report["root_entries"], [])
        self.assertEqual(report["configuration_candidates"], [])

    def test_inspection_is_shallow_and_does_not_report_source_files(self) -> None:
        project = self.base / "shallow"
        self.write(project, "src/deep/module.py", "password = 'do not read'\n")
        self.write(project, "tests/deep/test_module.py")
        report = self.report(project)
        serialized = json.dumps(report)
        self.assertIn('"path": "src"', serialized)
        self.assertIn('"path": "tests"', serialized)
        self.assertNotIn("module.py", serialized)
        self.assertNotIn("test_module.py", serialized)
        self.assertNotIn("do not read", serialized)

    def test_secret_file_classes_are_never_reported(self) -> None:
        project = self.base / "secrets"
        for relative in (
            ".env.production",
            "production.env",
            ".npmrc",
            "id_rsa",
            "client.pem",
            "signing.ppk",
            "signing.pk8",
            "signing.pkcs12",
            "service-token.yaml",
            "credentials.json",
        ):
            self.write(project, relative)
        self.write(project, "README.md")
        serialized = json.dumps(self.report(project))
        for relative in (
            ".env.production",
            "production.env",
            ".npmrc",
            "id_rsa",
            "client.pem",
            "signing.ppk",
            "signing.pk8",
            "signing.pkcs12",
            "service-token.yaml",
            "credentials.json",
        ):
            self.assertNotIn(relative, serialized)

    def test_preview_is_read_only_and_wrapper_matches_plugin(self) -> None:
        project = self.base / "parity"
        self.write(project, "README.md", "# Stable\n")
        before = {
            path.relative_to(project): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        wrapper = self.run_tool(project)
        plugin = self.run_tool(project, tool=PLUGIN_TOOL)
        self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
        self.assertEqual(plugin.returncode, 0, plugin.stderr)
        self.assertEqual(wrapper.stdout, plugin.stdout)
        after = {
            path.relative_to(project): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_project_root_must_exist_and_symlinks_are_unsupported(self) -> None:
        missing = self.run_tool(self.base / "missing")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("does not exist", missing.stderr)

        target = self.base / "target"
        target.mkdir()
        root_link = self.base / "root-link"
        root_link.symlink_to(target, target_is_directory=True)
        linked = self.run_tool(root_link)
        self.assertEqual(linked.returncode, 2)
        self.assertIn("symlinks are not supported", linked.stderr)

        project = self.base / "child-link"
        project.mkdir()
        self.write(project, ".gitignore", "ignored\n")
        (project / ".agents").symlink_to(target, target_is_directory=True)
        child = self.run_tool(project)
        self.assertEqual(child.returncode, 2)
        self.assertIn("symlinks are not supported", child.stderr)

    def test_check_accepts_version_2_and_project_owned_nested_fields(self) -> None:
        project = self.base / "checked"
        self.write_structure(
            project,
            source_state="brownfield",
            prior_agent_footprint="present",
        )
        result = self.run_tool(project, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("semantic project truth was not validated", result.stdout)

    def test_check_rejects_missing_malformed_and_version_1_profiles(self) -> None:
        project = self.base / "invalid"
        project.mkdir()
        missing = self.run_tool(project, "--check")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("missing required project file", missing.stderr)

        self.write_structure(project)
        profile = project / ".agents/project-profile.yaml"
        cases = {
            "source_state: greenfield": "source_state: unknown",
            "prior_agent_footprint: absent": "prior_agent_footprint: maybe",
            "version: 2": "version: 1",
            "status: intake-approved": "status: pending",
        }
        original = profile.read_text(encoding="utf-8")
        for old, new in cases.items():
            with self.subTest(new=new):
                profile.write_text(original.replace(old, new), encoding="utf-8")
                result = self.run_tool(project, "--check")
                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid", result.stderr)
        profile.write_text(
            original + "mode: brownfield\nprofile: python\n",
            encoding="utf-8",
        )
        legacy = self.run_tool(project, "--check")
        self.assertEqual(legacy.returncode, 1)
        self.assertIn("obsolete 'mode'", legacy.stderr)
        self.assertIn("obsolete 'profile'", legacy.stderr)

        profile.write_text(original + "technology_profile: python\n", encoding="utf-8")
        unsupported = self.run_tool(project, "--check")
        self.assertEqual(unsupported.returncode, 1)
        self.assertIn("unsupported top-level scalar 'technology_profile'", unsupported.stderr)

    def test_check_rejects_malformed_required_scalar_and_obsolete_file(self) -> None:
        project = self.base / "malformed"
        self.write_structure(project)
        profile = project / ".agents/project-profile.yaml"
        profile.write_text(
            profile.read_text(encoding="utf-8").replace(
                "source_state: greenfield",
                "source_state: [greenfield]",
            ),
            encoding="utf-8",
        )
        malformed = self.run_tool(project, "--check")
        self.assertEqual(malformed.returncode, 1)
        self.assertIn("invalid plain profile value", malformed.stderr)

        self.write_structure(project)
        self.write(project, "docs/codex/brownfield-classification.md")
        obsolete = self.run_tool(project, "--check")
        self.assertEqual(obsolete.returncode, 1)
        self.assertIn("remove obsolete", obsolete.stderr)

    def test_check_rejects_required_file_symlink(self) -> None:
        project = self.base / "linked-check"
        self.write_structure(project)
        external = self.base / "external.md"
        external.write_text("external\n", encoding="utf-8")
        truth = project / "docs/codex/project-truth.md"
        truth.unlink()
        truth.symlink_to(external)
        result = self.run_tool(project, "--check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlinks are not supported", result.stderr)

    def test_old_mode_profile_scope_and_inventory_flags_are_rejected(self) -> None:
        project = self.base / "removed-flags"
        project.mkdir()
        for arguments in (
            ("--mode", "greenfield"),
            ("--profile", "python"),
            ("--scope", "docs"),
            ("--list-profiles",),
            ("--scan-existing-project",),
            ("--skip-baseline",),
            ("--overwrite", "AGENTS.md"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_tool(project, *arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unrecognized arguments", result.stderr)

    def test_rewritten_inspector_callables_have_docstrings(self) -> None:
        tree = ast.parse(PLUGIN_TOOL.read_text(encoding="utf-8"))
        missing = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and ast.get_docstring(node) is None
        ]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
