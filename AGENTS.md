# Codex Resolve development

Purpose: natural-language editing in Codex with DaVinci Resolve 21. The user supplies creative intent; the agent maintains technical plans and records.

- Read docs/CAPABILITIES.md before describing what is implemented. Historical validation does not certify this port.
- User requested no tests for this initial preparation. None were run. Do not claim validation. Future validation follows the then-current user scope.
- Never embed personal paths, named performers, song offsets, local model locations or historical project preferences in public defaults.
- Importing modules must not connect to Resolve or modify projects. Resolve object mutations require an explicit task target and recoverable work version.
- Internal time ranges are zero-based [start,end); rates are rational. Adapt API boundaries explicitly and inspect actual results.
- Preserve originals and accepted versions. Agent records and file checkpoints do not substitute for DRP backups.
- Keep SKILL.md concise; put workflow detail in linked references. Skills guide creativity; tools handle repeatable operations.
- Keep capability status, implementation and docs consistent. No simulated success or silent effect downgrade.
- Do not bundle third-party runtimes, models, paid software, media, LUTs or copied SDK documentation.

This repository is independent of the historical local toolkit and does not authorize modifying any original video project.
