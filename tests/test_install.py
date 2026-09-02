from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "install.py"
PLUGIN_TOOL = ROOT / "plugins/codex-kit/skills/setup/scripts/install.py"


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = self.base / "codex-home"
        self.environment = {**os.environ, "CODEX_HOME": str(self.home)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(self, *arguments: str, tool: Path = TOOL) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(tool), *arguments],
            text=True,
            capture_output=True,
            env=self.environment,
            check=False,
        )

    def add_retired_managed_profile(
        self,
        name: str = "project_lead.toml",
        content: bytes = b"retired managed profile\n",
    ) -> Path:
        """Add one formerly managed profile to an installed test state.

        Args:
            name: Retired profile filename.
            content: Installed profile content.

        Returns:
            The retired profile path.
        """
        target = self.home / "agents" / name
        target.write_bytes(content)
        state_path = self.home / "codex-kit/managed-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["kit_version"] = "0.3.1+codex.20260810000221"
        state["profiles"][name] = {
            "installed_sha256": hashlib.sha256(content).hexdigest()
        }
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target

    def test_dry_run_does_not_write(self) -> None:
        result = self.run_tool("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WRITE", result.stdout)
        self.assertFalse(self.home.exists())

    def test_plugin_distributed_installer_runs_without_checkout_path_state(self) -> None:
        result = self.run_tool(tool=PLUGIN_TOOL)
        self.assertEqual(result.returncode, 0, result.stderr)
        state_text = (self.home / "codex-kit/managed-state.json").read_text(encoding="utf-8")
        instructions = (self.home / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn(str(ROOT), state_text)
        self.assertNotIn(str(ROOT), instructions)
        self.assertNotIn("plugins/codex-kit", state_text)
        self.assertNotIn("plugins/codex-kit", instructions)

    def test_removed_vault_argument_is_rejected(self) -> None:
        result = self.run_tool("--vault-root", "/old/path")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_install_is_idempotent_and_check_passes(self) -> None:
        first = self.run_tool()
        self.assertEqual(first.returncode, 0, first.stderr)
        snapshot = {
            path.relative_to(self.home): path.read_bytes()
            for path in self.home.rglob("*")
            if path.is_file()
        }
        state_path = self.home / "codex-kit/managed-state.json"
        state_stat = state_path.stat()
        second = self.run_tool()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(
            snapshot,
            {
                path.relative_to(self.home): path.read_bytes()
                for path in self.home.rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(state_path.stat().st_ino, state_stat.st_ino)
        self.assertEqual(state_path.stat().st_mtime_ns, state_stat.st_mtime_ns)
        checked = self.run_tool("--check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        state = json.loads((self.home / "codex-kit/managed-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["state_version"], 1)
        self.assertNotIn("installed_at", state)
        self.assertEqual(
            set(state["profiles"]),
            {"luna_worker.toml", "terra_worker.toml"},
        )
        self.assertFalse((self.home / "agents/project_lead.toml").exists())
        self.assertFalse((self.home / "agents/sol_reviewer.toml").exists())
        instructions = (self.home / "AGENTS.md").read_text(encoding="utf-8")
        for skill in (
            "setup",
            "bootstrap",
            "commission",
            "launch",
            "portfolio",
            "auto-deliver",
            "auto-route-learnings",
        ):
            self.assertIn(f"`{skill}`", instructions)
        self.assertNotIn("vault", instructions.lower())

    def test_check_before_install_is_read_only(self) -> None:
        result = self.run_tool("--check", tool=PLUGIN_TOOL)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.home.exists())

    def test_malformed_block_is_refused(self) -> None:
        self.home.mkdir(parents=True)
        (self.home / "AGENTS.md").write_text(
            "<!-- codex-kit:begin -->\ninvalid\n<!-- codex-kit:begin -->\n",
            encoding="utf-8",
        )
        result = self.run_tool(tool=PLUGIN_TOOL)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid Codex Kit managed block", result.stderr)

    def test_modified_agent_is_not_overwritten(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.home / "agents" / "terra_worker.toml"
        target.write_text(target.read_text(encoding="utf-8") + "\n# local change\n", encoding="utf-8")
        result = self.run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to overwrite", result.stderr)

    def test_uninstall_removes_only_owned_files(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        preview = self.run_tool("--uninstall", "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("REMOVE", preview.stdout)
        for name in ("luna_worker.toml", "terra_worker.toml"):
            self.assertTrue((self.home / "agents" / name).is_file())
        result = self.run_tool("--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("codex-kit:begin", (self.home / "AGENTS.md").read_text(encoding="utf-8"))
        for name in ("luna_worker.toml", "terra_worker.toml"):
            self.assertFalse((self.home / "agents" / name).exists())
        self.assertFalse((self.home / "codex-kit/managed-state.json").exists())

    def test_uninstall_refuses_modified_agent(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.home / "agents" / "terra_worker.toml"
        target.write_text(target.read_text(encoding="utf-8") + "\n# local change\n", encoding="utf-8")
        result = self.run_tool("--uninstall")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to remove", result.stderr)
        self.assertTrue(target.exists())

    def test_install_adopts_exact_profiles_without_prior_state(self) -> None:
        target_agents = self.home / "agents"
        target_agents.mkdir(parents=True)
        source_agents = ROOT / "plugins/codex-kit/agents"
        for name in ("luna_worker.toml", "terra_worker.toml"):
            shutil.copyfile(source_agents / name, target_agents / name)
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / "codex-kit/managed-state.json").is_file())
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_upgrade_adds_luna_to_an_older_managed_installation(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.home / "agents/luna_worker.toml"
        target.unlink()
        state_path = self.home / "codex-kit/managed-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["kit_version"] = "0.3.4+codex.20260811132106"
        del state["profiles"]["luna_worker.toml"]
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        preview = self.run_tool("--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn(f"WRITE {target}", preview.stdout)
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(target.is_file())
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_uninstall_does_not_claim_exact_profiles_without_state(self) -> None:
        target_agents = self.home / "agents"
        target_agents.mkdir(parents=True)
        source_agents = ROOT / "plugins/codex-kit/agents"
        for name in ("luna_worker.toml", "terra_worker.toml"):
            shutil.copyfile(source_agents / name, target_agents / name)
        result = self.run_tool("--uninstall")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to remove", result.stderr)
        self.assertTrue((target_agents / "terra_worker.toml").exists())

    def test_install_upgrades_an_owned_older_profile(self) -> None:
        kit_copy = self.base / "kit-copy"
        shutil.copytree(ROOT, kit_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        copied_tool = kit_copy / "tools/install.py"
        self.assertEqual(self.run_tool(tool=copied_tool).returncode, 0)
        source = kit_copy / "plugins/codex-kit/agents/terra_worker.toml"
        source.write_text(source.read_text(encoding="utf-8") + "\n# new managed release\n", encoding="utf-8")
        manifest = kit_copy / "plugins/codex-kit/.codex-plugin/plugin.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["version"] = "0.5.0+codex.20260807000000"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_tool(tool=copied_tool)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new managed release", (self.home / "agents/terra_worker.toml").read_text(encoding="utf-8"))
        state = json.loads((self.home / "codex-kit/managed-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["kit_version"], "0.5.0+codex.20260807000000")

    def test_upgrade_removes_owned_retired_project_lead_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.add_retired_managed_profile()
        preview = self.run_tool("--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn(f"REMOVE {target}", preview.stdout)
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())
        state = json.loads((self.home / "codex-kit/managed-state.json").read_text(encoding="utf-8"))
        self.assertNotIn("project_lead.toml", state["profiles"])
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_upgrade_refuses_modified_retired_project_lead_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.add_retired_managed_profile()
        target.write_text(target.read_text(encoding="utf-8") + "# local change\n", encoding="utf-8")
        result = self.run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to remove modified agent file", result.stderr)
        self.assertTrue(target.exists())

    def test_upgrade_preserves_unowned_retired_project_lead_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.home / "agents/project_lead.toml"
        target.write_text("unowned local profile\n", encoding="utf-8")
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "unowned local profile\n")
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_upgrade_removes_owned_retired_sol_reviewer_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.add_retired_managed_profile("sol_reviewer.toml")
        preview = self.run_tool("--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn(f"REMOVE {target}", preview.stdout)
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())
        state = json.loads(
            (self.home / "codex-kit/managed-state.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("sol_reviewer.toml", state["profiles"])
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_upgrade_refuses_modified_retired_sol_reviewer_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.add_retired_managed_profile("sol_reviewer.toml")
        target.write_text(
            target.read_text(encoding="utf-8") + "# local change\n",
            encoding="utf-8",
        )
        result = self.run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to remove modified agent file", result.stderr)
        self.assertTrue(target.exists())

    def test_upgrade_preserves_unowned_retired_sol_reviewer_profile(self) -> None:
        self.assertEqual(self.run_tool().returncode, 0)
        target = self.home / "agents/sol_reviewer.toml"
        target.write_text("unowned local profile\n", encoding="utf-8")
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            target.read_text(encoding="utf-8"),
            "unowned local profile\n",
        )
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_managed_file_symlink_is_refused_before_all_operations(self) -> None:
        self.home.mkdir(parents=True)
        external = self.base / "external-agents.md"
        external.write_text("# External\n", encoding="utf-8")
        (self.home / "AGENTS.md").symlink_to(external)
        for arguments in (("--dry-run",), (), ("--uninstall", "--dry-run")):
            with self.subTest(arguments=arguments):
                result = self.run_tool(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("managed path uses a symlink", result.stderr)
                self.assertEqual(external.read_text(encoding="utf-8"), "# External\n")

    def test_managed_parent_symlinks_are_refused(self) -> None:
        for relative in ("agents", "codex-kit"):
            with self.subTest(relative=relative):
                home = self.base / f"home-{relative}"
                external = self.base / f"external-{relative}"
                home.mkdir()
                external.mkdir()
                (home / relative).symlink_to(external, target_is_directory=True)
                environment = {**os.environ, "CODEX_HOME": str(home)}
                result = subprocess.run(
                    [sys.executable, str(PLUGIN_TOOL), "--dry-run"],
                    text=True,
                    capture_output=True,
                    env=environment,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("managed path uses a symlink", result.stderr)
                self.assertEqual(list(external.iterdir()), [])

    def test_symlinked_codex_home_is_refused_for_all_operations(self) -> None:
        external = self.base / "external-home"
        external.mkdir()
        home = self.base / "linked-home"
        home.symlink_to(external, target_is_directory=True)
        environment = {**os.environ, "CODEX_HOME": str(home)}
        for arguments in (("--dry-run",), (), ("--check",), ("--uninstall", "--dry-run")):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, str(PLUGIN_TOOL), *arguments],
                    text=True,
                    capture_output=True,
                    env=environment,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("managed path uses a symlink", result.stderr)
                self.assertEqual(list(external.iterdir()), [])

    def test_managed_directory_paths_must_be_directories(self) -> None:
        for relative in ("agents", "codex-kit"):
            for arguments in (("--dry-run",), (), ("--uninstall", "--dry-run")):
                with self.subTest(relative=relative, arguments=arguments):
                    home = self.base / f"regular-{relative}-{'-'.join(arguments) or 'apply'}"
                    home.mkdir()
                    (home / relative).write_text("not a directory\n", encoding="utf-8")
                    environment = {**os.environ, "CODEX_HOME": str(home)}
                    result = subprocess.run(
                        [sys.executable, str(PLUGIN_TOOL), *arguments],
                        text=True,
                        capture_output=True,
                        env=environment,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("managed directory path is not a directory", result.stderr)
                    self.assertFalse((home / "AGENTS.md").exists())

    def test_codex_home_must_be_a_directory_before_preview_or_apply(self) -> None:
        for arguments in (("--dry-run",), (), ("--uninstall", "--dry-run")):
            with self.subTest(arguments=arguments):
                home = self.base / f"regular-home-{'-'.join(arguments) or 'apply'}"
                home.write_text("not a directory\n", encoding="utf-8")
                environment = {**os.environ, "CODEX_HOME": str(home)}
                result = subprocess.run(
                    [sys.executable, str(PLUGIN_TOOL), *arguments],
                    text=True,
                    capture_output=True,
                    env=environment,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("managed directory path is not a directory", result.stderr)
                self.assertEqual(home.read_text(encoding="utf-8"), "not a directory\n")


if __name__ == "__main__":
    unittest.main()
