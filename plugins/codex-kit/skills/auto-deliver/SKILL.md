---
name: auto-deliver
description: Agent-only read-only Workstream Lead procedure for launched streams that performs detailed intake, plans and orchestrates spawned execution, obtains fresh assurance, applies gates, routes learning, and reports closure.
---

# Auto Deliver

Resolve every relative path in this skill relative to this `SKILL.md`. Read
`../../references/operating-model.md` and apply its canonical policy. This skill
executes one launched Workstream.

## Start gates

Before editing, verify the launch packet, Project Lead task ID, current
Workstream task ID, saved project, primary folder, repository kind, and the
recorded branch for Git projects. If an item is absent or does not match, stop
without editing and direct the user to the verified Project Lead.

The Lead has `mutation_authority: none`. It can use read-only project commands
only. It must not implement, remediate, integrate, stage, commit, mutate an
environment, or run protected execution. An execution agent uses a compatible
existing project environment, absolute environment binaries, and the primary
project folder. Do not create or provision an environment. Require human
approval for an environment change. If no compatible environment exists, mark
affected checks `blocked`.

When work changes a tool or script, read
`../../references/script-documentation.md`. Document every callable that Codex
creates or materially changes in a tool or script. Use Google-style docstrings
for Python or the standard equivalent for the language. Do not expand the task
to untouched legacy callables.

For a required read-only lane, run `scripts/readonly.py` with the resolved
environment's absolute Python binary. Do not use another execution surface as a
fallback.

## Work loop

1. Inspect project truth, the checkout, and the relevant source.
2. Resolve required product and implementation decisions with the user. Record
   safe assumptions.
3. Produce a decision-complete plan with acceptance criteria, non-goals, risks,
   gates, lanes, checks, and stop conditions. Map each criterion and important
   negative constraint to a check or inspection. Stop when authority, scope, or
   verification is insufficient. Start every plan with this delivery-control
   block. The first line records the active procedure. It does not invoke the
   skill again. Replace each angle-bracket placeholder with selected values.

   ```text
   Delivery procedure: $codex-kit:auto-deliver (already active)
   Lead mutation authority: none
   Execution topology: <selected topology>
   Executor assignments: <agent, model, reasoning, scope, and owned files>
   Assurance: <review and verification tiers>
   ```

   If mutation is not authorized, also state `Mutation authorization: absent;
   no executor starts.`
4. Select four decisions separately: Lead tier, execution topology,
   per-assignment executor model and reasoning, and assurance tier. For a
   planning-only Workstream, do not spawn an executor until mutation is
   authorized.
5. Before the first mutation, spawn a native execution agent. Record its
   identity, model, reasoning, scope, owned files, authority, and topology.
   State shared-checkout preservation and no unrelated-edit revert. Use one
   writer for an overlapping file set. Run overlaps serially. Use parallel
   bounded executors only for non-overlap. Small work still has one spawned
   executor. Tightly coupled work can use one executor sequentially. If spawn,
   model, slot, or sandbox enforcement is unavailable, mark work `blocked`.
   Do not downgrade, substitute, create a user-visible-task fallback, or use a
   Lead fallback.
6. Give each executor a complete bounded packet with its objective, owned
   scope, interfaces, constraints, exact checks, return format, and stop
   conditions. Require each executor to inspect its change and run focused
   checks. The Lead inspects each returned change and evidence.
7. For every mutation, run a fresh independent read-only reviewer through
   `scripts/readonly.py`. Use Terra Medium for small low-risk work, Terra High
   for normal work, and Sol High for protected, high-risk, or
   difficult-integration mutations. Supply the
   absolute project folder and complete bounded packet. Require the reviewer to
   report its effective sandbox before inspection, perform the review
   personally, not implement findings, and not delegate, spawn, or create
   another agent.
8. Run a fresh independent read-only verifier separate from the Lead and every
   executor. The verifier reports claims and checks. If a review finding is
   accepted, route it to an authorized spawned executor. Every remediation
   mutation receives its own fresh independent read-only review before a fresh
   independent verification lane. Material remediation requires a new reviewer
   and a new verifier after remediation.
9. If the helper, report, read-only sandbox, required verifier, or required
   execution agent is unavailable, mark work `blocked`. Do not use a native
   agent, user-visible task, substitute, or Lead fallback.
10. Assess acceptance. Do not accept or close while a required check or review
    is `failed`, `blocked`, or `not run`.
11. Use `$codex-kit:auto-route-learnings` when accepted work changes project
    truth or reveals a reusable operating pattern.
12. Report closure directly to the user.

## Protected completion

Completion, Workstream acceptance, and human approval are separate states.
Apply all canonical human gates. Record recovery information before a release
or migration.

Apply the canonical Git history gate before every history or ref change. When
authority is absent, leave changes unstaged and uncommitted. After exact human
commit authority, spawn an executor to stage and commit the approved scope.
The Lead never stages or commits. Report the exact change, checks, review
result, remaining risk, and proposed history action, then wait for the human.

## Closure report

Report:

- changed scope;
- each check as `passed`, `failed`, `not run`, or `blocked`;
- review findings and accepted evidence;
- unresolved risks and follow-up work;
- the learning-routing result.
