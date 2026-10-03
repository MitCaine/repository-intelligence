> Historical extended instructions, retained for audit. Not the default workflow.
> Use [the current controller workflow](../capsule-controller-workflow.md).

# Capsule controller workflow with RI

The [lightweight workflow](../simple-controller-workflow.md) is the default for
new or explicitly replaced RI adoption. This extended reference describes
additional consumer-selected controls; its packet, protected transport and
qualification procedures are not universal RI requirements. Existing bindings
change only through authorized adoption. Do not require repairing an obsolete
extended route before an owner-authorized lightweight replacement.

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

Before product planning, resolve adoption/setup conflicts and bind the selected
map, complete skill resources, compatible runtime and supported review route.
Setup repair is a separate assignment; do not dispatch product planning while
that repair remains unresolved. Representative setup proof is not future C/Q/R
evidence. Keep candidate-specific rehearsal and qualification at their later stages.

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
    | mismatch --> STOP_REPLAN --> diagnose --> authorized recovery --> preflight
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

Failure arrows in this overview route through
[the failure transition map](#trace-failure-transitions-not-only-the-successful-sequence);
they do not imply every failure needs new planning or implementation. Fresh
contexts are the default, with the bounded [capacity exception](#release-completed-agent-capacity).
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

Use the [scope-review skill template](../skill-templates/capsule-scope-review/SKILL.md)
for the independent inventory challenge and the preflight template's
[evidence checker](../skill-templates/capsule-preflight/references/evidence-contract.md)
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

Adopt the [shared procedure and local map](extended-project-setup-2026-10-02.md#adopt-one-shared-procedure)
at an immutable pin. This also defines instruction delivery, active stop handling
and compaction/resume bindings; local executable authority remains consumer-owned.

Use the consumer's accepted command guide and parser revision to record an
execution map in its existing planning record: who creates planning refs and P,
who edits, who captures C, when publication is permitted, qualification entry
point/runtime, review lane/report validator, export contents/supplements, and
approval/acceptance/closeout commands. The branch workflow is supported wherever
these actors are authorized; role names alone do not grant Git mutation.

### Standing authority for routine controller work

A user-authorized task carried out under this adopted workflow includes routine
coordination, diagnosis and preparation needed to complete it. Do not request a
new human approval merely because a gate failed, an agent omitted information,
or the controller must communicate with a role it dispatched. Apply the existing
task authority and consumer map; a failure does not revoke unrelated authorized
work or create a new authority grant.

Within existing scope, permissions, evidence destinations and finite allowances,
the controller may without another approval:

- Read and authenticate retained source, logs, results, runtime identities and
  actual operation state; ask assigned roles for factual clarification.
- Validate handoffs, prepare bounded recovery proposals and correct controller-
  owned preparation records through the permitted route.
- Delegate authorized in-scope corrections to the appropriate role and advance
  through already authorized checks, review, publication and integration stages.
- Preserve failures, reconcile uncertain dispatch/integration, perform permitted
  cancellation/cleanup and recover notification delivery without rerunning work.
- Apply the documented capacity fallback and diagnostic-only stop-explanation
  exception, keeping reviewer independence and one working subagent at a time.

Keep implementation with its authorized actor; preparation authority is not a
license for the controller to patch product or repair source. A STOP still halts
that attempt and its dependent work. Diagnosis and preservation can continue,
but execution recovery requires the existing correction/replacement authority,
distinct identity where required, and remaining allowance. Standing authority
never resets limits, transfers an old verdict or makes missing proof pass.

Ask the user only for a concrete decision outside that authority: changed scope
or objective, additional permissions, exhausted retry/correction budget, a new
unapproved disclosure destination/payload, or an action reserved for explicit
owner approval. Identify the exact boundary, evidence, available options and the
smallest approval needed. Do not turn ordinary diagnosis into an approval request
or invent a restriction not present in the adopted contract. New user-owned chats
still follow the host's explicit creation-authorization requirement.

Record standing authority once in the existing execution map/checkpoint and
preserve it across compaction. Where a consumer rule actually contradicts this
policy, resolve that adoption conflict explicitly; do not silently claim the
shared doc overrides executable consumer policy. Host permissions and automatic
approval review remain binding: retain any rejection, use an already authorized
supported alternative where available, and report a specific unresolved boundary.

Map diagnostic execution and evidence disclosure separately before dispatch.
Record destination visibility (including public CI logs/artifacts), the bounded
payload, and the existing authority permitting its release. Apply standing
authorization where it covers that payload and destination; do not add routine
approval rounds. A private-diagnostic restriction still applies when a diagnostic
uses a public repository. Short artifact retention does not make disclosure private.
If automatic approval review rejects release, preserve the rejection and halt that
action. Use an already supported private route if available; do not bypass the
rejection through an indirect upload. Report the exact uncovered payload and
destination when specific human authorization is necessary. Unaffected local
preparation can continue within its existing authority.

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

### One subagent at a time

The controller runs one subagent assignment at a time. The primary sequence is:

1. A fresh capsule creator returns the draft and final planning artifacts.
2. After controller validation of final P, a fresh implementor returns its work.
3. After controller capture and required qualification of C, a fresh independent
   reviewer returns its verdict.

The controller consumes the terminal result and verifies the required handoff
before dispatching the next role. Do not run concurrent discovery assistants,
setup assistants, implementors, or Standards/Spec reviewer subagents, and do not
allow a role to create a parallel agent tree. One reviewer covers both Standards
and Spec. Any separately required scope challenge is a serial assignment after
its complete draft inputs exist; it cannot overlap the capsule creator or waive
an existing consumer gate. Corrections use fresh assignments sequentially,
retaining implementation artifacts rather than reusing the agent conversation.
Use verified native completion or capsule-queue, then suspend once bounded
controller preparation is finished. Do not poll or invent work to avoid waiting.

### Release completed agent capacity

One working subagent at a time does not guarantee a free host slot: limits can
count open agent threads, including completed conversations. After each terminal
return, retain and authenticate the required artifacts, record the controller's
disposition and next handoff, then close the completed agent using the host's
supported agent-close operation, **where available**, before creating the next fresh role. Keep
source, branches, receipts and failure evidence; closing a conversation does not
authorize deleting those artifacts. Do not close an agent still executing or
awaiting a required terminal return, and do not treat interruption alone as closure.

At setup, establish whether the host supports closing completed agents and
releasing capacity. If dispatch reports an agent/thread limit, inspect the host's
agent inventory once, close only completed agents whose handoffs are retained,
and retry creation only after capacity release is confirmed. This is dispatch
recovery, not permission to rerun a completed command or reset attempt allowances.
If the host exposes no close operation or still rejects creation after supported
cleanup, retain the verified checkpoint and record the capacity limitation.
**Last-resort agent reuse is authorized by this workflow** when fresh creation is
blocked and capacity cannot be released through the available host operations.
Do not repeatedly attempt unsupported UI cleanup or spawning. Fresh contexts
remain the normal route; convenience or a desire to retain earlier reasoning is
not a reason to reuse. A separate controller task still needs explicit user
authorization; creating one is not a required intermediate step before reuse.

For last-resort reuse, select one idle agent whose previous assignment has ended,
retain its original result, and give it a complete new handoff with the current
phase, exact source identities, scope, instructions, pending gates and stop state.
Record the reused agent and capacity reason in the existing checkpoint. Require
it to reauthenticate those inputs; prior conversation, verdicts and approvals do
not satisfy the new assignment. Keep one assignment running at a time and
preserve attempt allowances and historical STOP records. Reuse does not clear a
stopped attempt or authorize dependent work.

Keep review independent: an agent that authored or implemented the candidate or
its repairs cannot review that candidate. Reuse for review is permitted only for
an otherwise uninvolved agent, with enforced read-only access and a new
candidate-bound verdict; record that its conversation is reused rather than
claiming a fresh context. If no independent agent is available, preserve the
checkpoint and report that review remains blocked. This exception concerns
context freshness only, not consumer permissions, qualification or acceptance.

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

When intake exposes a setup conflict, preserve the current product state and
resolve only the separately authorized setup assignment. Do not install or change
the selected workflow/skill/helper/runtime bindings inside an active product
attempt. A required change returns through the consumer's recovery/adoption route;
it is not an implicit restart. Specification advice may inform a draft, but cannot
stand in for scope challenge of the complete capsule, impact inventory and proof
routes. Record premature assignments as deviations, retaining useful drafts as
inputs rather than counting their results as gates passed in order.

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
| **Before initial implementor dispatch** | Complete the [pre-dispatch gate table](#check-the-execution-plan-before-dispatch), including every AC and required review standard. Verify authorization references the completed inventory and any required final scope challenge. Rehearse costly or sandbox-sensitive commands where safe. Confirm exact P still heads the branch, the implementation checkout is ready, the selected model/effort and host have required access, and the handoff contains the frozen capsule, permitted source context, checks, and STOP_REPLAN route. | Delegate implementation bound to P and the dedicated branch. |
| **Before correction implementor dispatch** | Authenticate the recovery source/head and parent, retained failure/findings, required finalization, current scope/authority and remaining allowance. Do not require the branch to head original P when the accepted correction lane starts from failed C. | Dispatch only the bounded authorized correction; retain prior source and evidence. |
| **After implementor return** | Require DONE or a precise failure, authorized worktree changes, changed paths, checks and gaps. Verify actual diff/status against P and scope; require C only if the implementor was the authorized capture actor. | Preserve failed work/evidence or send verified changes through the authorized candidate-capture route. |
| **After candidate capture** | Require exact C, applicable local/remote ref state and current head. Verify base..P and full P..C diffs, changed-file inventory, scope, profiles and checks. Publication occurs only when permitted by the execution map; a remote C is not universally required before review. | Authenticate captured C and prepare exact-C qualification. |
| **Before exact-C qualification** | Reconcile the gate table with every changed file, required profile, and standard. Confirm each command's path, host, inputs and evidence location; rehearse costly or sandbox-sensitive invocation where safe. Ensure C and its source material are stable and that no required test or fixture is missing. | Run the consumer's mandatory local/native and hosted gates on exact C; preserve raw results. |
| **At external-gate dispatch** | Select one completion route before starting the job: the runner's reliable terminal callback, or a bounded watcher using `capsule-queue` with the exact verified Codex controller destination. For a Work controller, use only a tested bridge to that exact chat or its supported bounded wait. Bind the job to C, required profiles, deadline, and retained status/log paths. | Launch the gate once and wait for its terminal event; no periodic controller-turn status checks or duplicate native run. |
| **After qualification, before reviewer dispatch** | Verify Q(C) names the exact candidate, host/profile, commands, exit status, logs, coverage gaps, hosted-check SHA and mandatory node observations under the actual selecting gate/stage. A missing or failed mandatory gate remains unresolved. Confirm the accepted report template/validator and complete export/supplement requirements. Assemble the capsule/intent, B/P/C, full diff and changed-file inventory, expected AC observations, Q(C), and per-standard evidence. Authenticate immutable C and lane-required local/remote refs (head == C only if required there), and give a fresh reviewer enforced read-only access. | Dispatch one exact-C independent review only with a complete, authenticated packet. |
| **After reviewer return** | Authenticate the verdict's branch and C against current Git state. Require a finding or evidence-backed disposition for every active AC and applicable standard; reconcile each finding with the original objective, qualification, and changed-file inventory. Treat absent dispositions, unsupported evidence, or a moved C as unresolved. | Preserve failed C/findings and return an in-scope correction or replan; a complete PASS proceeds to guarded integration checks. |
| **Before guarded integration** | Recheck the base and candidate identity plus ref/publication conditions required by the consumer at integration; ensure required Q(C), fresh independent R(C), all active criteria and standards, approvals, and consumer-specific publication conditions bind the same C. Requalify and re-review any changed C or execution-relevant base. | Use only the consumer's authorized approval, publication, and acceptance route. |
| **After integration and review closeout** | Verify the intended target contains the reviewed candidate or approved merge result, record integration identity, confirm evidence is retained and review/issue status is reconciled. Verify the closeout predicate below, including retrievable source, issue/primary checkout reconciliation and no active capsule, worktree or follow-up needing the branch. | Close the issue when its objective is satisfied; delete the completed capsule branch and unused local copies through the consumer route. Retain unmerged or still-used branches. |
| **On failure, interruption, or changed scope at any stage** | Preserve the exact P/C, command outputs, findings, and current ref state. [Diagnose a stop before replanning](#diagnose-a-stop-before-replanning); if no reason is supported, record reason unknown and obtain bounded authorized diagnostics. Classify an in-scope correction, bounded infrastructure retry, replacement capsule, or decision outside current authority. Never infer success from a missing callback or reuse proof for changed source. | Resume the authorized stage with fresh checks, or STOP_REPLAN and bring only the concrete unresolved decision to the user. |

The gate before reviewer dispatch checks that the packet is complete; it cannot
prejudge the review. A reviewer finding remains a finding even if the planned
gate table and qualification passed. No subagent result grants a new edit path,
waives a mandatory host, or approves integration.

## Role detail for the controller gates

The gate table above is the advance/stop sequence. These notes describe what
each role does while the controller carries it out.

Use the phase table and controller gate table above as the procedural sequence.
Use [preflight](../skill-templates/capsule-preflight/SKILL.md) for applicable envelope
checks, [scope review](../skill-templates/capsule-scope-review/SKILL.md) for planning
challenge, [RI handoff](../skill-templates/ri-evidence-handoff/SKILL.md) for exact
blob/page evidence, and [independent review](../skill-templates/capsule-independent-review/SKILL.md)
for fresh candidate judgment. The [setup stage map](../new-project-setup.md) assigns
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
Use the [capsule-queue skill](../skill-templates/capsule-queue/SKILL.md) when the
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
[preflight closeout adapter](../skill-templates/capsule-preflight/references/evidence-contract.md#closeout-and-installed-workflow-probes)
checks these exported expectations and observations. Consumer tooling must
authenticate exports and enforce missing-record failures; a skill alone cannot.
The fresh reviewer accounts for the original outcomes and applicable installed/terminal
obligations before guarded finalization. An explicitly adopted consumer contract
may retain authenticated unchanged implementation judgments under the
[scoped carry-forward rules](../workflow-effectiveness.md#stage-obligations-and-bounded-reuse);
otherwise its existing original-outcome review requirement still applies. Installation success does not close an issue whose live
probes or history gates remain pending.

### Trace failure transitions, not only the successful sequence

Use this routing map when checking the workflow end to end. It summarizes the
existing recovery rules; it adds no mandatory artifact or review stage. Apply it
at the current phase, including setup and planning, without demanding future P,
C, qualification or review records that cannot yet exist.

```text
Troublesome state / stopping result
  -> halt affected work; retain identity, output and actual execution state
  -> is the reason supported by retained evidence?
       no -> bounded authorized diagnosis -> still unknown? remain blocked
       yes
        -> did dispatch/integration possibly occur despite a missing response?
             yes -> reconcile existing operation; do not duplicate it
        -> select the smallest authorized recovery:
             agent capacity -> supported cleanup or last-resort independent reuse
             notification lost -> retrieve/redeliver result; do not rerun work
             preparation/transport -> correct affected setup within authority
             missing proof, same C -> permitted supplement or necessary gate rerun
             in-scope source defect -> implementor correction -> new C -> checks
             changed scope/base/authority -> replacement planning and validation
             no authority/allowance/independent reviewer -> checkpoint and block
        -> reauthenticate affected inputs; invalidate only proof required by
           the consumer's adopted contract; enter the permitted recovery stage
```

A stopped attempt never returns to running. Recovery proceeds through the
consumer's permitted correction/replacement identity and retained lineage;
otherwise it remains blocked. A failure is not automatic authority for a new
launch. Confirm applicable allowances and actual dispatch state before acting.
Do not funnel an environment, notification or missing-evidence problem into a
capsule rewrite merely because the status label says `STOP_REPLAN`.

| Walkthrough branch | Required destination under the existing rules |
| --- | --- |
| Agent emits STOP at intake with no reason; no edits/tests | Keep the attempt stopped, record reason unknown, diagnose retained intake/trace/wrapper. No guessed scope revision. |
| Fresh role cannot spawn; idle agents cannot be closed | Reauthenticate a last-resort reused role under the capacity exception; an involved implementor cannot become its candidate reviewer. With no independent option, review remains blocked. |
| Job completed but its nudge/report delivery failed | Recover the existing result or use permitted delivery recovery; no second execution just to obtain a notification. |
| Transport timed out or response was lost | Verify shutdown and reconcile actual startup/completion and consumed allowance before a permitted retry; an unknown response does not prove no launch occurred. |
| Review finds missing logs with unchanged source | Preserve failed review; use consumer-permitted authenticated supplementation and required review. Do not invent historical logs or automatically rewrite source. |
| Review finds an in-scope implementation defect | Give the evidence-backed correction to the implementor; retain prior work, capture new C, rerun affected gates under current authority. |
| Required correction exceeds scope or budget | Diagnose the concrete missing authority, preserve the attempt, and follow replacement planning or request the specific decision. Do not reset limits by renaming the attempt. |
| Integration response is lost | Inspect actual integrated refs/receipt for the same operation before retrying; never merge twice or declare closeout from uncertainty. |
| Integration passed but retention/branch cleanup failed | Keep integration recorded as complete and closeout incomplete; fix only the pending closeout step. Retain needed refs until retrieval is verified. |

Launch-wrapper validation also has two moments: validate deterministic inputs and
route feasibility before READY; if the generated wrapper requires final P,
validate that exact generated wrapper after P and before implementation dispatch.
A published P alone grants no implementation readiness. Preserve any partial
publication as such rather than dispatching to discover a setup defect.

### Establish the trigger before emitting STOP_REPLAN

`STOP_REPLAN` is the last resort when bounded permitted checks establish a
blocking condition and no existing authorized route can resolve it within this
attempt. It is not the default response to an unfamiliar handoff or evidence not
yet inspected. **Not checked is not failed.** Inspect the relevant authentication
records and actual source/runner state before claiming that authentication failed.
Check the suspected blocker and related capsule prerequisites through one bounded
read-only pass; do not run every test, expensive qualification or speculative
investigation before stopping.

Before emitting the stopping outcome, the implementor or other role must:

1. Identify the capsule/consumer stop condition it believes applies.
2. Inspect its supplied evidence and perform bounded checks within granted read
   and execution authority. If a necessary observation is unavailable, describe
   it as unavailable rather than inventing failure.
3. Use an already permitted clarification, read expansion or in-scope correction
   when it resolves the issue without changing scope, authority or frozen proof.
4. If the blocker remains, hold implementation and run the bounded diagnostic
   sweep below before finalizing the stopping outcome where the host permits it.
   Return all supported blockers together, evidence locators, checks made,
   unchecked prerequisites, uncertainty and why permitted routes cannot resolve them.

A confirmed scope/authority violation, explicit owner stop, or consumer-required
immediate halt must stop execution immediately; do not continue edits or run
implementation/test work to exhaust alternatives. Read-only diagnostic interaction
can continue within existing read authority unless the owner or host prohibits it. When safe diagnosis cannot establish required authority,
hold dependent work and report the unresolved prerequisite through the accepted
interface. Last resort never means proceeding without authentication or bypassing
a mandatory guard. Failure of implementation or a test within scope should use
its existing failure/correction route unless the adopted contract requires replan.

Opening progress is **nonterminal**: state that intake/authentication is underway
using the runner's supported progress channel. Do not populate a terminal result
or emit the reserved `stop_replan` status as an opening acknowledgement, placeholder
or prediction. If the interface lacks a nonterminal status, keep the structured
outcome for completion rather than inventing a status. Authenticate this distinction
when preparing the wrapper. An actual stopping event still halts the attempt even
if emitted accidentally; preserve it and diagnose under the rules below rather
than silently treating it as harmless progress or continuing the same attempt.

### Hold execution, then consolidate diagnostic findings

Finding a replan blocker must not end all interaction with the capsule at the
first observation. Immediately hold edits, tests, qualification, publication and
integration; keep bounded read-only diagnosis available. Before final terminal
closure, where the host supports it, perform **one diagnostic sweep** of the
capsule and existing handoff to find related blockers that would otherwise fail
the replacement one at a time. Use the supported nonterminal progress channel
to describe the execution hold; do not emit a terminal `stop_replan` to mean
"diagnosis in progress" or invent a new status unsupported by the runner.

The sweep checks relevant existing records: authentication/base/P and source
identities, scope/path availability, required runtime/profile/command bindings,
and evidence/reviewer delivery prerequisites observable at the current phase.
Inspect repeated instances of the failed assumption elsewhere in the capsule.
Respect the current read scope and existing diagnostic time/resource budget;
no new mandatory test suite, review role or report format is required. It does
not authorize edits, test runs, permission probing, new execution, broader reads
or private-data export. Do not manufacture findings for future artifacts that
cannot exist yet, or keep searching indefinitely for every conceivable defect.

Return one consolidated diagnostic result in the existing handoff/checkpoint:
confirmed blockers with evidence, unresolved observations clearly marked unknown,
and checks completed or unavailable. The controller uses that set to prepare one
coherent recovery instead of guessing successive capsule revisions. Revalidate
all affected prerequisites after the recovery; the diagnostic sweep is not a
promise that no further defect exists.

If the wrapper has already made the stop terminal or killed the agent, preserve
that terminal state. Use the standing diagnostic-only follow-up or retained-evidence
route to perform the same bounded sweep **before replacement planning**; never
resume the stopped implementation to finish diagnosis. If read authority is itself
invalid, the host denies inspection, or the owner stopped all work, preserve what
is available and report the diagnostic limit. Do not widen permissions to finish
the sweep. Neither an execution hold nor a diagnostic response clears an existing
STOP or authorizes a replacement launch.

### Diagnose a stop before replanning

A `STOP_REPLAN` halts the affected attempt and dependent work. Preserve its exact
P/C or current planning identity, terminal result, raw output, public turn/events,
wrapper error and cleanup outcome. A stopping status emitted at intake is not
proof of a capsule defect. Confirm whether the host made that status terminal;
if execution continues despite a stopping status, halt it through the permitted
route and retain the resulting terminal evidence.

Before changing a capsule or dispatching replacement work, the controller must:

- Read the retained reason and supporting evidence from the agent, wrapper and
  required gate; distinguish the observed failure from a proposed explanation.
- Identify whether the blocker concerns capsule scope/authority, source behavior,
  environment/transport, or an agent/wrapper error. Do not classify by guess.
- If no supported reason exists, record **reason unknown**. Use a bounded,
  authorized read-only diagnostic to inspect the preserved attempt or request an
  explanation. An explanation request is not permission to resume the stopped
  implementation, edit source, rerun a costly gate or create replacement work.
- Complete the [bounded diagnostic sweep](#hold-execution-then-consolidate-diagnostic-findings)
  of related capsule prerequisites before replacement planning; retain all findings
  together instead of revising for each discovered blocker separately.
- Select the smallest evidence-supported recovery under existing authority and
  remaining allowances. Record what must change and why in the existing
  checkpoint before returning a correction or replacement handoff.

#### Standing authority for a stop explanation

The controller may request the stopping implementor's factual explanation
**without further human permission** as part of the authorized task's diagnosis.
It may read retained results and send a bounded diagnostic-only follow-up through
the existing authorized agent channel. This is an explicit exception to requiring
a fresh context for every assignment: the original agent may explain its own
stopped attempt, but may not resume implementation. If that agent is unavailable,
use the existing read-only diagnostic route on retained evidence.

The request names the stopped attempt and asks for the concrete trigger, evidence
locator, whether any edits/tests or dispatch occurred, related prerequisite
blockers from the bounded sweep, and any uncertainty.
Allow only existing authorized reads; prohibit edits, tests, command re-execution,
replacement dispatch and new evidence export. Retain the response separately as
a diagnostic explanation, not a revised terminal result, reviewer verdict or
recovery approval. The controller checks it against retained facts before choosing
recovery. Use a bounded completion wait and report reason unknown if no usable
answer returns; do not repeatedly ask or poll for an explanation.

No new approval is required solely because the implementation is stopped or the
reason was omitted. New permissions, destinations, sensitive disclosure or work
outside the existing authority still follow their own rules. This authorization
does not override a consumer's explicitly adopted prohibition; resolve such a
conflict during adoption rather than silently treating the diagnosis as execution.

Role handoffs require a concrete stop reason and evidence locator when available;
if unavailable, the role must state that explicitly. Do not invent a reason to
fill the result. The controller must not rewrite the capsule merely because the
agent emitted `stop_replan`, or assume a parser/transport failure is a planning
failure. If diagnosis remains inconclusive, keep dependent work blocked and
report the missing fact. A later diagnostic success never clears the original
STOP or resets a consumed allowance. Apply the recovery routes below only after
this diagnosis; no extra mandatory report or review stage is introduced.

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

### No-change completion

When authenticated inspection demonstrates all requested behavior already exists,
return a no-change disposition with source identity and evidence for each active
criterion. The controller and required independent reviewer check that evidence;
then use the consumer's supported no-change issue closeout. Do not invent an edit,
commit or integration. If the consumer requires a specific finding-only or no-change
route, map it explicitly; missing evidence cannot be called already satisfied.

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

The [skill templates](../skill-templates/README.md) are portable source files, not
an RI runtime dependency. Install only the skills useful to that project's
roles. The consumer's `AGENTS.md` and capsule remain authoritative if a skill
example disagrees with them. A local Codex installation does not register a
skill in ChatGPT Work. Verify Work availability separately before relying on
automatic activation. Follow the
[new-project setup guide](../new-project-setup.md) to install the appropriate
skills for each role and test the handoff before adoption.

## Evidence feasibility and trial handoffs

Apply the [review evidence feasibility and handoff gate](../review-evidence.md#feasibility-and-handoff-gate) during existing planning and reviewer-intake gates. Measure actual evidence before final P and test the accepted report/export route before reviewer allocation. The [trial lessons](../review-evidence.md#trial-lessons-and-consumer-boundaries) identify consumer integration checks; they do not authorize consumer upgrades or add approval rounds.

## Effectiveness and adopted consumer contracts

Use the [lightweight corrections](../workflow-effectiveness.md) at the existing
planning, qualification, review and closeout gates. They specify selecting-gate
observations, validate-before-readiness ordering, staged obligations and
consumer-authorized evidence/review reuse. Existing consumer rules remain
controlling until adopted; no extra mandatory review stage is introduced.
