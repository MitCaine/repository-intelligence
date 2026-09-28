# Capsule controller workflow with RI

This is a reusable handoff pattern, not an RI execution policy. The consumer
repository's current capsule contract, runner, issue state, and supported-host
rules control the work. RI supplies bounded source evidence. The example roles
are a Sol Light ChatGPT Work controller, a Luna Max Codex implementor, and a
separate Sol Light Work reviewer; the contracts matter more than those model
names. Local Codex skills do not automatically appear in Work chats.

## Why this guide exists

The controller needs one place to orient a task before dispatch: what outcome
the user authorized, what the capsule permits, which source facts RI can add,
what each actor must return, and which evidence is required to finish. The
goal is to complete routine implementation and correction loops without asking
the user to restate the same objective. The capsule still comes from the
consumer project's contract. This guide does not create a second RI capsule
schema, a permission grant, or a shortcut around qualification and review.

```text
User objective
    |
    v
Controller (Sol Light, Work)
  authenticate issue + current repository state
  write decision-complete capsule in consumer's format
    |
    v
Preflight exact capsule/base/planning overlay/scope/host
    | mismatch --> STOP_REPLAN --> controller repairs capsule --> preflight
    v
RI evidence, if useful: locate -> inspect -> bind to exact Git blob
    |
    v
Implementor (Luna Max, Codex) -> candidate C + tests + return packet
    | terminal result --> event route --> controller wakes once
    |
    v
Controller qualifies exact C on required host/checks
    | terminal result --> event route --> controller wakes once
    | failure --> preserve C/evidence --> correction or revised capsule --+
    v                                                                |
Fresh reviewer (separate Sol Light Work chat, read-only)                 |
  exact capsule + P/C + full diff + qualification evidence              |
    | terminal verdict --> event route --> controller wakes once         |
    | FAIL or missing evidence --> preserve C/findings -----------------+
    v PASS for every active criterion and applicable standard
Controller reconciles and uses consumer's guarded approval,
publication, acceptance, and closeout commands

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
- [ ] **Exact source state:** Record the base, planning object/overlay, branch,
  and expected clean or allowed-dirty state. Keep the base-to-planning change
  separate from the planning-to-candidate implementation change.
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

The controller authors `Expected` and `Check` before implementation. Luna may
check off implementation work, but only candidate-bound check results and the
fresh reviewer can satisfy the AC. If a requirement cannot be made observable,
resolve it before dispatch rather than leaving the implementor to guess.

## Hand-off packets and done condition

Keep handoffs short but exact. The controller sends the implementor the frozen
capsule, selected authenticated source/contract excerpts, permitted repository
read route, and how to report a scope collision. The implementor returns C,
changed paths, complete diff location, test commands/results, and unresolved
questions. The controller adds qualification Q(C), host/settings, raw logs,
coverage gaps, and the complete changed-file inventory for the fresh reviewer.
The reviewer returns a finding or PASS/FAIL for every active criterion and
applicable standard, all tied to C. The controller records disposition and uses
the consumer's guarded closeout path. No model role or skill name substitutes
for an artifact, command result, or required approval.

## Run one objective to completion

1. **Controller:** Establish the objective, current issue and active-capsule
   state, accepted runner lane, exact base and planning identities, edit/read
   scope, non-goals, independently expected acceptance results, required checks,
   supported host, and stop conditions. Create the capsule using the consumer's
   existing schema. Run its draft/planning checks. The
   [capsule preflight template](skill-templates/capsule-preflight/SKILL.md)
   helps authenticate the envelope; it cannot supply missing authority.
2. **Context:** Ask RI a specific source question only where it helps. Bind each
   selected location to the intended blob, inspect actual source/callers/types,
   and retain parser coverage gaps. Give the implementor the selected context
   through the consumer's supported read or page lane. See
   [RI evidence handoff](skill-templates/ri-evidence-handoff/SKILL.md), the
   [consumer guide](consumer-guide.md), and the
   [Poker example](poker-capsule-workflow.md).
3. **Implementor:** Work only within the capsule's grants. Return the candidate
   commit or immutable identity, changed paths, authored tests, exact commands
   and results, unresolved questions, and any scope collision. The controller
   compares planning P to candidate C and keeps the base-to-P planning change
   separate. A structural RI delta is optional; the full Git diff is mandatory.
   At dispatch, establish how its terminal result reaches the controller. Use
   the native agent completion channel when it reliably wakes the controller;
   for an external job requiring status checks, use the
   [queue skill](skill-templates/capsule-queue/SKILL.md) with a blocking watcher.
4. **Controller:** Qualify the exact C using the authored checks on the required
   host. Route long external gates through the same terminal event pattern.
   Save raw status and logs, then wake the verified controller session once.
5. **Fresh reviewer:** Receive the exact capsule/intent, P and C identities,
   complete diff and changed-file inventory, raw qualification evidence, and
   current standards. Read the candidate independently and return a PASS/FAIL
   disposition for every active criterion and applicable standard. Missing
   evidence is not PASS. Use the
   [independent review template](skill-templates/capsule-independent-review/SKILL.md).
   Arrange its completion route at dispatch as well; the queue is a notifier,
   never a substitute for the review verdict.
6. **Controller:** Reconcile findings, then use the consumer's existing guarded
   approval, publication, acceptance, and closeout interfaces. A reviewer
   verdict alone does not perform those actions.

The controller owns continuation for the authorized objective. A test failure,
review finding, or recoverable interruption should not by itself require the
user to say "continue" or request another capsule. The controller should do
the authorized repair, checks, and handoff, and surface only an actual decision
or final result. This does not grant a wider task or bypass a required host,
reviewer, or approval boundary.

**Queue routing matters:** `codex queue` targets an existing Codex session. It
does not by itself address an arbitrary ChatGPT Work chat. For a Sol Work
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
| Failing authored test or reviewer finding within scope | Preserve C and evidence. Return the finding to the implementor, make a new candidate, and rerun applicable qualification and review for that candidate. |
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
automatic activation or a cross-chat callback.
