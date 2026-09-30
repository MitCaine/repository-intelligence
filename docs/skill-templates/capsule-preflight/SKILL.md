---
name: capsule-preflight
description: Authenticate an active task capsule and its exact repository state before capsule implementation, qualification, or review. Use when a consumer project runs a capsule workflow; do not apply to ordinary standalone RI work.
---

# Capsule preflight

For candidate evidence checks, read [the adapter contract](references/evidence-contract.md)
and use [evidence_preflight.py](scripts/evidence_preflight.py) when the consumer
has exported authenticated expectations and observed runner records. A checked
result covers deterministic comparisons only; consumer authority, scope purpose,
remote ref verification and independent review remain required.

For closeout history, use the consumer's current schema-aware builder when
available and validate the draft before the planner returns or commits it.
Validate exact closeout C again before qualification and review. Where live
installation probes are required, use the adapter's closeout checks for metadata,
recovery capsule hash, installed base/workflow and exact probe/check identities.
Require execution of the selected test, an isolated expected negative failure,
and a passing control; a generic job failure or skipped test is insufficient.
The consumer authenticates the exports and the reviewer judges outcome coverage.

Before implementation authorization, require an impact inventory covering implementation, callers, tests, fixtures, workflow assertions, documentation and profile rules, with edit/inspect disposition and reasons per actual path. Search for tests asserting changed structures and profile sets. A fresh read-only scope challenger is required by consumer policy, cross-seam workflow/profile/infra changes or meaningful scope uncertainty. Record the trigger or omission rationale. Resolve findings before READY/P; material inventory/base/scope changes require a fresh challenge of the final identity. Unresolved dependencies block dispatch. Authorization references the completed inventory and challenge. Candidate attachment also references applicable pre-freeze subprocess rehearsal and exact-C protected qualification, including exact source, command, collection settings, isolation policy and result. A host-only pass is insufficient. Consumer tooling enforces these records where supported; this skill cannot supply missing authority.

Treat the consumer repository's current capsule contract and accepted runner as execution authority. Read the active capsule and relevant local workflow instructions; never infer authority from this skill, RI output, issue prose, or an old transcript.

Select the consumer's current phase first. Intake needs objective/authority/base and planning permissions, not future P/C. Planning acceptance needs draft/P, requirement trace and scope/evidence feasibility. Implementation needs ready P and an authorized worktree. Qualification needs C and frozen commands; review needs C/Q and complete accepted report inputs. Integration needs matching approvals/current refs and retrievable retained source/evidence. Resume verifies existing stage, revisions, jobs, findings, remaining allowance and next action against current Git/runner state. Adopt changed rules at a safe boundary and revalidate affected permissions/proof/interfaces; chat reset cannot reset allowances.

Before the requested capsule step, establish the applicable current repository and issue state, capsule revision, planner-created dedicated branch under controller direction and recorded remote, exact base and planning identities, active overlay, allowed reads and edits, acceptance criteria, required checks, supported host, and stop conditions. The controller must authenticate the planner's returned P before implementation. Check identities against the actual checkout and the selected runner lane. Distinguish the base-to-planning change from the planning-to-candidate implementation change. Preserve unrelated dirty work. The consumer execution map identifies who captures and publishes C and when. An implementor may commit and push only explicitly authorized candidate work to that branch for review, but not to `main`; a push is not approval or acceptance.

For a draft capsule, check that each active acceptance criterion has a stable ID, independently expected result, and authored verification route, including negative or boundary cases where needed. Check fixed compatibility contracts, non-goals, reviewer packet requirements, and the recovery boundary. The consumer's own capsule schema remains controlling. A checked planning box is not candidate-bound evidence.

For a planner handoff, distinguish controlling issue requirements from background evidence and unverified hypotheses. The controller supplies the current issue/request identity, authenticated base, sourced behavior and constraints, consumer format, proposed scope, supported profiles, checks, and unresolved decisions. The planner returns a trace from every controlling requirement to an AC or fixed contract with expected result and evidence route, or marks it unresolved or properly deferred. The controller checks that trace against the original objective and actual planning diff before accepting P. A source lead does not grant an edit path, and a mechanical planning PASS does not settle a missing product decision.

Before dispatch, the controller records a compact gate table mapping every active criterion and required review standard to its exact check, execution place, retained evidence, and environment assumptions. Compare the capsule's owned paths and profiles with the commands and expected changed files. Rehearse costly or sandbox-sensitive commands in the intended evidence environment when safe, without treating the rehearsal as candidate qualification. Run new tests and applicable cross-platform fixtures before freezing the candidate; recheck the table against actual P-to-C files and the planned reviewer packet before remote qualification. Use the consumer's existing planning record rather than inventing another capsule format.

Trace every controlling requirement through the draft. Mark it covered, unresolved, or explicitly deferred by the owning authority. RI exclusions, unsupported source, and a revised capsule cannot silently erase it. Include relevant manifests, workflows, feature flags, and unsupported files in this accounting even when RI maps no callable there.

Before qualification and reviewer dispatch, check actual packet completeness: required profiles and commands, source identity, raw results/logs, skipped test IDs/reasons and applicable capability probes. Compare every full-diff edit with its authorized path and stated inventory purpose; an allowed file cannot carry unrelated work. Match frozen command/arguments, working directory, configuration, interpreter, profiles, isolation policy, relevant environment and source with the successful rehearsal; relevant changes require fresh protected rehearsal. Use mechanical checks where supported. For unchanged C with missing evidence, preserve the incomplete record and use only consumer-authorized supplementation or rerun routes; never fabricate historical results or silently rewrite sealed evidence. Missing evidence alone does not require a new code revision, but remains unresolved until authenticated proof and required fresh review are complete.

Report gaps for the current phase only. Refresh context within existing read grants; use policy-permitted bounded infrastructure retries; apply in-scope corrections only with remaining allowance and required parent lineage. Missing authority/prerequisites block dependent work. Changed scope, base, required proof or authority requires `STOP_REPLAN` and the smallest needed controller decision. Do not repair authority by widening paths, choosing a different base, substituting an old candidate, or silently dropping a required check. A mechanical PASS authenticates only what that check actually covers; the controller still resolves semantic scope and acceptance.

Return a compact preflight record: verified capsule and repository identities, permitted next action, applicable lane and checks, unresolved gaps, and the exact source of each decision. Do not launch implementation, qualify, publish, accept, or merge unless the active request and consumer workflow authorize that step.

Before accepting P when RI is mandatory, require the consumer runtime probe and representative comparison with the selected interpreter; runtime/harness changes invalidate dependent readiness. Supply the accepted review/report/export format and fixture validation record. Rehearsal must show selected test collection, fixtures, skips/deselection and actual hosted workflow/source identities, rather than only successful command launch.

When a protected service requires committed C, record that constraint and use permitted preparation before freeze, then mandatory protected qualification on C. Do not invent a pre-freeze run or substitute ordinary host evidence.
