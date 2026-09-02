# Codex Kit Instructions

This repository contains reusable Codex project operations. Keep all policy
project-neutral.

## Required rules

- Use ASD-STE100 Simplified Technical English for new or active prose.
- Keep `AGENTS.md` short. Put task procedures in skills.
- Keep one canonical rule. Do not copy policy into several files.
- Do not create a reusable tool without explicit human approval and a reuse
  check.
- Do not add project data to this repository.
- Keep project truth in the consuming project. Keep temporary coordination in
  Codex tasks.
- Do not add automatic Project Lead succession.

## Verification

Run:

```bash
python3 tools/doctor.py --kit-root .
python3 -m unittest discover -s tests
git diff --check
```

State which checks passed, failed, or were not run.
