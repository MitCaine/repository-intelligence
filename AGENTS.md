# Working on Repository Intelligence

> **Defunct project — historical reference only.** RI is no longer developed or maintained.
> See [project status](README.md#project-status). Instructions and commands below describe the retained snapshot,
> not an actively supported workflow; existing pinned consumers retain their own authority.


This is the standalone RI package. Poker App and Nutrition App capsules,
session scripts, database rules, and consumer-specific authority maps do not
apply here. The current user request defines the task scope.

- Inspect the checkout status and preserve unrelated changes before editing.
- Read README.md for project purpose or first-use questions. Read
  docs/architecture.md when changing module seams or ownership. Use
  docs/README.md to find the current contract relevant to the task.
- Keep scanning, source identity, adapter semantics, ranking, and comparison at
  their existing seams. Ordinary operations remain language-neutral and local;
  native Rust analysis remains a separate optional operation.
- Add independently expected source slices, names, kinds, or deltas for defects.
  Counts agreeing with other production counters alone do not prove correctness.
- Do not weaken incomplete/unsupported/excluded results to make tests pass.
- Review compatibility versions when source identity, classification, coverage,
  or comparison behavior changes. Update current docs and package assertions.
- Keep package pins only in pyproject.toml; use scripts/maintain.py for shared
  environment preparation and verification. Follow docs/maintenance.md for
  grammar updates, native tools, and offline wheel verification. Run git diff
  --check and report skips and unavailable checks.
- Keep source acquisition bounded and read-only. Avoid new services, registries,
  persistent indexes, or consumer permission policy without a concrete need.
- For this standalone RI checkout, do not commit, push, merge, or change
  repository settings unless requested. This restriction does not override the
  documented consumer workflow: one author engineers and implements, and a fresh
  independent reviewer assesses the exact candidate against original requirements.
  Project authority still controls qualification, capture/publication, integration
  and closeout; useful RI tools do not grant those permissions. Preserve active
  attempts' selected instructions and historical compatibility. No subagent pushes
  directly to `main`; the consumer's acceptance route controls integration.
