---
name: commission
description: Create and pin exactly one first or replacement Project Lead from approved project truth and current Codex Kit policy. Use after project bootstrap or after the human archives a prior lead and prepares any needed transient packet.
---

# Commission

An explicit invocation authorizes creation and pinning of exactly one
user-visible Project Lead task. It does not authorize a second attempt.

1. Resolve the saved local project and its primary folder. Resolve
   `../bootstrap/scripts/project.py` relative to this `SKILL.md` and run:

   `python3 <script> --project-root <root> --check`

   Stop when the structural check fails.
2. Read `AGENTS.md`, `.agents/project-profile.yaml`,
   `docs/codex/project-truth.md`, and `docs/codex/verification.md`. Confirm that
   the profile status is `intake-approved`. Treat these files as the durable
   source of truth.
3. Resolve `../../references/operating-model.md` relative to this `SKILL.md`,
   then read it. Use its canonical Project Lead model, reasoning, role, and
   boundaries.
4. Confirm that no pinned Project Lead exists for the saved project. Stop when
   one exists. Do not inspect its transcript, unpin it, archive it, or prepare
   a handoff.
5. Accept an optional transient packet only when the human supplies it in the
   current request. Label it as temporary input. Do not investigate an old
   lead or any Workstream to complete it. Project truth and human gates take
   precedence over the packet.
6. Confirm that Codex can resolve the saved project, create and read a
   user-visible task, set its title, and pin it. Stop before creation when a
   required control is unavailable.
7. Create one task in the saved project with the canonical model and reasoning.
   Give it the durable truth paths, a concise project summary, the optional
   packet, its role boundary, and its initial stop condition. Do not make the
   task prompt the only copy of accepted project truth. The created task input
   authorizes acknowledgment only. Do not include a downstream skill name,
   token, link, or path in that input.
8. Convert only the first character of the project profile value to uppercase
   and preserve all remaining characters. Set the exact title
   `Project Lead - <Project>` and pin the task. Tell the Project Lead to read
   and acknowledge its project, role, boundaries, and durable sources. Tell it
   to take no Workstream action, ask no Workstream question, end its turn after
   acknowledgment, and wait for a separate future human request.
9. Verify the task identity, accepted model and reasoning, saved project,
   title, pin state, and acknowledgment. Report only independently observed
   settings.

Report the created task ID and verified state. If creation, configuration,
pinning, or acknowledgment fails, report the observed task identity and failed
phase, then stop. Do not retry, replace, archive, unpin, or create another task.
