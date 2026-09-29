# Capsule controller workflow with RI

This is a reusable handoff pattern, not an RI execution policy. The consumer
repository's current capsule contract, runner, issue state, and supported-host
rules control the work. RI supplies bounded source evidence. The example roles
are Orchestrator/Controller, Capsule Planner, Implementor, and Independent
Reviewer. The target model assignment is a Sol Light controller and planner,
a Luna Max implementor, and a fresh Sol Light reviewer. The RI probe verified
the three child roles and native completion in Codex; it did not qualify a
Work-host controller. Confirm model availability and repository access in the
actual consumer environment. Local
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
capsule-planner subagent to create the dedicated branch and decision-complete
capsule. The planner returns branch, base, P, capsule path, scope, checks, and
status. The controller independently verifies those against Git and the
consumer's planning route before dispatching an implementor subagent. The
implementor commits and pushes candidate C to that branch where the consumer
requires a remote review ref. The controller verifies the reported C and
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
Capsule Planner subagent -> create branch + decision-complete capsule
    | native completion: branch, base, P, capsule, scope, checks, status
    v
Controller -> independently verify P, validate planning, publish branch
    | mismatch --> STOP_REPLAN --> repair planning state --> verify again
    |
    v
Preflight exact capsule/base/planning overlay/scope/host
    | mismatch --> STOP_REPLAN --> controller repairs capsule --> preflight
    v
RI evidence, if useful: locate -> inspect -> bind to exact Git blob
    |
    v
Implementor subagent -> commit and push C to capsule branch + tests
    | native completion: DONE/STOP_REPLAN, C, paths, checks, status
    |
    v
Controller verifies C metadata + branch head, then qualifies exact C
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
next delegation. The capsule-queue watcher is unnecessary for these native
subagent handoffs.
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
  implementor may push and how the controller will verify its head against C.
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
Rehearse costly or sandbox-sensitive frozen commands in the intended evidence
environment when safe: verify invocation, fixtures, permissions, and output
capture without treating a planning-state result as qualification of C. Run
applicable cross-platform fixtures before C is frozen, and rerun them on C when
the capsule requires candidate-bound proof. New tests should run before C is
frozen. Keep machine-global settings out of an isolated evidence run unless
the consumer explicitly requires them; record any unavoidable assumption.
Before paying for remote qualification, recheck the table against the actual
P..C changed files and the planned review packet's per-standard evidence. A dry run cannot
waive a mandatory check or a substantive reviewer finding.

## Hand-off packets and done condition

Keep handoffs short but exact. The controller sends the implementor the frozen
capsule, dedicated branch and remote, exact P, selected authenticated
source/contract excerpts, permitted repository read route, and how to report a
scope collision. The implementor commits and pushes to that branch, then
returns the pushed C SHA, branch/ref, changed paths, complete diff location,
test commands/results, and unresolved questions. The controller verifies that
the remote ref contains C and adds qualification Q(C), host/settings, raw logs,
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
| Capsule planner, Sol Light | Authenticated objective, base, consumer format and branch policy | Branch/ref, base, capsule path, P SHA, owned paths, ACs, checks, planning status |
| Implementor, Luna Max | Verified P, exact capsule, branch/ref, permitted source context | DONE or STOP_REPLAN, committed C SHA, changed paths, check results, clean/status state |
| Fresh independent reviewer, Sol Light | Exact P and C, full diff, capsule, qualification logs and standards | Per-AC and standards verdict, exact C and branch metadata, findings or uncertainty |

The controller checks the planner's P against the actual branch and capsule
before launching the implementor. After DONE, it checks C against the branch
head, P..C changed paths, and required checks before launching the reviewer.
After review, it checks the returned verdict against the same C and rechecks
the branch head before integration. A completion message is a trigger to
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

## Controller gates from intake through closeout

The controller owns every transition. Check actual repository and runner
state rather than accepting a subagent's status label. Record a compact result
in the consumer's existing planning or evidence record; this table creates no
new capsule format. A failed or missing item stops that handoff and follows the
recovery rules below.

| When | Controller checks before advancing | Next action |
| --- | --- | --- |
| **Before planner dispatch** | Authenticate the current issue/request and every requirement; inspect local and published base refs, worktree status, active capsules, branch policy, runner and review lane. Resolve stale or conflicting authority. Give the planner the sourced [issue-to-planner handoff](#prepare-the-issue-to-planner-handoff), exact base, capsule format, branch rules, planning paths, and stop conditions. | Dispatch the planner only with a bounded planning task. |
| **After planner return** | Verify the reported branch, base, P SHA, capsule path and clean/allowed-dirty state against Git; check a remote ref if the planner published one under the consumer's rules. Inspect base..P and the capsule. Reconcile the planner's requirement-to-AC/contract trace with the original objective; verify owned paths, profiles, checks, evidence routes, non-goals, gaps, and recovery. Run the consumer's draft/planning checks and resolve semantic omissions. | Publish/record validated P through the consumer route, or repair planning and revalidate. |
| **Before implementor dispatch** | Complete the [pre-dispatch gate table](#check-the-execution-plan-before-dispatch), including every AC and required review standard. Rehearse costly or sandbox-sensitive commands where safe. Confirm exact P still heads the branch, the implementation checkout is ready, the selected model/effort and host have required access, and the handoff contains the frozen capsule, permitted source context, checks, and STOP_REPLAN route. | Delegate implementation bound to P and the dedicated branch. |
| **After implementor return** | Require DONE or a precise failure, C SHA, branch/ref, changed-file list, check results, and unresolved gaps. Independently verify the committed branch head and remote ref where required, clean/allowed-dirty state, base..P and full P..C diffs, owned paths, profiles, new tests, and applicable cross-platform fixtures. A DONE flag or matching counts alone is insufficient. | Preserve failed C/evidence for repair; otherwise prepare exact-C qualification. |
| **Before exact-C qualification** | Reconcile the gate table with every changed file, required profile, and standard. Confirm each command's path, host, inputs and evidence location; rehearse costly or sandbox-sensitive invocation where safe. Ensure C and its source material are stable and that no required test or fixture is missing. | Run the consumer's mandatory local/native and hosted gates on exact C; preserve raw results. |
| **After qualification, before reviewer dispatch** | Verify Q(C) names the exact candidate, host/profile, commands, exit status, logs, coverage gaps, and hosted-check SHA. A missing or failed mandatory gate remains unresolved. Assemble the capsule/intent, B/P/C, full diff and changed-file inventory, expected AC observations, Q(C), and per-standard evidence. Recheck branch head C and give a fresh reviewer enforced read-only access. | Dispatch one exact-C independent review only with a complete, authenticated packet. |
| **After reviewer return** | Authenticate the verdict's branch and C against current Git state. Require a finding or evidence-backed disposition for every active AC and applicable standard; reconcile each finding with the original objective, qualification, and changed-file inventory. Treat absent dispositions, unsupported evidence, or a moved C as unresolved. | Preserve failed C/findings and return an in-scope correction or replan; a complete PASS proceeds to guarded integration checks. |
| **Before guarded integration** | Recheck published base/ref and candidate head; ensure required Q(C), fresh independent R(C), all active criteria and standards, approvals, and consumer-specific publication conditions bind the same C. Requalify and re-review any changed C or execution-relevant base. | Use only the consumer's authorized approval, publication, and acceptance route. |
| **After integration and review closeout** | Verify the intended target contains the reviewed candidate or approved merge result, record integration identity, confirm evidence is retained and review/issue status is reconciled. Check that no active capsule, worktree, or follow-up needs the branch. | Close the issue when its objective is satisfied; delete the completed capsule branch and unused local copies through the consumer route. Retain unmerged or still-used branches. |
| **On failure, interruption, or changed scope at any stage** | Preserve the exact P/C, command outputs, findings, and current ref state. Classify an in-scope correction, bounded infrastructure retry, replacement capsule, or decision outside current authority. Never infer success from a missing callback or reuse proof for changed source. | Resume the authorized stage with fresh checks, or STOP_REPLAN and bring only the concrete unresolved decision to the user. |

The gate before reviewer dispatch checks that the packet is complete; it cannot
prejudge the review. A reviewer finding remains a finding even if the planned
gate table and qualification passed. No subagent result grants a new edit path,
waives a mandatory host, or approves integration.

## Role detail for the controller gates

The gate table above is the advance/stop sequence. These notes describe what
each role does while the controller carries it out.

1. **Controller and planner subagent:** The controller establishes the objective,
   current issue, accepted runner lane, authenticated base, consumer rules,
   supported host, and unresolved decisions. Delegate capsule drafting and
   dedicated branch creation to a planner subagent. It returns the capsule,
   branch/ref, P SHA, edit/read scope, non-goals, independently expected ACs,
   checks, and stop conditions. The controller inspects the actual planning
   diff, runs draft/planning checks, resolves omissions, publishes the validated
   branch, and verifies its remote/ref and P SHA before implementation. It
   records and checks the pre-dispatch gate table above before handing off. Use the
   [capsule preflight template](skill-templates/capsule-preflight/SKILL.md)
   to authenticate the envelope; it cannot supply missing authority.
2. **Context:** Ask RI a specific source question only where it helps. Bind each
   selected location to the intended blob, inspect actual source/callers/types,
   and retain parser coverage gaps. Give the implementor the selected context
   through the consumer's supported read or page lane. Use the
   [RI evidence handoff](skill-templates/ri-evidence-handoff/SKILL.md)
   skill to bind selected evidence. See the
   [consumer guide](consumer-guide.md), and the
   [Poker example](poker-capsule-workflow.md).
3. **Implementor subagent:** Authenticate P and the planner-created branch
   before editing, using `capsule-preflight` where installed. Work only within
   the capsule's grants. Commit and push C to the dedicated branch when that
   is the consumer's authorized candidate route; never push directly to main.
   Run new tests and applicable cross-platform fixtures before freezing C.
   Return DONE or STOP_REPLAN, C SHA, changed paths, authored tests, exact
   checks and results, unresolved questions, and any scope collision. The
   controller compares planning P to candidate C and keeps the base-to-P planning change
   separate. A structural RI delta is optional; the full P..C Git diff is mandatory.
   Wait for native completion, then authenticate the returned metadata against
   the branch and repository before treating DONE as a candidate handoff.
4. **Controller:** Fetch the recorded branch and verify its head equals the
   returned C SHA and that the changed-file inventory matches P..C. Reconcile
   the gate table with the actual changed files, execution profiles, and full
   reviewer packet. Rehearse costly or sandbox-sensitive commands where safe
   before remote qualification, then qualify exact C using the authored checks
   on the required host. Route long external gates through their own supported
   completion mechanism. Open or update a review PR when the consumer uses
   GitHub PRs; confirm that consumer's hosted checks
   actually ran for the candidate. A branch push alone is not a hosted pass.
   Save raw status and logs bound to C.
5. **Fresh reviewer subagent:** Receive the exact capsule/intent, branch/ref, and P/C
   identities, complete diff and changed-file inventory, raw qualification evidence, and
   current standards. Read the candidate independently and return a PASS/FAIL
   disposition for every active criterion and applicable standard. Missing
   evidence is not PASS. Use the
   [independent review skill](skill-templates/capsule-independent-review/SKILL.md)
   when it is available in the reviewer's environment. Wait for its native
   completion, then authenticate the verdict's exact candidate metadata.
6. **Controller:** Recheck the branch head before integration. If it moved
   beyond the reviewed C, bind qualification and fresh review to the new SHA.
   Reconcile findings, then use the consumer's existing guarded
   approval, publication, acceptance, and closeout interfaces. A reviewer
   verdict alone does not perform those actions. Once the reviewed candidate
   is integrated, the review is closed, and evidence is retained, delete the
   dedicated remote branch and unused local copies. Keep a branch that remains
   unmerged or in use. Record branch cleanup with the merge identity.

The controller owns continuation for the authorized objective. A test failure,
review finding, or recoverable interruption should not by itself require the
user to say "continue" or request another capsule. The controller should do
the authorized repair, checks, and handoff, and surface only an actual decision
or final result. This does not grant a wider task or bypass a required host,
reviewer, or approval boundary.

Native completion returns each child result to the parent controller. The
controller waits for that result once and verifies its evidence. A long external
qualification gate may have its own watcher; it is separate from these three
subagent handoffs and cannot supply a planner, candidate, or reviewer verdict.

## Recovery without repeated user turns

Put these rules in each consumer's capsule template or controller instructions,
using that consumer's existing fields rather than adding an RI policy format:

| Event | Controller action |
| --- | --- |
| Transient download, runner, or connection failure | Preserve the attempt and raw error; retry the same gate only when its own policy permits a bounded retry. Never call an absent result PASS. |
| Failing authored test or reviewer finding within scope | Preserve the failed C SHA and evidence. Return the finding to the implementor, have the implementor push a new candidate to the same capsule branch, and rerun applicable qualification and review for the new SHA. |
| Missing source context or RI coverage gap | Use the capsule's allowed read/expansion lane or ask a narrower question. Keep the incomplete result; do not infer absent behavior. |
| Fix requires paths or behavior outside the capsule | `STOP_REPLAN`. The controller may draft a replacement capsule for the same authorized objective, then authenticate its new scope/base and run the consumer's planning checks before dispatch. |
| Changed objective, unavailable mandatory prerequisite, or action requiring new authorization | Bring the concrete decision to the user with the evidence and available options. |

Retain failed candidates and review packets. A changed candidate or
execution-relevant base invalidates earlier candidate-bound proof; do not
transfer an old PASS. Avoid creating an automatic series of replacement
capsules with guessed authority: one authenticated revision is preferable to
retries that hide the underlying mismatch.

## Put the skills where each role can use them

The [skill templates](skill-templates/README.md) are portable source files, not
an RI runtime dependency. Install only the skills useful to that project's
roles. The consumer's `AGENTS.md` and capsule remain authoritative if a skill
example disagrees with them. A local Codex installation does not register a
skill in ChatGPT Work. Verify Work availability separately before relying on
automatic activation. Follow the
[new-project setup guide](new-project-setup.md) to install the appropriate
skills for each role and test the handoff before adoption.
