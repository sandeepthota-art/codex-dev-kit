---
name: bootstrap
description: Inspect greenfield, brownfield, or existing Codex Kit project evidence, run one comprehensive operator intake, replace or create durable project guidance through one exact approval gate, and validate the approved result. Use for initial project intake or an approved project-guidance migration after a Codex Kit upgrade.
---

# Bootstrap

Start intake when the skill is invoked. Do not require the operator to specify
a mode, technology profile, command, or approval gate in the initial request.
First, resolve `../setup/scripts/install.py` relative to this `SKILL.md` and run
`python3 <setup-script> --check`. This check is read-only. If it fails, stop and
direct the operator to `$codex-kit:setup`. Do not start project intake.

Use one gate: approve the exact final project-file changes. Do not create
placeholder project files. Do not change a project before this gate. Never
create, inspect, pin, unpin, archive, or message a Project Lead task.

## Stage 1: inspect and conduct intake

1. Resolve the project root from the saved local project's primary folder.
   State the absolute root. Ask only for the absolute root when one clear root
   is not available. The root must be an existing ordinary directory. Symlinks
   are not supported.
2. Resolve `scripts/project.py` relative to this `SKILL.md`. Run:

   `python3 <script> --project-root <root>`

   The script is read-only. It does not scaffold, replace, delete, or edit the
   project. It returns shallow root evidence, configuration candidates, agent
   footprint candidates, documentary truth candidates, ignore status, and two
   hints.
3. When the report says that ignore evaluation is unavailable, do not perform
   automated discovery. Explain that the existing `.gitignore` could not be
   applied and rely on operator intake. Never inspect ignored files, source
   files recursively, secrets, credentials, private keys, certificates, or
   environment files.
4. Read only selected safe text configuration candidates that can inform the
   intake. Do not add language-specific parsing to the script. Treat every
   detected language, framework, platform, infrastructure system, design
   system, command, and review need as evidence, not as a singular profile.
5. Ask the operator to confirm these two independent facts:

   - `source_state`: `greenfield` or `brownfield`.
   - `prior_agent_footprint`: `absent` or `present`.

   `greenfield` means that there is little or no source. `brownfield` means
   that source, tests, assets, or other implementation artifacts exist. Agent
   files do not make an otherwise empty project brownfield. `absent` means no
   footprint was detected and the operator confirmed that result. The script
   hints do not replace operator confirmation.
6. Use the same intake core for every combination. Ask one short question
   group at a time. Confirm purpose, current objective, success criteria,
   non-goals, architecture, languages, frameworks, platforms, infrastructure,
   design systems, constraints, risk boundaries, approval boundaries, release
   controls, test commands, lint commands, build commands, review needs, and
   expected work. Use repository evidence to make the questions more specific.
   Accept direct operator-provided truth when repository evidence is absent.
7. When `prior_agent_footprint` is `present`, inspect the detected safe text
   instructions, truth documents, local skills, hooks, and coordination files.
   Treat foreign, legacy, and current Codex Kit files the same way. Current
   Codex Kit files do not block repeated project intake. For each item, propose
   exactly one disposition:

   - Lift unchanged when it is current, project-specific, and compatible.
   - Transform it into the new project truth or project guidance.
   - Recreate it from current evidence and intake.
   - Remove it when it is obsolete, duplicated, temporary, or conflicting.

   Replace recognized prior orchestration and duplicate shared skills by
   default. Preserve source code, assets, and evidence-backed project facts.
   Treat an existing version 1 project profile as migration evidence and
   propose its replacement with version 2.
8. Check matching installed plugin skill metadata before proposing project
   skill guidance. Reference an installed shared skill from `AGENTS.md` when an
   actual matching skill exists. Do not copy a shared skill into the project.
   Preserve a repository-local skill only when it implements a unique,
   repeatable project workflow. When a local skill duplicates a shared skill,
   propose removal of the local copy and reference the installed skill. Record
   missing reusable capability candidates without creating or promoting them.

## Stage 2: apply approved project changes

1. Prepare one exact project-change diff. Include every proposed creation,
   edit, move, and deletion. The final project must contain:

   - `AGENTS.md`
   - `.agents/project-profile.yaml`
   - `docs/codex/project-truth.md`
   - `docs/codex/verification.md`

2. Preserve unrelated project-owned instructions when they remain compatible.
   Remove or replace obsolete Codex Kit skill invocations and recognized prior
   orchestration only in the proposed diff. Never delete an agent footprint
   automatically.
3. Put accepted purpose, architecture, languages, frameworks, platforms,
   infrastructure, design systems, constraints, risk, approval, release, and
   capability facts in project truth. Put confirmed test, lint, build, and
   release commands and review needs in verification guidance.
4. Use this version 2 profile schema. Serialize the project name with JSON
   double-quoted syntax, which is valid YAML. Do not add a singular profile
   field.

   ```yaml
   version: 2
   project: "<project>"
   source_state: greenfield
   prior_agent_footprint: absent
   status: intake-approved
   ```

   Set the two state values to the operator-confirmed values.
5. Show the complete exact diff. Include proposed Brownfield B dispositions
   with their resulting changes. Do not write or remove files. Stop for
   explicit approval.
6. After approval, apply only the approved diff with normal project edits.
   Compare every resulting creation, edit, move, and deletion with the approved
   diff.
7. Run:

   `python3 <script> --project-root <root> --check`

   This check validates required files and version 2 profile structure only.
   The current task must verify that the written truth matches the approved
   intake. Do not treat the structural check as semantic approval.
8. Report the validated project truth paths and unresolved intake gaps. Stop
   and direct the operator to invoke `$codex-kit:commission` when they want one
   new pinned Project Lead.
