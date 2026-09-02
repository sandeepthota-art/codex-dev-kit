from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/codex-kit"
HUMAN_SKILLS = ("setup", "bootstrap", "commission", "launch", "portfolio")
AUTO_SKILLS = ("auto-deliver", "auto-route-learnings")
CURRENT_SKILLS = (*HUMAN_SKILLS, *AUTO_SKILLS)
OLD_SKILLS = (
    "project",
    "succession",
    "workstream",
    "route-work",
    "deliver-work",
    "route-learnings",
    "project-lead-succession",
    "portfolio-review",
)


def read(relative: str) -> str:
    return (PLUGIN / relative).read_text(encoding="utf-8")


def flat(relative: str) -> str:
    return " ".join(read(relative).split())


class PolicyContractTests(unittest.TestCase):
    def test_readme_uses_plugin_distributed_operator_setup(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        operator_text = readme.split("## Maintainer development", 1)[0]
        for value in (
            "codex plugin marketplace add <codex-kit-repository-url>",
            "codex plugin marketplace upgrade codex-kit",
            "codex plugin add codex-kit@codex-kit",
            "$codex-kit:setup",
        ):
            self.assertIn(value, operator_text)
        for value in (
            "git clone",
            "/path/to/codex-kit",
            "python3 /path/to/codex-kit/tools/install.py",
            "codex plugin marketplace add /path/to/codex-kit",
        ):
            self.assertNotIn(value, operator_text)

    def test_top_level_tools_are_canonical_wrappers(self) -> None:
        install = (ROOT / "tools/install.py").read_text(encoding="utf-8")
        project = (ROOT / "tools/project.py").read_text(encoding="utf-8")
        self.assertIn("runpy.run_path", install)
        self.assertIn("skills/setup/scripts/install.py", install.replace('"\n    / "', "/"))
        self.assertIn("runpy.run_path", project)
        self.assertIn("skills/bootstrap/scripts/project.py", project.replace('"\n    / "', "/"))

    def test_skill_local_resources_resolve_from_each_skill_file(self) -> None:
        checked: list[Path] = []
        for skill_file in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
            source = skill_file.read_text(encoding="utf-8")
            resources = re.findall(r"`((?:\.\./|scripts/)[^`]+)`", source)
            if resources:
                self.assertIn("relative to this `SKILL.md`", source)
            for resource in resources:
                path = (skill_file.parent / resource).resolve()
                self.assertTrue(path.is_file(), f"missing skill resource: {path}")
                checked.append(path)
        self.assertGreaterEqual(len(checked), 6)

    def test_catalog_has_only_current_skill_folders(self) -> None:
        actual = tuple(sorted(path.name for path in (PLUGIN / "skills").iterdir() if path.is_dir()))
        self.assertEqual(actual, tuple(sorted(CURRENT_SKILLS)))
        for old_name in OLD_SKILLS:
            self.assertFalse((PLUGIN / "skills" / old_name).exists())

    def test_skill_frontmatter_and_ui_match_the_current_catalog(self) -> None:
        for skill in CURRENT_SKILLS:
            source = read(f"skills/{skill}/SKILL.md")
            ui = read(f"skills/{skill}/agents/openai.yaml")
            self.assertIn(f"name: {skill}", source)
            self.assertIn(f"${skill}", ui)
            description = re.search(r'^  short_description: "(.+)"$', ui, re.MULTILINE)
            self.assertIsNotNone(description)
            assert description is not None
            self.assertGreaterEqual(len(description.group(1)), 25)
            self.assertLessEqual(len(description.group(1)), 64)
        for skill in HUMAN_SKILLS:
            self.assertIn("allow_implicit_invocation: false", read(f"skills/{skill}/agents/openai.yaml"))
        for skill in AUTO_SKILLS:
            source = read(f"skills/{skill}/SKILL.md")
            self.assertIn("allow_implicit_invocation: true", read(f"skills/{skill}/agents/openai.yaml"))
            self.assertIn("Agent-only", source)

    def test_expanded_frontmatter_descriptions_preserve_triggers(self) -> None:
        contracts = {
            "bootstrap": ("greenfield", "brownfield", "project-guidance migration"),
            "commission": ("exactly one", "replacement Project Lead", "approved project truth"),
            "launch": ("Explicit human entry", "free text", "external work item", "same-project"),
            "auto-deliver": ("Agent-only", "launched streams", "detailed intake", "closure"),
            "portfolio": ("cross-project state", "stale leads", "shared blockers", "repository health"),
            "auto-route-learnings": ("Agent-only", "user memory requests", "accepted project truth", "reusable patterns"),
        }
        for skill, expected in contracts.items():
            frontmatter = read(f"skills/{skill}/SKILL.md").split("---", 2)[1]
            for value in expected:
                self.assertIn(value, frontmatter)

    def test_manifest_has_exact_human_starter_prompts(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertEqual(
            prompts,
            [
                "Use $codex-kit:setup to preview and validate machine setup.",
                "Use $codex-kit:bootstrap to inspect and intake this project.",
                "Use $codex-kit:commission to create and pin one Project Lead.",
                "Use $codex-kit:launch inside Project Lead - <Project> to start work.",
            ],
        )
        self.assertTrue(all(len(prompt) <= 128 for prompt in prompts))
        descriptions = " ".join(
            (
                manifest["description"],
                manifest["interface"]["shortDescription"],
                manifest["interface"]["longDescription"],
            )
        )
        self.assertIn("Workstream launch", descriptions)
        self.assertIn("launches branch-based Workstream tasks in saved projects", descriptions)
        self.assertNotIn("routes scoped work", descriptions)

    def test_canonical_workstream_matrix_and_specialist_lanes(self) -> None:
        policy = read("references/operating-model.md")
        for contract in (
            "Configure it with\nGPT-5.6 Sol and High reasoning",
            "Small, local, low-risk | GPT-5.6 Terra with Medium reasoning",
            "Normal or multi-file | GPT-5.6 Terra with High reasoning",
            "Protected, architecture-heavy, high-risk, or difficult integration",
            "GPT-5.6 Sol with High reasoning",
            "Bounded file search, inventories, evidence collection, deterministic",
            "Focused read-only exploration and repetitive mechanical changes",
            "Bounded implementation from an approved detailed plan",
            "Long, fully specified bounded execution with strong checks",
            "Broad exploration that needs active judgment",
            "Focused verification: GPT-5.6 Terra with Low or Medium reasoning",
            "| Small, local, low-risk | GPT-5.6 Terra with Medium reasoning |",
            "| Normal | GPT-5.6 Terra with High reasoning |",
            "| Protected, high-risk, or difficult integration | GPT-5.6 Sol with High reasoning |",
            "Fresh review: select the risk-matrix tier through the enforced read-only",
            "Exceptional advice: fresh GPT-5.6 Sol with XHigh or Max reasoning",
        ):
            self.assertIn(contract, policy)

    def test_reviewer_is_independent_and_read_only(self) -> None:
        routing = flat("skills/auto-deliver/SKILL.md")
        policy = flat("references/operating-model.md")
        release_evaluation = (ROOT / "tests/release-evaluation.md").read_text(encoding="utf-8")
        helper = read("skills/auto-deliver/scripts/readonly.py")
        assurance_mapping = (
            "Terra Medium for small low-risk work, Terra High for normal work, "
            "and Sol High for protected, high-risk, or difficult-integration mutations"
        )
        self.assertIn("For every mutation, run a fresh independent read-only reviewer through `scripts/readonly.py`", routing)
        self.assertIn(assurance_mapping, routing)
        self.assertIn(assurance_mapping, release_evaluation)
        self.assertIn("report its effective sandbox before inspection", routing)
        self.assertIn("not implement findings", routing)
        self.assertIn("Do not use a native agent, user-visible task, substitute, or Lead fallback", routing)
        self.assertIn("perform the review personally, not implement findings, and not delegate, spawn, or create another agent", routing)
        self.assertIn("Every mutation requires a fresh independent read-only review through the enforced ephemeral Codex CLI helper", policy)
        self.assertIn("Every mutation also requires a fresh independent read-only verification lane", policy)
        self.assertIn("Every remediation mutation receives its own fresh independent read-only review", policy)
        self.assertIn("Material remediation requires a new reviewer and a new verifier", policy)
        self.assertIn("it disables native multi-agent delegation", policy)
        self.assertIn("native multi-agent delegation and hooks", policy)
        self.assertIn("The CLI process must perform the lane itself", policy)
        self.assertIn('SANDBOX = "read-only"', helper)
        self.assertIn('APPROVAL_POLICY = "never"', helper)
        self.assertIn('"--disable",\n        "multi_agent"', helper)
        self.assertIn('"--disable",\n        "hooks"', helper)
        self.assertFalse((PLUGIN / "agents/sol_reviewer.toml").exists())

    def test_native_agents_use_general_delegation_controls(self) -> None:
        policy = flat("references/operating-model.md")
        routing = flat("skills/auto-deliver/SKILL.md")
        profile = read("agents/luna_worker.toml")
        for contract in (
            "Select the execution surface, role, model, and reasoning from the specialist lanes",
            "complete bounded packet",
            "objective, owned scope, interfaces, constraints, exact checks, return format, and stop conditions",
            "Use isolated context when independence requires it",
            "If a required role or execution surface is unavailable, mark that lane `blocked`",
            "Do not silently change its model or execution surface",
        ):
            self.assertIn(contract, policy)
        self.assertNotIn("Luna delegation", policy)
        self.assertNotIn("delegation envelope", policy)
        self.assertNotIn("Luna delegation", routing)
        self.assertNotIn("delegation envelope", routing)
        self.assertTrue((PLUGIN / "agents/luna_worker.toml").is_file())
        self.assertIn('model = "gpt-5.6-luna"', profile)
        self.assertNotIn("model_reasoning_effort", profile)
        self.assertNotIn("delegation envelope", profile)
        self.assertIn("request exceeds the supplied scope", profile)
        self.assertIn("Do not independently review,\nverify, or accept your own work", profile)
        self.assertIn(
            "The only task-creation exceptions are the Project Lead authorized by an explicit "
            "`$codex-kit:commission` invocation, the one Workstream task authorized by an "
            "explicit `$codex-kit:launch` invocation.",
            policy,
        )

    def test_bootstrap_has_one_project_change_gate_and_no_task_actions(self) -> None:
        bootstrap = flat("skills/bootstrap/SKILL.md")
        self.assertIn("approve the exact final project-file changes", bootstrap)
        self.assertIn("Never create, inspect, pin, unpin, archive, or message a Project Lead task", bootstrap)
        self.assertIn("direct the operator to invoke `$codex-kit:commission`", bootstrap)
        for removed in (
            "Approve Project Lead creation and pinning",
            "Determine whether one Project Lead already exists",
            "Stage 3: create the Project Lead",
        ):
            self.assertNotIn(removed, bootstrap)

    def test_bootstrap_starts_intake_from_a_short_invocation(self) -> None:
        bootstrap = flat("skills/bootstrap/SKILL.md")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Start intake when the skill is invoked", bootstrap)
        self.assertIn("Do not require the operator to specify a mode, technology profile", bootstrap)
        self.assertIn("resolve `../setup/scripts/install.py` relative to this `SKILL.md`", bootstrap)
        self.assertIn("`python3 <setup-script> --check`", bootstrap)
        self.assertIn("If it fails, stop and direct the operator to `$codex-kit:setup`", bootstrap)
        self.assertIn("Ask one short question group at a time", bootstrap)
        self.assertIn("Use $codex-kit:bootstrap.", readme)
        self.assertNotIn("This is a brownfield project.", readme)
        self.assertNotIn("Run the deterministic scaffold in preview mode.", readme)

    def test_bootstrap_uses_one_intake_with_independent_state_facts(self) -> None:
        bootstrap = flat("skills/bootstrap/SKILL.md")
        for contract in (
            "The script is read-only",
            "Use the same intake core for every combination",
            "source_state",
            "prior_agent_footprint",
            "Agent files do not make an otherwise empty project brownfield",
            "The script hints do not replace operator confirmation",
            "Never inspect ignored files, source files recursively, secrets",
            "structural check as semantic approval",
        ):
            self.assertIn(contract, bootstrap)
        self.assertNotIn("RESET REQUIRED", bootstrap)
        self.assertNotIn("brownfield-classification.md", bootstrap)
        self.assertNotIn("native Terra", bootstrap)

    def test_bootstrap_replaces_prior_footprints_only_after_one_diff_gate(self) -> None:
        bootstrap = flat("skills/bootstrap/SKILL.md")
        for contract in (
            "Do not create placeholder project files",
            "Current Codex Kit files do not block repeated project intake",
            "Lift unchanged",
            "Transform it into the new project truth",
            "Recreate it from current evidence and intake",
            "Remove it when it is obsolete",
            "Prepare one exact project-change diff",
            "Never delete an agent footprint automatically",
            "apply only the approved diff with normal project edits",
        ):
            self.assertIn(contract, bootstrap)
        for removed in ("--skip-baseline", "--overwrite", "--scan-existing-project"):
            self.assertNotIn(removed, bootstrap)

    def test_bootstrap_uses_version_2_and_stack_neutral_skill_rules(self) -> None:
        bootstrap = flat("skills/bootstrap/SKILL.md")
        for contract in (
            "version: 2",
            "source_state: greenfield",
            "prior_agent_footprint: absent",
            "Do not add a singular profile field",
            "Reference an installed shared skill",
            "Do not copy a shared skill into the project",
            "unique, repeatable project workflow",
            "Record missing reusable capability candidates without creating or promoting",
        ):
            self.assertIn(contract, bootstrap)

    def test_commission_creates_one_lead_without_old_task_inspection(self) -> None:
        commission = flat("skills/commission/SKILL.md")
        for contract in (
            "explicit invocation authorizes creation and pinning of exactly one",
            "Confirm that no pinned Project Lead exists",
            "Accept an optional transient packet only when the human supplies it",
            "Do not inspect its transcript, unpin it, archive it, or prepare a handoff",
            "Create one task in the saved project with the canonical model and reasoning",
            "Convert only the first character of the project profile value to uppercase",
            "preserve all remaining characters. Set the exact title `Project Lead - <Project>`",
            "The created task input authorizes acknowledgment only",
            "Do not include a downstream skill name, token, link, or path in that input",
            "take no Workstream action, ask no Workstream question",
            "wait for a separate future human request",
            "Do not retry, replace, archive, unpin, or create another task",
        ):
            self.assertIn(contract, commission)
        self.assertNotIn("`$codex-kit:launch`", commission)
        self.assertNotIn("succession assessment", commission.lower())
        self.assertNotIn("read the current Project Lead task", commission)

    def test_canonical_launch_contract_is_one_attempt(self) -> None:
        policy = flat("references/operating-model.md")
        for contract in (
            "exact title `Project Lead - <Project>`",
            "only inside the pinned `Project Lead - <Project>` task",
            "Only a new human-authored message in the pinned Project Lead task can authorize",
            "Delegated task-creation input, a skill link or path, a quoted example, a summary, a prohibition, or a future instruction does not authorize",
            "do not inspect project or task state, ask for a Workstream purpose, or take a Workstream action",
            "Verify the current task identity, saved project, and pin state",
            "Do not forward, create, or message a task",
            "free-text purpose or one external work-item reference",
            "purpose-built read-only MCP",
            "input, not authority",
            "connector or canonical work-item ID cannot be resolved",
            "authorizes one attempt to create, verify, and start exactly one Workstream task",
            "stream - <purpose>",
            "stream - <ticket_id>",
            "Run the task in the saved project's primary folder",
            "with the local task environment",
            "Name it `codex/<slug>`",
            "Allow only one active writing Workstream for each saved project",
            "Let Git manage all data under `.git`; do not create a custom Git metadata path",
            "For a non-Git project, use the saved project's primary folder directly",
            "Do not create a Codex worktree, project checkout, environment, or project artifact under `CODEX_HOME`",
            "base commit SHA",
            "Pass the selected model and reasoning as task-creation arguments",
            "verified Project Lead task ID, created Workstream task ID",
            "report the task ID, project folder, created branch when applicable, and failed phase",
            "The human owns failed-task cleanup, duplicate prevention, recovery",
            "The Project Lead has no post-launch Workstream status or coordination role",
        ):
            self.assertIn(contract, policy)
        for removed in ("launch-blocked", "Retry the failed phase", "recorded task IDs", "isolated Git worktree"):
            self.assertNotIn(removed, policy)

    def test_launch_applies_one_attempt_procedure(self) -> None:
        launch = flat("skills/launch/SKILL.md")
        for contract in (
            "read it. Apply its Project Lead identity gate",
            "Before project or task inspection, apply the current-human-message authority gate",
            "The current input must be a new human-authored message that directly invokes this skill",
            "Delegated task-creation input, a skill link or path, a quoted example, a summary, a prohibition, or a future instruction is not authority",
            "stop without inspecting project or task state, asking for a Workstream purpose, or taking a Workstream action",
            "one free-text purpose or one external work-item reference",
            "Apply the tier matrix in the canonical policy",
            "Mechanically require every exact canonical human-brief mapping",
            "Reject a missing, renamed, duplicated, merged, or invalid field",
            "topology outside the allowed enum",
            "Transmit the exact mappings unchanged",
            "Leave detailed questions and planning to the Workstream Lead",
            "An explicit invocation authorizes one launch attempt and no retry",
            "Resolve the saved project's primary folder and repository kind",
            "verify that no other active writing Workstream uses the primary folder",
            "resolve the default branch unless the request names another existing branch or ref",
            "Derive a concise valid branch name `codex/<slug>`",
            "Let Git manage all data under `.git`; do not create a custom Git metadata path",
            "For a non-Git project, do not create a branch",
            "Create exactly one same-project, user-visible task with the canonical title",
            "in the saved project's primary folder with the local task environment",
            "Pass the selected model and reasoning as creation arguments",
            "Verify the accepted model, reasoning, saved project, primary folder",
            "report the created task ID, project folder, created branch when applicable",
            "Do not use a native subagent or a Codex worktree",
            "Do not create a project checkout, environment, or project artifact under `CODEX_HOME`",
            "invoke `$codex-kit:auto-deliver` in the new task",
            "Validate and transmit unchanged the exact canonical mappings",
            "required spawned execution, allowed topology",
            "independent fresh read-only review, spawned remediation",
            "direct the human to the Workstream task",
            "Do not track, inspect, summarize, retry, accept, or close the Workstream",
        ):
            self.assertIn(contract, launch)
        for removed in ("launch-blocked", "Reuse this task", "observed overlaps", "last-observed"):
            self.assertNotIn(removed, launch)
        self.assertNotIn("GPT-5.6 Terra", launch)
        self.assertNotIn("GPT-5.6 Sol", launch)

    def test_launch_packet_requires_spawned_execution_and_assurance(self) -> None:
        policy = read("references/operating-model.md")
        match = re.search(r"```text\n(?P<records>lead\.model: .+?\n)```", policy, re.DOTALL)
        self.assertIsNotNone(match)
        assert match is not None
        records = tuple(
            tuple(line.split(": ", 1))
            for line in match.group("records").strip().splitlines()
        )
        expected = (
            ("lead.model", "<selected model>"),
            ("lead.reasoning", "<selected effort>"),
            ("lead.mutation_authority", "none"),
            ("execution.required", "true"),
            ("execution.spawn_required", "true"),
            ("execution.topology", "<single_spawned_writer | sequential_spawned_executors | parallel_bounded_executors>"),
            ("execution.delegation_authorized", "true"),
            ("execution.model_selection_basis", "assigned-task complexity"),
            ("execution.writer_policy", "one writer per overlapping file set"),
            ("execution.fallback_to_lead", "forbidden"),
            ("review.independent", "true"),
            ("review.fresh_agent", "true"),
            ("review.read_only", "true"),
            ("review.executor_can_self_review", "false"),
            ("review.lead_can_substitute", "false"),
            ("remediation.performed_by", "spawned_executor"),
            ("remediation.lead_role", "adjudicate_and_assign"),
            ("remediation.material_changes_require_independent_reverification", "true"),
            ("commit.human_authorization_required", "true"),
            ("commit.performed_by", "spawned_executor"),
            ("commit.lead_may_commit", "false"),
        )

        self.assertEqual(records, expected)
        selected_topologies = (
            "single_spawned_writer",
            "sequential_spawned_executors",
            "parallel_bounded_executors",
        )

        def runtime_records_are_valid(candidate: tuple[tuple[str, str], ...]) -> bool:
            """Return whether candidate has exact keys and one allowed topology value."""
            if len(candidate) != len(expected) or len({key for key, _ in candidate}) != len(candidate):
                return False
            expected_values = dict(expected)
            candidate_values = dict(candidate)
            if tuple(candidate_values) != tuple(expected_values):
                return False
            return (
                candidate_values["execution.topology"] in selected_topologies
                and all(
                    candidate_values[key] == value
                    for key, value in expected_values.items()
                    if key != "execution.topology"
                )
            )

        for topology in selected_topologies:
            runtime_records = tuple(
                (key, topology) if key == "execution.topology" else (key, value)
                for key, value in records
            )
            self.assertTrue(runtime_records_are_valid(runtime_records))
        runtime_records = tuple(
            (key, selected_topologies[0]) if key == "execution.topology" else (key, value)
            for key, value in records
        )
        self.assertFalse(runtime_records_are_valid(runtime_records[:-1]))
        self.assertFalse(runtime_records_are_valid((("lead.model_name", "<selected model>"), *runtime_records[1:])))
        self.assertFalse(runtime_records_are_valid((("lead.model", "<selected model>; <selected effort>"), *runtime_records[2:])))
        self.assertFalse(runtime_records_are_valid((*runtime_records, runtime_records[0])))
        for invalid_topology in (
            "<single_spawned_writer | sequential_spawned_executors | parallel_bounded_executors>",
            "single_spawned_writer | sequential_spawned_executors | parallel_bounded_executors",
            "invalid_topology",
        ):
            self.assertFalse(
                runtime_records_are_valid(
                    tuple(
                        (key, invalid_topology) if key == "execution.topology" else (key, value)
                        for key, value in runtime_records
                    )
                )
            )
        old_aliases = (
            ("execution.shared_checkout", "execution.writer_policy"),
            ("review.fresh_independent_read_only", "review.independent"),
            ("review.executor_or_lead_substitution", "review.lead_can_substitute"),
            ("remediation.spawned_executor_required", "remediation.performed_by"),
            ("commit.spawned_executor_after_human_authority", "commit.performed_by"),
        )
        for alias, canonical_key in old_aliases:
            self.assertFalse(
                runtime_records_are_valid(
                    tuple(
                        (alias, value) if key == canonical_key else (key, value)
                        for key, value in runtime_records
                    )
                )
            )
            self.assertNotIn(f"{alias}:", match.group("records"))
        self.assertIn("The Lead rejects a packet with a missing, renamed, duplicated,", policy)
        self.assertIn("It transmits the exact mappings unchanged", policy)
        self.assertIn("Angle brackets and vertical bars in the template are notation", policy)
        self.assertIn("The joined alternatives and the placeholder are", policy)
        self.assertIn("not valid transmitted values", policy)

    def test_auto_deliver_plan_identifies_active_procedure(self) -> None:
        """Verify that every plan identifies the active delivery procedure."""
        delivery = read("skills/auto-deliver/SKILL.md")
        delivery_flat = flat("skills/auto-deliver/SKILL.md")
        match = re.search(
            r"   ```text\n(?P<block>   Delivery procedure: \$codex-kit:auto-deliver.+?)\n   ```",
            delivery,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        assert match is not None
        records = tuple(line.strip() for line in match.group("block").splitlines())
        self.assertEqual(
            records,
            (
                "Delivery procedure: $codex-kit:auto-deliver (already active)",
                "Lead mutation authority: none",
                "Execution topology: <selected topology>",
                "Executor assignments: <agent, model, reasoning, scope, and owned files>",
                "Assurance: <review and verification tiers>",
            ),
        )
        self.assertNotIn("/plugins/cache/", match.group("block"))
        self.assertIn("It does not invoke the skill again", delivery_flat)
        self.assertIn(
            "Mutation authorization: absent; no executor starts.",
            delivery_flat,
        )

    def test_auto_deliver_plans_before_execution_and_closes(self) -> None:
        delivery = flat("skills/auto-deliver/SKILL.md")
        for contract in (
            "This skill executes one launched Workstream",
            "Before editing, verify the launch packet, Project Lead task ID, current Workstream task ID, saved project, primary folder, repository kind, and the recorded branch for Git projects",
            "stop without editing and direct the user to the verified Project Lead",
            "The Lead has `mutation_authority: none`",
            "It must not implement, remediate, integrate, stage, commit, mutate an environment, or run protected execution",
            "Do not create or provision an environment",
            "Require human approval for an environment change",
            "mark affected checks `blocked`",
            "Resolve required product and implementation decisions with the user",
            "Record safe assumptions",
            "decision-complete plan with acceptance criteria, non-goals, risks, gates, lanes, checks, and stop conditions",
            "Map each criterion and important negative constraint to a check or inspection",
            "Stop when authority, scope, or verification is insufficient",
            "Start every plan with this delivery-control block",
            "Delivery procedure: $codex-kit:auto-deliver (already active)",
            "Lead mutation authority: none",
            "Mutation authorization: absent; no executor starts",
            "Select four decisions separately: Lead tier, execution topology, per-assignment executor model and reasoning, and assurance tier",
            "planning-only Workstream, do not spawn an executor until mutation is authorized",
            "Before the first mutation, spawn a native execution agent",
            "identity, model, reasoning, scope, owned files, authority, and topology",
            "Small work still has one spawned executor",
            "Tightly coupled work can use one executor sequentially",
            "Do not downgrade, substitute, create a user-visible-task fallback, or use a Lead fallback",
            "For every mutation, run a fresh independent read-only reviewer through `scripts/readonly.py`",
            "Run a fresh independent read-only verifier separate from the Lead and every executor",
            "Every remediation mutation receives its own fresh independent read-only review",
            "Material remediation requires a new reviewer and a new verifier",
            "Use `$codex-kit:auto-route-learnings`",
            "Report closure directly to the user",
            "Do not accept or close while a required check or review is `failed`, `blocked`, or `not run`",
            "Completion, Workstream acceptance, and human approval are separate states",
            "Record recovery information before a release or migration",
            "Apply the canonical Git history gate",
            "leave changes unstaged and uncommitted",
            "each check as `passed`, `failed`, `not run`, or `blocked`",
        ):
            self.assertIn(contract, delivery)
        policy = flat("references/operating-model.md")
        self.assertIn("Every authorized mutation is done by at least one spawned native execution agent", policy)
        self.assertIn("There is no Lead-executes fallback", policy)
        self.assertIn("Use one writer for each overlapping file set", policy)
        self.assertIn("Run overlapping scopes serially", policy)
        self.assertIn("Use parallel executors only for non-overlap", policy)
        self.assertIn("The execution agent uses the resolved environment for the complete assignment", policy)
        self.assertIn("It must not create a replacement environment", policy)
        self.assertIn("It invokes absolute environment binaries", policy)
        self.assertIn("An install, package update, or other environment change requires explicit human approval", policy)
        self.assertIn("If no compatible environment exists", policy)
        self.assertIn("Do not let `uv run` provision an environment automatically", policy)
        self.assertIn("Normal, well-specified implementation or remediation: GPT-5.6 Terra with Medium reasoning", policy)
        self.assertIn("Complex debugging, cross-module implementation or remediation", policy)
        self.assertIn("data-loss risk, or broad runtime impact: GPT-5.6 Terra with High reasoning", policy)

    def test_git_history_and_push_have_separate_human_gates(self) -> None:
        policy = flat("references/operating-model.md")
        for contract in (
            "Treat every Git history or reference change as a protected action",
            "commit, amend, merge, cherry-pick, rebase, squash, revert, tag creation",
            "human-authored message in the task that controls the action directly requests the scoped history action",
            "when the human approves an exact request",
            "explicit `$codex-kit:launch` invocation authorizes only the one branch creation and checkout required by that launch",
            "It does not authorize a commit or another ref change",
            "Planning, implementation, review, verification, acceptance, and auto-deliver completion do not grant authority",
            "Each approval covers only the described action and change scope",
            "A push is a separate external write and requires separate explicit human approval",
            "After the human gives scoped commit authority, a spawned executor stages and commits the approved scope",
            "The Lead never stages or commits",
        ):
            self.assertIn(contract, policy)

        launch = flat("skills/launch/SKILL.md")
        self.assertIn("An explicit invocation authorizes one launch attempt and no retry", launch)
        self.assertIn("create and check out the normal Git branch", launch)

    def test_project_lead_is_commissioned_and_has_no_status_role(self) -> None:
        policy = flat("references/operating-model.md")
        commission = flat("skills/commission/SKILL.md")
        self.assertIn("`$codex-kit:bootstrap` owns initial project intake", policy)
        self.assertIn("`$codex-kit:commission` creates and pins", policy)
        self.assertIn("The Project Lead reads approved project truth", policy)
        self.assertIn("The human invokes `$codex-kit:launch` only inside", policy)
        self.assertIn("does not track, inspect, summarize, retry, accept, message, or close", policy)
        self.assertIn("The human uses each Workstream task directly", policy)
        self.assertIn("canonical Project Lead model, reasoning, role, and boundaries", commission)
        self.assertFalse((PLUGIN / "agents/project_lead.toml").exists())

    def test_readme_explains_catalog_and_workstream_lifecycle(self) -> None:
        source = (ROOT / "README.md").read_text(encoding="utf-8")
        readme = " ".join(source.split())
        self.assertEqual(source.count("```mermaid\nflowchart TD"), 1)
        self.assertEqual(source.count("```mermaid\nflowchart LR"), 1)
        for contract in (
            'U["User"] -->|"First machine setup"| S["$codex-kit:setup"]',
            'B -->|"Approved project truth"| Q["$codex-kit:commission"]',
            'Q -->|"One authorized task"| L["Pinned Project Lead - Project"]',
            'L -->|"$codex-kit:launch authorizes one attempt"| W["stream - purpose or ticket ID"]',
            'W --> I["Saved project primary folder"]',
            'I --> D["$codex-kit:auto-deliver"]',
            'D --> C["Workstream Lead reports closure to user"]',
            'I["Detailed intake"] --> P["Decision-complete plan"]',
            'P --> E["Spawned execution agent"]',
            'E --> R["Fresh independent review"]',
            'M --> RR["Fresh independent review after remediation"]',
            'RR --> V["Fresh independent verification"]',
            'L --> C["Close directly with user"]',
            "Project Lead remains available for new intake and launch requests",
            "user-visible Codex task, not a native subagent",
            "It is read-only. A spawned execution agent performs every authorized mutation",
            "four primary human entry skills",
            "requires the verified pinned Project Lead",
            "Run `$codex-kit:bootstrap` in the target project",
            "Invoke `$codex-kit:commission` in a fresh task",
        ):
            self.assertIn(contract, readme)
        for removed in ("$codex-kit:project", "$codex-kit:succession", "$codex-kit:workstream"):
            self.assertNotIn(removed, source)

    def test_operator_guide_uses_spawned_execution_and_fresh_assurance(self) -> None:
        guide = (ROOT / "Codex Kit — Project & Workstream Guide.html").read_text(encoding="utf-8")
        for contract in (
            "Spawned<br>execution",
            "Terra Medium small, Terra High normal, Sol High protected, high-risk, or difficult-integration mutations",
            "Spawned<br>remediation",
            "Fresh review<br>after remediation",
            "Fresh<br>verification",
            "Lead adjudicates<br>and closes",
            "The Workstream Lead is read-only",
        ):
            self.assertIn(contract, guide)
        self.assertIn("fresh review for protected, high-risk, or difficult-integration mutations", guide)
        self.assertNotIn("completes review and verification", guide)

    def test_script_documentation_rule_is_managed_and_language_neutral(self) -> None:
        rule = (
            "Document every callable that Codex creates or materially changes in a "
            "tool or script. Use Google-style docstrings for Python or the standard "
            "equivalent for the language. Do not expand the task to untouched legacy "
            "callables."
        )
        delivery = flat("skills/auto-deliver/SKILL.md")
        installer = " ".join(read("skills/setup/scripts/install.py").replace('"', "").split())
        self.assertIn(rule, delivery)
        self.assertIn(rule, installer)
        reference = read("references/script-documentation.md")
        for equivalent in ("JSDoc or TSDoc", "Javadoc", "Doxygen-compatible comments", "documentation comments", "rustdoc", "POD", "comment-based help"):
            self.assertIn(equivalent, reference)

    def test_auto_route_learnings_classifies_destinations(self) -> None:
        knowledge = flat("skills/auto-route-learnings/SKILL.md")
        for destination in ("Project documentation", "Codex Kit", "Current task", "Do not preserve"):
            self.assertIn(destination, knowledge)
        for transient in ("workstream status", "task identifiers", "handoff drafts"):
            self.assertIn(transient, knowledge)
        self.assertIn("user asks Codex to remember accepted information", knowledge)
        self.assertFalse((PLUGIN / "skills/vault-memory/SKILL.md").exists())

    def test_tool_proposal_requires_reuse_and_ownership_evidence(self) -> None:
        knowledge = flat("skills/auto-route-learnings/SKILL.md")
        for field in ("duplicate search", "reuse check", "owner", "maintenance cost", "security boundary", "validation plan", "explicit approval"):
            self.assertIn(field, knowledge)

    def test_portfolio_has_two_read_only_modes(self) -> None:
        portfolio = flat("skills/portfolio/SKILL.md")
        for contract in (
            "Project Lead mode",
            "Project mode",
            "Project Lead - <Project>",
            "missing or ambiguous",
            "explicit list of project roots or saved projects",
            "Do not create or message tasks",
            "Do not run tests",
        ):
            self.assertIn(contract, portfolio)


if __name__ == "__main__":
    unittest.main()
