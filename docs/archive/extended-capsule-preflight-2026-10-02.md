> Historical extended instructions, retained for audit. Not the default workflow.
> Use [the current controller workflow](../capsule-controller-workflow.md).

---
name: capsule-preflight
description: Authenticate an active task capsule and its exact repository state before capsule implementation, qualification, or review. Use when a consumer project runs a capsule workflow; do not apply to ordinary standalone RI work.
---

# Capsule preflight

Under an authorized task using the adopted workflow, routine coordination,
failure diagnosis, role clarification, handoff validation and bounded preparation
are included in standing authority. Do not request another human approval for
those actions solely because a gate failed. Continue only consumer-authorized
corrections/stages within scope, permissions, destinations and remaining limits;
a STOP still blocks dependent execution. Keep source edits with the authorized
implementor. Ask only for the specific uncovered decision, not permission to
investigate. See [controller authority](extended-controller-workflow-2026-10-02.md#standing-authority-for-routine-controller-work).

For candidate evidence checks, read [the adapter contract](../skill-templates/capsule-preflight/references/evidence-contract.md)
and use [evidence_preflight.py](../skill-templates/capsule-preflight/scripts/evidence_preflight.py) when the consumer
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

Before implementation authorization, require an impact inventory covering implementation, callers, tests, fixtures, workflow assertions, documentation and profile rules, with edit/inspect disposition and reasons per actual path. Search for tests asserting changed structures and profile sets. A fresh read-only scope challenger is required by consumer policy, cross-seam workflow/profile/infra changes or meaningful scope uncertainty. Record the trigger or omission rationale. Resolve findings before READY/P; material inventory/base/scope changes require a fresh challenge of the final identity. Unresolved dependencies block dispatch. Authorization references the completed inventory and any required final challenge. Candidate attachment references applicable pre-freeze rehearsal or the recorded committed-C-only constraint, followed by mandatory exact-C protected qualification, including exact source, command, collection settings, isolation policy and result. A host-only pass is insufficient. Consumer tooling enforces these records where supported; this skill cannot supply missing authority.

Treat the consumer repository's current capsule contract and accepted runner as execution authority. Read the active capsule and relevant local workflow instructions; never infer authority from this skill, RI output, issue prose, or an old transcript.

Select the consumer's current phase first. Intake needs objective/authority/base and planning permissions, not future P/C. Planning acceptance needs draft/P, requirement trace and scope/evidence feasibility. Implementation needs ready P and an authorized worktree. Qualification needs C and frozen commands; review needs C/Q and complete accepted report inputs. Integration needs matching approvals/current refs and retrievable retained source/evidence. Resume verifies existing stage, revisions, jobs, findings, remaining allowance and next action against current Git/runner state. Adopt changed rules at a safe boundary and revalidate affected permissions/proof/interfaces; chat reset cannot reset allowances.

Before the requested capsule step, establish the applicable current repository and issue state, capsule revision, planner-created dedicated branch under controller direction and recorded remote, exact base and planning identities, active overlay, allowed reads and edits, acceptance criteria, required checks, supported host, and stop conditions. The controller must authenticate the planner's returned P before implementation. Check identities against the actual checkout and the selected runner lane. Distinguish the base-to-planning change from the planning-to-candidate implementation change. Preserve unrelated dirty work. The consumer execution map identifies who captures and publishes C and when. An implementor may commit and push only explicitly authorized candidate work to that branch for review, but not to `main`; a push is not approval or acceptance.

For a draft capsule, check that each active acceptance criterion has a stable ID, independently expected result, and authored verification route, including negative or boundary cases where needed. Check fixed compatibility contracts, non-goals, reviewer packet requirements, and the recovery boundary. The consumer's own capsule schema remains controlling. A checked planning box is not candidate-bound evidence.

For a planner handoff, distinguish controlling issue requirements from background evidence and unverified hypotheses. The controller supplies the current issue/request identity, authenticated base, sourced behavior and constraints, consumer format, proposed scope, supported profiles, checks, and unresolved decisions. The planner returns a trace from every controlling requirement to an AC or fixed contract with expected result and evidence route, or marks it unresolved or properly deferred. The controller checks that trace against the original objective and actual planning diff before accepting P. A source lead does not grant an edit path, and a mechanical planning PASS does not settle a missing product decision.

Before dispatch, the controller records a compact gate table mapping every active criterion and required review standard to its exact check, execution place, retained evidence, and environment assumptions. Compare the capsule's owned paths and profiles with the commands and expected changed files. Rehearse costly or sandbox-sensitive commands in the intended evidence environment when safe, without treating the rehearsal as candidate qualification. Run new tests and applicable cross-platform fixtures before freeze where the accepted lane supports that; otherwise record its committed-C prerequisite and require exact-C proof; recheck the table against actual P-to-C files and the planned reviewer packet before remote qualification. Use the consumer's existing planning record rather than inventing another capsule format.

Trace every controlling requirement through the draft. Mark it covered, unresolved, or explicitly deferred by the owning authority. RI exclusions, unsupported source, and a revised capsule cannot silently erase it. Include relevant manifests, workflows, feature flags, and unsupported files in this accounting even when RI maps no callable there.

Before qualification and reviewer dispatch, check actual packet completeness: required profiles and commands, source identity, raw results/logs, skipped test IDs/reasons and applicable capability probes. Compare every full-diff edit with its authorized path and stated inventory purpose; an allowed file cannot carry unrelated work. For checks with pre-freeze rehearsal, match frozen invocation and mode/byte source identities against the successful rehearsal; relevant changes require fresh rehearsal. Committed-C-only lanes instead require their recorded preparation constraint and exact-C protected qualification. Use mechanical checks where supported. For unchanged C with missing evidence, preserve the incomplete record and use only consumer-authorized supplementation or rerun routes; never fabricate historical results or silently rewrite sealed evidence. Missing evidence alone does not require a new code revision, but remains unresolved until authenticated proof and required fresh review are complete.

Report gaps for the current phase only. Refresh context within existing read grants; use policy-permitted bounded infrastructure retries; apply in-scope corrections only with remaining allowance and required parent lineage. Missing authority/prerequisites block dependent work. Changed scope, base, required proof or authority requires `STOP_REPLAN` and the smallest needed controller decision. Do not repair authority by widening paths, choosing a different base, substituting an old candidate, or silently dropping a required check. A mechanical PASS authenticates only what that check actually covers; the controller still resolves semantic scope and acceptance.

Emit `STOP_REPLAN` only as a last resort after bounded authorized checks establish
the relevant stop trigger and existing permitted recovery cannot resolve it.
Evidence not yet inspected is not failed authentication. Check the supplied
identity records and report actual observations and uncertainty; do not run all
checks merely to justify a stop. Confirmed violations and explicit owner stops
still halt immediately. Opening progress uses the supported nonterminal channel,
not a terminal `stop_replan` placeholder. An accidentally emitted stop remains
stopped. See [stop-trigger checks](extended-controller-workflow-2026-10-02.md#establish-the-trigger-before-emitting-stop_replan).

A suspected replan blocker holds execution, not all capsule interaction. Within
existing read authority/budget, do one bounded read-only sweep of related capsule
identity, scope, runtime/command and delivery prerequisites, returning supported
blockers together plus unknown/unchecked items. Use nonterminal progress while
diagnosing; finalize STOP only afterward where the host permits. If already
terminal, use diagnostic-only follow-up before replacement planning without
resuming implementation. No edits, tests, qualification or permission widening
are granted. See [consolidated diagnosis](extended-controller-workflow-2026-10-02.md#hold-execution-then-consolidate-diagnostic-findings).

After a stopping result, diagnose before revising the capsule: authenticate the
retained agent/gate/wrapper reason and evidence, and separate observed failure
from hypothesis. If no reason is supplied, record `reason unknown` and use only
authorized bounded read-only diagnostics or an explanation request. Do not guess
a capsule change, resume the stopped attempt, or reset its allowance. Record the
smallest evidence-supported recovery in the existing checkpoint. Follow
[stop diagnosis](extended-controller-workflow-2026-10-02.md#diagnose-a-stop-before-replanning).

The authorized task includes a bounded diagnostic-only explanation request to
the stopping implementor through its existing authorized channel, without another
human approval. The original agent may explain its stop despite the normal
fresh-context rule; it cannot resume implementation. Limit the request to retained
facts and existing read scope, retain its answer separately and check it against
the stopped record. No edits, tests, reruns, new exports or replacement authority
are granted by this explanation request. See
[standing diagnostic authority](extended-controller-workflow-2026-10-02.md#standing-authority-for-a-stop-explanation).

Return a compact preflight record: verified capsule and repository identities, permitted next action, applicable lane and checks, unresolved gaps, and the exact source of each decision. Do not launch implementation, qualify, publish, accept, or merge unless the active request and consumer workflow authorize that step.

Before accepting P when RI is mandatory, require the consumer runtime probe and representative comparison with the selected interpreter; runtime/harness changes invalidate dependent readiness. Supply the accepted review/report/export format and fixture validation record. Where rehearsal is applicable, it must show selected test collection, fixtures and skips/deselection, rather than only successful command launch. Committed-C-only hosted workflow/source identities are verified during exact-C qualification.

When a protected service requires committed C, record that constraint and use permitted preparation before freeze, then mandatory protected qualification on C. Do not invent a pre-freeze run or substitute ordinary host evidence.

Require final observed invocation/source identity for every check, including
committed-C-only lanes. Where exported, check mandatory node collection and
execution under the actual selecting gate, not green totals. Use the
[effectiveness guidance](historical-workflow-effectiveness-2026-10-02.md) for validate-before-P
ordering and staged obligations; existing consumer contracts govern adoption.
