---
name: setup
description: Preview, install, check, upgrade, repair, or uninstall Codex Kit managed machine files with the deterministic installer bundled in the plugin. Use when an operator invokes Codex Kit setup after plugin installation or upgrade, asks to validate the machine setup, or asks to remove Kit-owned machine files before plugin removal.
---

# Codex Kit Setup

Use the installer at `scripts/install.py`, resolved relative to this `SKILL.md`.
Do not ask the operator to find the plugin cache or run Python manually.

## Safety rules

- Run a preview before each install, upgrade, repair, or uninstall write.
- Show the exact preview output and stop for explicit approval.
- Explain that writes under `CODEX_HOME` can need approval because they are
  outside the current project.
- Do not change model settings.
- Do not install or remove the plugin.
- Do not add, upgrade, or remove a marketplace.
- Do not edit a managed file when the installer refuses the operation.
- Do not bypass a managed-path safety refusal. Repair the path before a new
  preview.

## Install, upgrade, or repair

1. Resolve `scripts/install.py` from this skill directory.
2. Run `python3 <resolved-script> --dry-run`.
3. Report each proposed write. Stop for explicit approval.
4. After approval, run `python3 <resolved-script>`.
5. Run `python3 <resolved-script> --check`.
6. Report the apply and check results separately.

Use the same procedure for initial setup, upgrade, and repair. The installer
uses its state and file hashes to select the safe action. It does not support
symlinked `CODEX_HOME` or managed paths. Start a fresh setup task after each
plugin upgrade so that it uses the current plugin code.

## Check

Run `python3 <resolved-script> --check`. This operation is read-only. Report
each error and do not repair it without a new preview and approval.

## Uninstall

1. Run `python3 <resolved-script> --uninstall --dry-run`.
2. Report each proposed removal. Stop for explicit approval.
3. After approval, run `python3 <resolved-script> --uninstall`.
4. Confirm that the installer removed only files that it still owned.
5. Tell the operator that plugin removal is now a separate next step.
