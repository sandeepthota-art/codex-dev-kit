---
name: auto-route-learnings
description: Agent-only accepted-information routing for user memory requests, accepted project truth, or reusable patterns that need the correct source of truth.
---

# Auto Route Learnings

This is an agent-only procedure. Use it implicitly when the user asks Codex to
remember accepted information.

## Classify the knowledge

Read current project truth before you propose a durable change. Select one
destination:

- Project documentation: accepted project purpose, behavior, architecture,
  commands, verification guidance, technical decisions, goals, or risks.
- Codex Kit: project-neutral operating guidance that has repeated and will
  improve future work in more than one project.
- Current task: temporary objectives, sequencing, workstream status, task
  identifiers, handoff drafts, investigation notes, and unaccepted claims.
- Do not preserve: secrets, credentials, private account data, raw transcripts,
  temporary logs, guesses, or duplicated facts.

Identify the exact future decision or action that the knowledge will improve.
If there is no clear use, keep it in the current task or discard it.

## Route a durable change

For project knowledge, identify the existing source-of-truth file. Propose a
focused change and use the authority in the current request. Do not create a
parallel knowledge file when an existing project document owns the fact.

For reusable Kit guidance, search for an existing rule, skill, command, hook,
plugin, MCP server, or maintained open-source tool. Prefer an update to an
existing surface. Require explicit approval before you create or promote a
reusable skill, script, tool, hook, MCP server, or separate repository.

A reusable-tool proposal must record the duplicate search, reuse check,
expected reuse, owner, maintenance cost, security boundary, validation plan,
and explicit approval.

## Report

Report the classification, destination, source evidence, proposed action, and
approval state. Do not claim that temporary task context is durable.
