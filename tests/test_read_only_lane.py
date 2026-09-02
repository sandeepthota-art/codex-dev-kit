from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "plugins/codex-kit/skills/auto-deliver/scripts/readonly.py"
)


class ReadOnlyLaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.binary = self.base / "codex"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_codex(self, body: str) -> None:
        """Create one executable fake Codex CLI.

        Args:
            body: Python statements for the fake executable.
        """
        self.binary.write_text(
            f"#!{sys.executable}\n" + textwrap.dedent(body),
            encoding="utf-8",
        )
        self.binary.chmod(0o755)

    def run_tool(
        self,
        *arguments: str,
        packet: str = "Review this change.\n",
        path: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the helper with an isolated executable search path.

        Args:
            arguments: Helper command arguments.
            packet: Text supplied to the helper through standard input.
            path: Optional executable search path. The fake binary directory
                is used when this value is ``None``.

        Returns:
            The completed helper process.
        """
        environment = {**os.environ, "PATH": path if path is not None else str(self.base)}
        return subprocess.run(
            [sys.executable, str(TOOL), *arguments],
            input=packet,
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def standard_arguments(self, project_root: str = "/tmp/project") -> tuple[str, ...]:
        """Build the normal helper arguments for one test.

        Args:
            project_root: Absolute project root to pass unchanged.

        Returns:
            The helper arguments.
        """
        return (
            "--project-root",
            project_root,
            "--model",
            "gpt-5.6-sol",
            "--reasoning",
            "high",
        )

    def test_enforces_flags_and_forwards_packet_and_project_root(self) -> None:
        self.write_codex(
            """
            import json
            import sys

            print(json.dumps({"arguments": sys.argv[1:], "packet": sys.stdin.read()}))
            """
        )
        project_root = "/tmp/project/../project"
        packet = "Complete bounded review packet.\n"
        result = self.run_tool(
            *self.standard_arguments(project_root),
            packet=packet,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["packet"], packet)
        self.assertEqual(
            report["arguments"],
            [
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--strict-config",
                "--disable",
                "multi_agent",
                "--disable",
                "hooks",
                "--sandbox",
                "read-only",
                "--model",
                "gpt-5.6-sol",
                "--config",
                'model_reasoning_effort="high"',
                "--config",
                'approval_policy="never"',
                "--cd",
                project_root,
                "--color",
                "never",
                "-",
            ],
        )

    def test_does_not_run_project_root_through_a_shell(self) -> None:
        self.write_codex(
            """
            import json
            import sys

            print(json.dumps(sys.argv[1:]))
            """
        )
        marker = self.base / "unexpected"
        project_root = f"/tmp/project;touch {marker}"
        result = self.run_tool(*self.standard_arguments(project_root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(project_root, json.loads(result.stdout))
        self.assertFalse(marker.exists())

    def test_rejects_empty_packet(self) -> None:
        self.write_codex("print('unused')\n")
        result = self.run_tool(*self.standard_arguments(), packet=" \n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("packet is empty", result.stderr)

    def test_fails_when_codex_is_not_on_path(self) -> None:
        result = self.run_tool(*self.standard_arguments(), path="")
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex is not available on PATH", result.stderr)

    def test_fails_when_codex_cannot_start(self) -> None:
        self.binary.write_text("#!/missing/interpreter\n", encoding="utf-8")
        self.binary.chmod(0o755)
        result = self.run_tool(*self.standard_arguments())
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex could not start", result.stderr)

    def test_fails_on_unsuccessful_codex_exit(self) -> None:
        self.write_codex(
            """
            import sys

            print("review failed", file=sys.stderr)
            raise SystemExit(7)
            """
        )
        result = self.run_tool(*self.standard_arguments())
        self.assertEqual(result.returncode, 2)
        self.assertIn("review failed", result.stderr)

    def test_fails_on_empty_report(self) -> None:
        self.write_codex("pass\n")
        result = self.run_tool(*self.standard_arguments())
        self.assertEqual(result.returncode, 2)
        self.assertIn("returned no delegated lane report", result.stderr)

    def test_forwards_success_diagnostics_and_report(self) -> None:
        self.write_codex(
            """
            import sys

            print("diagnostic", file=sys.stderr)
            print("review report")
            """
        )
        result = self.run_tool(*self.standard_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "review report\n")
        self.assertEqual(result.stderr, "diagnostic\n")

    def test_rejects_sandbox_and_approval_overrides(self) -> None:
        self.write_codex("print('unused')\n")
        for arguments in (
            (*self.standard_arguments(), "--sandbox", "workspace-write"),
            (*self.standard_arguments(), "--approval-policy", "on-request"),
            (*self.standard_arguments(), "--enable", "multi_agent"),
            (*self.standard_arguments(), "--enable", "hooks"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_tool(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
