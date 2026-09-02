---
name: portfolio
description: Compare live Project Lead identity and readiness or explicit repositories for cross-project state, stale leads, shared blockers, repository health, or a concise portfolio review.
---

# Portfolio

Select one mode. Use `project-lead` for live lead identity and readiness. Use
`project` for source-grounded repository status.

## Project Lead mode

Use a temporary Sol task with High reasoning for a substantial multi-project
review. Do not create that task unless the user requests it.

1. Use Codex task tools to list recent tasks.
2. Convert only the first character of each project profile value to uppercase
   and preserve all remaining characters. Select candidates with the exact
   title `Project Lead - <Project>`.
3. Validate each candidate against its reported project context. Do not infer a
   role from its title alone.
4. If candidates are missing or ambiguous, report the gap and request the
   required project or task selection.
5. Read the selected tasks. Report identity, project, pin state, readiness, and
   last observed activity. Do not inspect or report Workstream state.
6. Separate direct task observations from inferences. Do not claim that task
   state is durable.

## Project mode

1. Require an explicit list of project roots or saved projects.
2. Read each project's instructions, project truth, verification guidance,
   declared goals, current revision, and Git status.
3. Compare declared state with repository evidence and recorded verification.
4. Report stale guidance, uncommitted work, unclear goals, missing evidence,
   important risks, and the next human decision.
5. Do not run tests or other commands that change external state unless the
   user separately requests them.

## Boundaries

Remain read-only. Do not create or message tasks, change priority, edit project
files, pin or archive a task, or commission a Project Lead. Recommend at most
three next actions. Route an approved follow-up through the applicable skill.
