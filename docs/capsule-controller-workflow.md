# Capsule controller workflow with RI

This is a reusable handoff pattern, not an RI execution policy. The consumer
repository's current capsule contract, runner, issue state, and supported-host
rules control the work. RI supplies bounded source evidence. The example roles
are Orchestrator/Controller, Capsule Planner, Independent Scope Challenger,
Implementor, and Independent Reviewer. Model/effort assignments belong in the
consumer's qualified deployment configuration (see new-project setup). The RI
historical probe verified planner, implementor and candidate reviewer roles and native completion in Codex; it did not
qualify a Work-host controller or enforced read-only review. Confirm model
availability and repository access in the actual consuming host. Local
Codex skills do not automatically appear in Work chats.

## Why this guide exists

The controller needs one place to orient a task before dispatch: what outcome
the user authorized, what the capsule permits, which source facts RI can add,
what each actor must return, and which evidence is required to finish. The
goal is to complete routine implementation and correction loops without asking
the user to restate the same objective. The capsule still comes from the
consumer project's contract. This guide does not create a second RI capsule
schema, a permission grant, or a shortcut around qualification and review.
Every requirement in the controlling objective must remain satisfied,
unresolved, or explicitly deferred by its proper authority. An RI exclusion,
unsupported file, bounded packet, failed check, or capsule revision cannot
silently remove a requirement. Incomplete RI evidence blocks a claim of
complete structural comparison; it does not by itself cancel otherwise
authorized work. Use another approved evidence route or replan while keeping
the obligation visible.

For each capsule, the controller authenticates the issue and base, then asks a
capsule-planner subagent to draft the capsule and impact inventory on its
planning branch. The first return supplies the draft and inventory identities.
After any required challenge and revision, the planner returns final READY/P,
branch, base, capsule path, scope, checks, and status. The controller independently verifies those against Git and the
consumer's planning route before dispatching an implementor subagent. The
consumer-authorized actor captures candidate C and publishes it at the point
permitted by the resolved execution map. An implementor may commit and push
only when that consumer explicitly authorizes it. The controller verifies the reported C and
changed paths, qualifies exact C, and sends a fresh read-only reviewer subagent
the complete packet. Use forward pushes so earlier candidate SHAs remain
reachable; preserve failed candidate evidence separately. A push makes a
candidate available; it does not qualify, approve, or integrate it. The
consumer's guarded acceptance path controls integration into `main`.

```text
User objective
    |
    v
Controller (one continuing parent)
  authenticate issue + current repository state
    |
    v
Capsule Planner subagent -> draft capsule + impact inventory; planning branch
    | native completion: draft/inventory identities, base, gaps, status
    v
Scope challenge when required -> planner revises findings -> rechallenge final inventory
    | material inventory change invalidates previous challenge
    v
Finalize READY capsule/P -> controller validates and publishes permitted P ref
    | mismatch --> repair planning before dispatch
    v
Authorize implementation paths
    |
    v
Preflight exact capsule/base/planning overlay/scope/host
    | mismatch --> STOP_REPLAN --> controller repairs capsule --> preflight
    v
RI evidence, if useful: locate -> inspect -> bind to exact Git blob
    |
    v
Implementor subagent -> authorized edits + tests
    | native completion: DONE/gap, changes, paths, checks, status
    v
Controller -> verify returned worktree changes/scope
    | require C here only if implementor is the authorized capture actor
    v
Consumer-authorized actor -> capture C; publish at the permitted stage
    |
    v
Controller authenticates C + lane-required ref state, then qualifies exact C
    | external gate: native terminal callback or one verified queue watcher
    | failure --> preserve C/evidence --> correction or revised capsule --+
    v                                                                |
Independent Reviewer subagent (fresh read-only context)         |
  exact capsule + P/C + full diff + qualification evidence              |
    | native completion: per-criterion verdict + exact metadata           |
    | FAIL or missing evidence --> preserve C/findings -----------------+
    v PASS for every active criterion and applicable standard
Controller reconciles and uses consumer's guarded approval,
publication, acceptance, and closeout commands
  verify integration and retained evidence; delete completed capsule branch

The parent waits on each native subagent completion; it does not repeatedly
poll unchanged status. Verify each returned identity and result before the
next delegation. A long external qualification needs its own verified terminal
delivery route. Use the capsule-queue watcher when it lacks native completion
and the exact controller destination can receive its notification; the watcher
is unnecessary for native subagent handoffs.
```

## Prepare the issue-to-planner handoff

The controller must give the planner enough authenticated context to write a
capsule without guessing intent or scope. An issue can be concise; it need not
be rewritten into a second capsule. Before dispatch, the controller reads the
current issue and relevant updates, the latest user direction, and the
consumer's issue/capsule contract. Resolve conflicting or stale text through
that consumer's authority rules. Treat issue comments, logs, source comments,
and RI matches as evidence or proposals unless the consumer grants them
decision authority.

Prepare one compact handoff with these facts and their sources:

| Include | What the planner needs |
| --- | --- |
| Objective and authority | Issue/request identity and revision, observable desired outcome, controlling requirements, priority of any later correction, and who may decide unresolved product or scope questions. |
| Current behavior and evidence | Reproduction or failing observation where applicable, independently expected behavior, boundary and negative cases, relevant screenshots/logs/PRD excerpts, and uncertainties marked as such. Do not turn a hypothesis into an acceptance criterion. |
| Repository state | Repository/remote, published base commit, local worktree status, active capsule or competing branch, consumer capsule format, planning command, and the dedicated branch rule. |
| Scope and contracts | Likely owners and callers as source leads, proposed edit/read paths, fixed external behavior, non-goals, supported platforms/profiles, and any protected interfaces. Verify actual paths before granting them in the capsule. |
| Proof and handoffs | Candidate-independent expected results; required tests, fixtures, hosts and review standards; evidence sandbox assumptions; reviewer packet and guarded acceptance route; stop and recovery conditions. |
| RI context, if useful | Exact RI version/source identity, selected source excerpts and coverage gaps, each tied to the intended Git blob. RI locations help the planner navigate but do not authorize edits or prove behavior. |

If an issue lacks a detail that the controller can establish from the current
repository, accepted project documents, or an authorized investigation, add
that sourced fact to the handoff. Amend the issue only when the consumer's
process requires the issue itself to carry the clarification. If a material
choice remains unresolved, record the question and stop the dependent planning
step rather than inventing an answer. Do not require the user to rewrite a
clear issue just to satisfy a template.

The planner returns a capsule plus a short trace: each controlling requirement
maps to an AC or named fixed contract, its independently expected result, an
authorized path/profile, a check and evidence route, or an explicit unresolved
or properly deferred disposition. The planner distinguishes issue facts from
inferences and lists source/context gaps. Before accepting P, the controller
compares that trace with the original request and issue, inspects the actual
base..P planning diff, and verifies the proposed paths, profiles and frozen
commands against the checkout. Mechanical planning PASS does not resolve a
missing requirement or an invented grant.

## Author a decision-complete capsule

### Discover and challenge scope before authorization

Before granting implementation paths, the planner prepares an impact inventory
for each planned behavior change. Inspect implementation, callers, tests,
fixtures, workflow assertions, documentation, and profile rules. Record actual
paths, whether each requires editing or inspection only, the reason, and its
associated requirement. Search explicitly for tests that assert changed workflow
structures, checkout counts, profile sets, or command layouts. Existing test
expectations are scope inputs; a source-only inventory is insufficient. RI can
help locate source and expose coverage gaps, but the inventory also needs direct
search and inspection of files outside RI's structural mapping.

The inventory is always required. Use a fresh read-only scope challenger when
the consumer requires one, the change crosses module/workflow/profile/infra
seams, or the controller finds meaningful scope uncertainty. Record the trigger
or rationale for omitting that conditional lane. The challenger checks objective,
exact base, draft/inventory identities, source/tests and consumer rules.
Resolve findings before finalizing READY/P or granting implementation paths.
Material changes to inventory/scope/base invalidate the earlier challenge:
challenge the final inventory identity again before freezing P. An early planning
branch or draft commit may support recovery; it is not authoritative READY/P.
The planner owns draft revision after controller-returned findings and supplies the final READY/P return only after any required rechallenge. Record the final inventory and applicable challenge result in existing planning
records. Unresolved dependencies block dispatch; candidate review remains fresh.

For new subprocess tests, rehearse invocation, collection, fixtures, isolation,
permissions and output in the intended protected lane before freeze where that
lane supports pre-freeze execution. If the service requires a committed C,
record this constraint and use the permitted preparation/fixture route; run
mandatory protected qualification on exact C after freeze. An ordinary host
pass cannot substitute for that final gate. Capture source modes and bytes,
command/settings, skips and probes. Rehearsal never replaces exact-C qualification.

The consumer's authorization must reference the completed inventory and any required final scope
challenge. Candidate attachment references applicable protected rehearsal
records or the recorded committed-C-only constraint and mandatory exact-C proof and reconcile actual P..C paths with the inventory. Where the consumer
supports mechanical gates, missing, stale, or mismatched records must block
advancement. RI documents this evidence requirement; consumer tooling owns its
enforcement. Do not invent an RI authorization service or another receipt store.

Use the consumer's existing fields and checks. The controller can work through
this checklist while drafting; each checked item must cite the source or exact
state that supports it. Do not copy the whole list into a capsule whose existing
fields already cover it. A checkmark is a planning aid, not acceptance evidence.

- [ ] **Intent and authority:** State the observable user outcome, controlling
  issue or request, active capsule identity/revision, and the accepted runner
  and review lane. Resolve conflicting or stale issue text before dispatch.
- [ ] **Exact source state:** Authenticate the base; create a dedicated capsule
  branch and record its remote/ref, planning object/overlay P and SHA, and
  expected clean or allowed-dirty state. Keep the base-to-P planning change
  separate from the P-to-C implementation change. State which ref the
  authorized capture/publication actor may publish and how the controller verifies C.
- [ ] **Bounded access:** List owned edit paths and permitted reads, plus
  explicit non-goals and protected interfaces. Include the supported host,
  runtime, feature/target settings, and allowed context expansion route.
- [ ] **Fixed contracts:** Name external behavior, error/persistence formats,
  compatibility promises, and adjacent callers that must remain correct. RI
  can locate these; the controller must inspect and author them.
- [ ] **Acceptance criteria:** Give each required behavior a stable ID, an
  independently expected observation, and a way to check it. Include negative
  and boundary cases where they distinguish a correct implementation from a
  plausible but wrong one. Do not use another production counter as the sole
  oracle for a source name, kind, range, or delta.
- [ ] **Qualification:** Name required commands, real runtime or consumer
  tests, fixtures, host, and the evidence each produces. State whether a check
  is mandatory or conditional. An unavailable mandatory check remains open.
- [ ] **Pre-dispatch gate:** Map every active acceptance criterion and required
  review standard to its exact check or inspection, execution place, expected
  evidence, and environment assumption. Reconcile owned paths and required
  profiles with the files and commands the capsule actually permits.
- [ ] **Review and completion:** Define the exact candidate and evidence
  packet for a fresh reviewer, the required per-criterion and standards
  dispositions, and the consumer's guarded approval/acceptance route.
- [ ] **Recovery and stop conditions:** Distinguish an in-scope correction,
  bounded infrastructure retry, replacement capsule, and decision requiring
  the user. Specify where failed candidates and raw evidence are retained.
- [ ] **Preflight:** Run the consumer's draft/planning validation against the
  exact state. `READY` means the work order is executable; it does not mean
  implementation, qualification, or review has passed.
- [ ] **Whole-objective coverage:** Account for relevant configuration,
  manifests, workflows, feature flags, and unsupported source outside RI's
  selected mapping. Mark each original requirement satisfied, unresolved, or
  explicitly deferred by the owning authority; no scan limit closes it.

Write criteria as independently checkable outcomes, not directions to edit a
particular line. For example, an illustrative source-mapping capsule might say:

| ID | Required result | Independent check | Completion evidence |
| --- | --- | --- | --- |
| AC-1 | A named declaration maps to the complete expected source slice, including its attached syntax | Compare output with an authored fixture containing the literal expected name, kind, and raw bytes | Exact candidate test result and inspected slice |
| AC-2 | A malformed or unsupported input stays incomplete or unsupported | Run the authored negative fixture and inspect status and failures | Raw status and failure record; no forced success |
| AC-3 | A real caller still works under the required runtime settings | Run the named consumer or runtime test on the supported host | Command, host/settings, exit and relevant output bound to C |

These rows illustrate the shape; copy neither the IDs nor requirements into an
unrelated capsule. A criterion is complete only when its expected observation
matches candidate-bound evidence and the independent reviewer accepts that
evidence. A passing test count or checked planning box alone is insufficient.

For each *real* criterion, the capsule should give the implementor a small
checkable work item in the consumer's existing body or AC fields. This is a
drafting example, not a new file format:

```text
- [ ] AC-<id>: <observable result and exact boundary/negative behavior>
      Expected: <independently authored value, slice, name/kind, or outcome>
      Check: <test or inspection and required host/configuration>
      Evidence: <candidate-bound result location to fill after execution>
```

The planner drafts `Expected` and `Check`; the controller verifies and owns
them before implementation. The implementor may check off implementation
work, but only candidate-bound check results and the
fresh reviewer can satisfy the AC. If a requirement cannot be made observable,
resolve it before dispatch rather than leaving the implementor to guess.

## Check the execution plan before dispatch

Record a short gate table with the planning packet, using the consumer's
existing notes or capsule fields. Include one row per active AC and each
review standard requiring separate evidence. Do not add a second capsule
schema or count a row as passing evidence.

| Requirement | Exact check or inspection and expected result | Where it runs and evidence retained | Environment assumption |
| --- | --- | --- | --- |
| AC or required standard ID | Authored test, source inspection, or reviewer judgment | Local sandbox, supported native host, or hosted check; output bound to C | Profile, tool version, network, filesystem, or Git setting needed |

Before implementor dispatch, compare this table with the capsule's owned
paths, permitted reads, required profiles, changed-file expectations, and
reviewer packet. Resolve any check that needs an unowned file, unavailable
host, or missing evidence route through the consumer's planning authority.
Rehearsal must establish actual selected-test collection, profiles, fixtures,
output capture and relevant negative/boundary cases; record skips and deselection.
An expected baseline regression is distinct from an unusable environment. A zero-test
profile cannot satisfy a required test. For hosted proof, freeze expected event,
workflow/jobs and whether candidate-head, merge-result or both sources are required.
Verify actual checked-out/tested source; absent, cancelled or inapplicable jobs
remain unresolved. Rehearse costly or sandbox-sensitive frozen commands in the intended evidence
environment when safe: verify invocation, fixtures, permissions, and output
capture without treating a planning-state result as qualification of C. Run
applicable cross-platform fixtures before freeze where the lane supports it, and rerun them on C when
the capsule requires candidate-bound proof. New tests should run before C is frozen where the accepted lane permits it;
services requiring committed C need mandatory exact-C qualification after freeze. Keep machine-global settings out of an isolated evidence run unless
the consumer explicitly requires them; record any unavoidable assumption.
Before paying for remote qualification, recheck the table against the actual
P..C changed files and the planned review packet's per-standard evidence. A dry run cannot
waive a mandatory check or a substantive reviewer finding.

## Hand-off packets and done condition

### Check evidence completeness, scope drift, and rehearsal identity

Use the [scope-review skill template](skill-templates/capsule-scope-review/SKILL.md)
for the independent inventory challenge and the preflight template's
[evidence checker](skill-templates/capsule-preflight/references/evidence-contract.md)
for deterministic comparisons. The consumer exports trusted expectations and
actual observations from its existing records, authenticates their provenance,
and connects the result to its own gates. RI supplies portable source templates;
copying them does not automatically enforce a consumer policy.

Before qualification and again before reviewer dispatch, compare the required
evidence inventory with the actual packet. Check each required command/profile,
source identity, expected result, raw exit status and log, and every skip's test
ID, reason and capability-probe result where applicable. Verify retained record
identities or digests through the consumer's evidence route. A passing count or
summary cannot stand in for missing detail. Use mechanical completeness checks
where the consumer supports them; an unexplained omission blocks advancement.

Compare every P..C edit with both the authorized paths and the impact inventory's
stated purpose. Inspect the full diff, including documentation and generated
content. An allowed path does not authorize unrelated behavior or prose. Resolve
any new dependency or purpose outside the capsule through scope revalidation
before attachment, qualification, or review.

Compare the frozen execution with its rehearsal: exact command/arguments,
working directory, configuration, interpreter/toolchain, profiles, isolation
policy, relevant environment settings, and source identity. A relevant change
invalidates the earlier rehearsal and requires a fresh protected rehearsal
before freeze where supported, or the recorded preparation route plus exact-C
protected qualification in a committed-C-only lane. A rehearsal on planning or preserved candidate bytes checks
invocation only; new test bytes and the final candidate require their own
applicable evidence. Record any consumer-approved equivalence rather than
assuming two environments behave the same.

Keep handoffs short but exact. The controller sends the implementor the frozen
capsule, dedicated branch and remote, exact P, selected authenticated
source/contract excerpts, permitted repository read route, and how to report a
scope collision. The implementor returns authorized changes, changed paths,
test results and unresolved questions. The consumer-authorized actor captures C
and publishes only at the stage allowed by the execution map; include C/ref
metadata when that action is part of the implementor lane. The controller verifies
C against actual source and any required published ref and adds qualification Q(C), host/settings, raw logs,
coverage gaps, and the complete changed-file inventory for the fresh reviewer.
The reviewer returns a finding or PASS/FAIL for every active criterion and
applicable standard, all tied to C. The controller records disposition and uses
the consumer's guarded closeout path. No model role or skill name substitutes
for an artifact, command result, or required approval.

## Delegate through native subagents

Keep one controller as the continuing parent. Delegate these roles in order;
each subagent returns through the host's native completion channel:

| Subagent | Input from controller | Required return |
| --- | --- | --- |
| Capsule planner | Authenticated objective, base, consumer format and branch policy; returned scope findings | First return: draft/inventory identities, branch/base and gaps. After revisions and any fresh challenge: final READY/P, capsule/scope/check identities and status. |
| Independent scope challenger | Objective, exact base, proposed impact inventory, draft capsule and consumer rules | Read-only findings and scope disposition before implementation authorization |
| Implementor | Verified P, exact capsule, branch/ref, permitted source context | DONE or precise gap, authorized changes, C SHA when permitted, changed paths, checks and worktree state |
| Fresh independent reviewer | Exact P and C, full diff, capsule, qualification logs and standards | Per-AC and standards verdict, exact C and branch metadata, findings or uncertainty |

The controller checks the planner's P against the actual branch and capsule
before launching the implementor. After DONE, the controller verifies changes and directs authorized capture; it then authenticates C and lane-required
ref state, P..C changed paths, and required checks before launching the reviewer.
After review, it checks the verdict against C and the ref/publication conditions
required at integration. An immutable promoted C need not advance execution HEAD. A completion message is a trigger to
inspect evidence, never evidence by itself. Use a supported bounded native
wait for a running child; do not spend repeated controller turns polling.

Use a fresh reviewer context with read-only access that is enforced by the
consumer's review lane. A role label or request to avoid edits is insufficient
if the agent still has write tools. If the consumer's independence policy does
not admit a subagent reviewer, resolve that lane before adoption; do not mark
review complete from the implementor's self-report. Confirm each subagent's
host, repository access, branch, model and effort before dispatch. The small
RI probe demonstrated native completion in Codex; a consumer still has to
qualify its own host and protected review lane. See OpenAI's
[subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Resolve the consumer interfaces before planning

Use the consumer's accepted command guide and parser revision to record an
execution map in its existing planning record: who creates planning refs and P,
who edits, who captures C, when publication is permitted, qualification entry
point/runtime, review lane/report validator, export contents/supplements, and
approval/acceptance/closeout commands. The branch workflow is supported wherever
these actors are authorized; role names alone do not grant Git mutation.

When RI is mandatory, run the consumer's actual runtime compatibility probe and
one representative comparison with the selected RI interpreter before accepting
P. Record producer/consumer contract versions and runtime identity. Recheck when
runtime or harness changes; retain a qualified older runtime or authorize a
separate upgrade if incompatible. Optional RI does not become mandatory here.

Validate representative review-report and export fixtures before adoption and
whenever those interfaces change. Record required fields, source dispositions,
receipt imports and supplementary artifacts. Fixture identities are specimens,
never future production C/Q evidence. Give reviewers the accepted report format
and validator requirements as part of their handoff.

## Phase selection and resume

Use the consumer's existing stage/attempt state. Require only artifacts that
exist at that stage; a missing future P or C is not an intake failure.

| Phase | Required inputs and permitted next step |
| --- | --- |
| Intake | Current objective/authority, base, planning permissions and resolved execution map; dispatch planning without requiring P/C. |
| Planning acceptance | Actual draft/P, full objective trace, inventory and any required final scope challenge, runtime compatibility and feasible evidence routes; resolve findings before implementation. |
| Implementation | Ready P, authorized worktree/read/edit scope and candidate-capture owner; implement through the permitted transport. |
| Qualification | Exact C, frozen commands, profiles and runner; collect candidate-bound proof. |
| Review | Exact C/Q, full diff, complete packet and accepted report schema; request fresh enforced read-only review. |
| Integration/closeout | Matching approval/Q/R, current refs and accepted route; verify retained source, history, issue and checkout reconciliation before cleanup. |
| Resume/rule adoption | Authenticate retained state against live Git/runner state and re-enter its actual phase. |

A fresh or resumed controller reads authoritative instructions and an existing
retained planning/evidence checkpoint containing objective/issue, consumer
contract/command/runtime/skill revisions, stage, capsule revision, relevant B/P/C,
refs/worktree state, active job/attempt and exact completion destination,
Q/R/approval locations, unresolved findings, remaining correction allowance and
next authorized action. Verify those facts against current source and runner
state. Chat history cannot supply missing authority; a reset cannot replenish
an exhausted budget or justify restarting a job to recreate notification.

Adopt revised rules at a safe boundary. Preserve or stop active jobs through
existing authority, compare old/new permissions, checks, command semantics and
report formats, and record what supersedes what. Revalidate affected readiness
or evidence for substantive changes. Pure editorial corrections do not force
reruns; classify the change using actual contracts rather than a label.

## Controller gates from intake through closeout

The controller owns every transition. Check actual repository and runner
state rather than accepting a subagent's status label. Record a compact result
in the consumer's existing planning or evidence record; this table creates no
new capsule format. A failed or missing item stops that handoff and follows the
recovery rules below.

| When | Controller checks before advancing | Next action |
| --- | --- | --- |
| **Before planner dispatch** | Authenticate the current issue/request and every requirement; inspect local and published base refs, worktree status, active capsules, branch policy, runner and review lane. Resolve stale or conflicting authority and the consumer execution/review/export map. Give the planner the sourced [issue-to-planner handoff](#prepare-the-issue-to-planner-handoff), exact base, capsule format, branch rules, planning paths, and stop conditions. | Dispatch the planner only with a bounded planning task. |
| **After planner draft return** | Verify base, draft capsule and inventory identities, planning branch and allowed worktree state. Reconcile every objective requirement, proposed paths/profiles/checks and runtime/evidence feasibility. Treat draft commits as recovery state, not final P. | Resolve gaps and dispatch scope challenge when triggered. |
| **Before final READY/P and implementation authorization** | Complete the impact inventory and any required independent scope challenge (see [scope discovery](#discover-and-challenge-scope-before-authorization)), including tests asserting changed workflow structures and profiles. Resolve dependencies and bind the inventory and challenge records to the proposed capsule and exact base. Validate deterministic inputs, launch wrapper, actual packet-size/report route and applicable rehearsal before declaring READY/P; any published partial preparation stays explicitly non-READY. | Recheck materially changed inventories in the conditional challenge lane; finalize READY/P only when gaps are resolved. |
| **After final P return** | Verify capsule/P/base, full planning diff and permitted branch/ref, final inventory/challenge identity and mandatory runtime compatibility. Run draft/published planning checks through the consumer route. | Publish validated P where permitted, then grant implementation paths and dispatch. |
| **Before implementor dispatch** | Complete the [pre-dispatch gate table](#check-the-execution-plan-before-dispatch), including every AC and required review standard. Verify authorization references the completed inventory and any required final scope challenge. Rehearse costly or sandbox-sensitive commands where safe. Confirm exact P still heads the branch, the implementation checkout is ready, the selected model/effort and host have required access, and the handoff contains the frozen capsule, permitted source context, checks, and STOP_REPLAN route. | Delegate implementation bound to P and the dedicated branch. |
| **After implementor return** | Require DONE or a precise failure, authorized worktree changes, changed paths, checks and gaps. Verify actual diff/status against P and scope; require C only if the implementor was the authorized capture actor. | Preserve failed work/evidence or send verified changes through the authorized candidate-capture route. |
| **After candidate capture** | Require exact C, applicable local/remote ref state and current head. Verify base..P and full P..C diffs, changed-file inventory, scope, profiles and checks. Publication occurs only when permitted by the execution map; a remote C is not universally required before review. | Authenticate captured C and prepare exact-C qualification. |
| **Before exact-C qualification** | Reconcile the gate table with every changed file, required profile, and standard. Confirm each command's path, host, inputs and evidence location; rehearse costly or sandbox-sensitive invocation where safe. Ensure C and its source material are stable and that no required test or fixture is missing. | Run the consumer's mandatory local/native and hosted gates on exact C; preserve raw results. |
| **At external-gate dispatch** | Select one completion route before starting the job: the runner's reliable terminal callback, or a bounded watcher using `capsule-queue` with the exact verified Codex controller destination. For a Work controller, use only a tested bridge to that exact chat or its supported bounded wait. Bind the job to C, required profiles, deadline, and retained status/log paths. | Launch the gate once and wait for its terminal event; no periodic controller-turn status checks or duplicate native run. |
| **After qualification, before reviewer dispatch** | Verify Q(C) names the exact candidate, host/profile, commands, exit status, logs, coverage gaps, hosted-check SHA and mandatory node observations under the actual selecting gate/stage. A missing or failed mandatory gate remains unresolved. Confirm the accepted report template/validator and complete export/supplement requirements. Assemble the capsule/intent, B/P/C, full diff and changed-file inventory, expected AC observations, Q(C), and per-standard evidence. Authenticate immutable C and lane-required local/remote refs (head == C only if required there), and give a fresh reviewer enforced read-only access. | Dispatch one exact-C independent review only with a complete, authenticated packet. |
| **After reviewer return** | Authenticate the verdict's branch and C against current Git state. Require a finding or evidence-backed disposition for every active AC and applicable standard; reconcile each finding with the original objective, qualification, and changed-file inventory. Treat absent dispositions, unsupported evidence, or a moved C as unresolved. | Preserve failed C/findings and return an in-scope correction or replan; a complete PASS proceeds to guarded integration checks. |
| **Before guarded integration** | Recheck the base and candidate identity plus ref/publication conditions required by the consumer at integration; ensure required Q(C), fresh independent R(C), all active criteria and standards, approvals, and consumer-specific publication conditions bind the same C. Requalify and re-review any changed C or execution-relevant base. | Use only the consumer's authorized approval, publication, and acceptance route. |
| **After integration and review closeout** | Verify the intended target contains the reviewed candidate or approved merge result, record integration identity, confirm evidence is retained and review/issue status is reconciled. Verify the closeout predicate below, including retrievable source, issue/primary checkout reconciliation and no active capsule, worktree or follow-up needing the branch. | Close the issue when its objective is satisfied; delete the completed capsule branch and unused local copies through the consumer route. Retain unmerged or still-used branches. |
| **On failure, interruption, or changed scope at any stage** | Preserve the exact P/C, command outputs, findings, and current ref state. Classify an in-scope correction, bounded infrastructure retry, replacement capsule, or decision outside current authority. Never infer success from a missing callback or reuse proof for changed source. | Resume the authorized stage with fresh checks, or STOP_REPLAN and bring only the concrete unresolved decision to the user. |

The gate before reviewer dispatch checks that the packet is complete; it cannot
prejudge the review. A reviewer finding remains a finding even if the planned
gate table and qualification passed. No subagent result grants a new edit path,
waives a mandatory host, or approves integration.

## Role detail for the controller gates

The gate table above is the advance/stop sequence. These notes describe what
each role does while the controller carries it out.

Use the phase table and controller gate table above as the procedural sequence.
Use [preflight](skill-templates/capsule-preflight/SKILL.md) for applicable envelope
checks, [scope review](skill-templates/capsule-scope-review/SKILL.md) for planning
challenge, [RI handoff](skill-templates/ri-evidence-handoff/SKILL.md) for exact
blob/page evidence, and [independent review](skill-templates/capsule-independent-review/SKILL.md)
for fresh candidate judgment. The [setup stage map](new-project-setup.md) assigns
these resources to roles; the consumer execution map assigns commands and Git
mutations. Full P..C review remains mandatory even with an empty RI delta.

The controller owns continuation for the authorized objective. A test failure,
review finding, or recoverable interruption should not by itself require the
user to say "continue" or request another capsule. The controller should do
the authorized repair, checks, and handoff, and surface only an actual decision
or final result. This does not grant a wider task or bypass a required host,
reviewer, or approval boundary.

Native completion returns each child result to the parent controller. The
controller waits for that result once and verifies its evidence. A long external
qualification gate must have a verified terminal route selected at dispatch.
Use the [capsule-queue skill](skill-templates/capsule-queue/SKILL.md) when the
gate lacks a native callback and the exact Codex controller can receive the
queued result. `codex queue` does not address an arbitrary ChatGPT Work chat;
use a tested Work bridge or a supported bounded wait there. Put any necessary
status polling inside one watcher with backoff and a deadline, not in repeated
controller turns. The watcher saves one terminal outcome for success, failure,
timeout, or lost delivery. On receipt, the controller checks its status, logs,
candidate SHA and required profiles before deciding Q(C). A queued message
cannot supply a planner, candidate, qualification PASS, or reviewer verdict.
Do not restart a completed native run merely to regain notification.

A supported bounded wait must actually wait for an event or block in the
runner; a deadline around repeated model-driven status requests is still
controller polling. Record the selected mechanism, destination, job/C identity,
deadline and retained evidence paths before launch. If the host has no verified
wake-up route, report that limitation once and use its supported blocking wait;
do not claim that installing the queue skill creates a Work callback.

While a gate runs, the controller may finish bounded, authorized preparation
that does not depend on its outcome or alter C, such as assembling the review
packet or preparing installation probes. After that work is complete, wait for
the terminal event. Do not query CI jobs, reread unchanged status files, or
announce "still running" to fill the interval. Report a new failure, timeout,
delivery problem, requested status, or decision-relevant change. A different
profile becoming green need not wake the controller when acceptance still
requires the same final aggregate result. Tool-level resumptions needed to
receive a blocking command's output are transport handling; they must not
become repeated CI inspection or new controller decisions.

## Recovery without repeated user turns

### Validate closeout before returning its draft

When closeout needs a history record, the planner uses the consumer's current
schema-aware builder where available and runs its history validator immediately
after drafting, before returning or committing the record. Missing repository
metadata must fail here. Validate again on exact closeout C before qualification
and fresh review; retain the validator result with the closeout packet.

For required installed-workflow probes, authenticate the installed workflow/base,
separate authorized probe candidates and provider checks. Require the selected
test to execute and fail in the negative case, with no unrelated test failures,
and to execute and pass in the positive control. Bind history metadata, recovery
commit/capsule hash and both probe proofs to the retained records. The
[preflight closeout adapter](skill-templates/capsule-preflight/references/evidence-contract.md#closeout-and-installed-workflow-probes)
checks these exported expectations and observations. Consumer tooling must
authenticate exports and enforce missing-record failures; a skill alone cannot.
The fresh reviewer accounts for the original outcomes and applicable installed/terminal
obligations before guarded finalization. An explicitly adopted consumer contract
may retain authenticated unchanged implementation judgments under the
[scoped carry-forward rules](workflow-effectiveness.md#stage-obligations-and-bounded-reuse);
otherwise its existing original-outcome review requirement still applies. Installation success does not close an issue whose live
probes or history gates remain pending.

### Resume or replan from preserved evidence

Put these rules in each consumer's capsule template or controller instructions,
using that consumer's existing fields rather than adding an RI policy format:

| Event | Controller action |
| --- | --- |
| Transient download, runner, or connection failure | Preserve the attempt and raw error; retry the same gate only when its own policy permits a bounded retry. Never call an absent result PASS. |
| Missing evidence for unchanged C, with no demonstrated code defect | Preserve the failed/incomplete record. If the consumer permits supplemental evidence, authenticate C and collect only the missing detail through its existing evidence route; bind the supplement to the original run and source as required. Never reconstruct an unrecorded historical observation or change a sealed record silently. Re-submit the complete packet for fresh review when required. An evidence omission alone does not mandate a new implementation revision or repeat native qualification; if the consumer requires a new run or forbids supplementation, follow that rule. |
| Failing authored test or reviewer finding within scope | Preserve the failed C SHA and evidence. Check the consumer's remaining correction allowance and finalized parent failure. Return the finding through its permitted transport; capture a new candidate with required lineage/parent binding and rerun applicable qualification/review. An exhausted allowance blocks continuation; this loop grants no unlimited retries. |
| Missing source context or RI coverage gap | Use the capsule's allowed read/expansion lane or ask a narrower question. Keep the incomplete result; do not infer absent behavior. |
| Fix requires paths or behavior outside the capsule | `STOP_REPLAN`. The controller may draft a replacement capsule for the same authorized objective, then authenticate its new scope/base and run the consumer's planning checks before dispatch. |
| Changed objective, unavailable mandatory prerequisite, or action requiring new authorization | Bring the concrete decision to the user with the evidence and available options. |

Retain failed candidates and review packets. A changed candidate or
execution-relevant base invalidates earlier candidate-bound proof; do not
transfer an old PASS. Avoid creating an automatic series of replacement
capsules with guessed authority: one authenticated revision is preferable to
retries that hide the underlying mismatch.

## Closeout predicate before ref deletion

Require all of: verified consumer-specific integrated result; complete history
and active-capsule reconciliation; issue/review closure when the objective is
satisfied; primary checkout synchronization when safe; and retrievable retained
source plus evidence. Test retrieval of reviewed and failed candidates from an
accepted retained ref or verified source/patch/bundle route. A recorded SHA alone
is not retention, and squash/rebase integration need not preserve its ancestry.
Keep refs/worktrees still needed by evidence or follow-up work. Delete a completed
branch only after those conditions pass; preserve a blocked cleanup explicitly.

## Put the skills where each role can use them

The [skill templates](skill-templates/README.md) are portable source files, not
an RI runtime dependency. Install only the skills useful to that project's
roles. The consumer's `AGENTS.md` and capsule remain authoritative if a skill
example disagrees with them. A local Codex installation does not register a
skill in ChatGPT Work. Verify Work availability separately before relying on
automatic activation. Follow the
[new-project setup guide](new-project-setup.md) to install the appropriate
skills for each role and test the handoff before adoption.

## Evidence feasibility and trial handoffs

Apply the [review evidence feasibility and handoff gate](review-evidence.md#feasibility-and-handoff-gate) during existing planning and reviewer-intake gates. Measure actual evidence before final P and test the accepted report/export route before reviewer allocation. The [trial lessons](review-evidence.md#trial-lessons-and-consumer-boundaries) identify consumer integration checks; they do not authorize consumer upgrades or add approval rounds.

## Effectiveness and adopted consumer contracts

Use the [lightweight corrections](workflow-effectiveness.md) at the existing
planning, qualification, review and closeout gates. They specify selecting-gate
observations, validate-before-readiness ordering, staged obligations and
consumer-authorized evidence/review reuse. Existing consumer rules remain
controlling until adopted; no extra mandatory review stage is introduced.
