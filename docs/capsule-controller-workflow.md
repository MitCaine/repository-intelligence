# Capsule controller workflow with RI

This is a reusable handoff pattern, not an RI execution policy. The consumer
repository's current capsule contract, runner, issue state, and supported-host
rules control the work. RI supplies bounded source evidence. The example roles
are Controller, Implementor, and Independent Reviewer. Consumer projects may
choose models and effort levels using their own evaluated workflow. Local Codex
skills do not automatically appear in Work chats.

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

For each capsule, the controller authenticates the base, creates a dedicated
branch, writes the capsule and planning state P through the consumer's planning
route, validates P, then publishes the branch and records its exact remote/ref
and P SHA before dispatch. The implementor commits and pushes candidate work
to that branch for review. Use forward pushes so earlier candidate SHAs remain
reachable; preserve failed candidate evidence separately. A push makes a
candidate available; it does not qualify, approve, or integrate it. The
consumer's guarded acceptance path controls integration into `main`.

```text
User objective
    |
    v
Controller
  authenticate issue + current repository state
  write decision-complete capsule in consumer's format
  create dedicated capsule branch from authenticated base
  validate P, publish branch, record remote/ref + P SHA; dispatch
    |
    v
Preflight exact capsule/base/planning overlay/scope/host
    | mismatch --> STOP_REPLAN --> controller repairs capsule --> preflight
    v
RI evidence, if useful: locate -> inspect -> bind to exact Git blob
    |
    v
Implementor -> commit and push C to capsule branch + tests + return packet
    | terminal result --> event route --> controller wakes once
    |
    v
Controller verifies pushed C, then qualifies exact C on required host/checks
    | terminal result --> event route --> controller wakes once
    | failure --> preserve C/evidence --> correction or revised capsule --+
    v                                                                |
Independent Reviewer (fresh read-only context)                 |
  exact capsule + P/C + full diff + qualification evidence              |
    | terminal verdict --> event route --> controller wakes once         |
    | FAIL or missing evidence --> preserve C/findings -----------------+
    v PASS for every active criterion and applicable standard
Controller reconciles and uses consumer's guarded approval,
publication, acceptance, and closeout commands
  verify integration and retained evidence; delete completed capsule branch

Event route: native completion callback when reliable; otherwise
capsule-queue watches the external job and sends one terminal result
to a verified controller session. No repeated agent-status polling.
```

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

The controller authors `Expected` and `Check` before implementation. The implementor may
check off implementation work, but only candidate-bound check results and the
fresh reviewer can satisfy the AC. If a requirement cannot be made observable,
resolve it before dispatch rather than leaving the implementor to guess.

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

## Launch the Codex implementor from a terminal

There are two supported handoff shapes for this guide:

| Implementor transport | How the controller starts it | What returns |
| --- | --- | --- |
| Work to Codex chat | Launch a separate Codex chat with the exact capsule, branch, P and selected context | Chat completion and a candidate handoff through the available chat channel |
| Terminal Codex CLI | Run the consumer's authenticated wrapper, or the minimal `codex exec` example below after adding its missing checks | Process exit, saved result and terminal notification or a verified queue callback |

Use the same capsule, scope, checks and downstream review requirements in
either route. A `.py` checkpoint command is a separate candidate transaction:
it consumes C after implementation and does not start a Codex chat or execute
the capsule for Codex. The controller selects one implementation transport per
attempt and does not run both over the same workspace.

For a consumer without an owning launcher, the controller can run Codex from
the checkout at authenticated planning state P. Replace `<capsule-path>` with
that project's active capsule path. This is a minimal implementation command
(wrapped for readability); the consumer still owns preflight, qualification,
review, commit and publication:

```sh
codex exec -m gpt-6-luna -c 'model_reasoning_effort="max"' \
  --sandbox workspace-write --approve-for-me \
  'Read and preflight <capsule-path> against the recorded branch and P. Implement only its authorized scope and report changed paths, test results, and unresolved gaps. STOP_REPLAN on an authority mismatch.'
```

The controller substitutes the actual capsule path and retains the command's
terminal output and exit status with the candidate handoff. `--approve-for-me`
routes eligible tool approvals through automatic review; it does not grant
wider capsule scope. This example does not supply a complete execution wrapper
or authorize Codex to commit and push. If the consumer owns a launch command,
use that exact command and its model/effort settings instead of this example.
For Poker App, the current literal command owner is
[CAPSULE_COMMANDS.md](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/CAPSULE_COMMANDS.md):
its direct wrapper requests `gpt-5.6-luna` at Max, authenticates the branch,
planning SHA, capsule and runtime, preserves the process result, and alerts on
completion. The Poker checkpoint CLI consumes committed C; it does not launch
implementation. Poker's controller/operator transaction handles commit,
qualification, review and candidate publication after the direct Codex process.
The exact command flags and Luna's Max support are documented in
[OpenAI's CLI settings](https://learn.chatgpt.com/docs/developer-settings),
[CLI commands](https://learn.chatgpt.com/docs/developer-commands), and
[Luna model reference](https://developers.openai.com/api/docs/models/gpt-6-luna).

## Run one objective to completion

1. **Controller:** Establish the objective, current issue and active-capsule
   state, accepted runner lane, exact base and planning identities, edit/read
   scope, non-goals, independently expected acceptance results, required checks,
   supported host, and stop conditions. Create the capsule using the consumer's
   existing schema. Create its dedicated branch from the authenticated base,
   put planning state P on it through the consumer's planning route, and run
   draft/planning checks. Publish the validated branch and record its exact
   remote/ref and P SHA before dispatch. Use the
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
3. **Implementor:** Authenticate P and the controller-created branch before
   editing, using `capsule-preflight` where installed. The Work controller may
   launch a Codex chat with the exact handoff; the terminal route uses the
   consumer's wrapper or the example above when no launcher exists. Work only within the
   capsule's grants. The controller/operator commits and publishes candidate C
   under the consumer's policy; in Poker's current direct lane, Codex does not
   commit or push. Return changed paths, authored tests, exact commands
   and results, unresolved questions, and any scope collision. The controller
   compares planning P to candidate C and keeps the base-to-P planning change
   separate. A structural RI delta is optional; the full P..C Git diff is mandatory.
   At dispatch, establish how its terminal result reaches the controller. Use
   the native agent completion channel when it reliably wakes the controller;
   for an external job requiring status checks, use the
   [queue skill](skill-templates/capsule-queue/SKILL.md) with a blocking watcher.
4. **Controller:** Fetch the recorded branch and verify its head equals the
   returned C SHA and that the changed-file inventory matches P..C. Qualify
   exact C using the authored checks on the required host. Route long external
   gates through the same terminal event pattern. Open or update a review PR
   when the consumer uses GitHub PRs; confirm that consumer's hosted checks
   actually ran for the candidate. A branch push alone is not a hosted pass.
   Save raw status and logs, then wake the verified controller session once.
5. **Fresh reviewer:** Receive the exact capsule/intent, branch/ref, and P/C
   identities, complete diff and changed-file inventory, raw qualification evidence, and
   current standards. Read the candidate independently and return a PASS/FAIL
   disposition for every active criterion and applicable standard. Missing
   evidence is not PASS. Use the
   [independent review skill](skill-templates/capsule-independent-review/SKILL.md)
   when it is available in the reviewer's Work environment.
   Arrange its completion route at dispatch as well; the queue is a notifier,
   never a substitute for the review verdict.
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

**Queue routing matters:** `codex queue` targets an existing Codex session. It
does not by itself address an arbitrary ChatGPT Work chat. For a Work
controller, use its verified native agent completion/wait facility or an
explicitly tested bridge to the controller's exact task. Where a job exposes
only status polling, attach one bounded watcher with a deadline and terminal
notification; do not spend repeated controller turns checking unchanged state.
If no terminal delivery route exists, use one supported blocking wait rather
than claiming that a queue message reached Work. Never infer a destination
from a role name or the most recently active chat.

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
automatic activation or a cross-chat callback. Follow the
[new-project setup guide](new-project-setup.md) to install the appropriate
skills for each role and test the handoff before adoption.
