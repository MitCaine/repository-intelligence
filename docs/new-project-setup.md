# Set up RI and capsule skills in a new project

Use this checklist when a consumer project wants the
[controller workflow](capsule-controller-workflow.md). RI also works for ordinary
source lookup without capsules or these skills. A skill helps an agent follow a
procedure; it does not create a capsule runner, repository permission, review
independence, or a completion channel.

## One-time project setup

1. **Establish the consumer's authority.** Identify its issue source, capsule
   format and runner, base/planning checks, permitted branch and push route,
   supported hosts, qualification commands, independent review lane, and
   guarded integration process. Keep those rules in the consumer project. Adapt
   the RI templates to them before installation.
2. **Provision RI separately.** Follow the [consumer guide](consumer-guide.md)
   and pin the installed RI commit or retained bundle. Try one source query and
   inspect its identity and coverage status. RI is source evidence, not the
   authority for a capsule.
3. **Install the relevant skill folders for local Codex.** Copy the whole
   selected folders from [RI's templates](skill-templates/README.md) into the
   consumer repository's `.agents/skills/`. Compare any existing skill before
   replacing it.
   Record the RI template revision and project adaptations. Check that Codex
   discovers the skills from that repository and try a harmless invocation.
4. **Make every role able to read its instructions.** The continuing controller
   and capsule planner need the adapted `capsule-preflight` and
   `ri-evidence-handoff` instructions. The implementor needs preflight and the
   exact capsule. The fresh reviewer needs `capsule-independent-review` and may
   use `ri-evidence-handoff` for source inspection. Provide these through the
   environment's supported skill route or in each handoff packet. A local
   `.agents/skills/` copy does not install skills in a Work chat. Verify actual
   availability for all four roles.
5. **Test native subagent completion.** The controller should delegate a small
   capsule to a planner, verify returned P, delegate implementation with P,
   verify returned C, then delegate a fresh read-only review with exact P/C.
   Confirm branch and SHA metadata at every return. Test both successful and
   failed subagent returns in the actual host. Use native completion rather
   than repeated controller status checks; no queue helper is needed for these
   three handoffs.
6. **Test the external qualification return route.** If a long hosted gate has
   no reliable native completion, install the whole `capsule-queue` template
   including its helper and test one terminal success and failure to the exact
   controller destination. `codex queue` targets a Codex session; a Work
   controller needs a tested bridge or supported bounded wait. Select the
   route at dispatch so one hosted run does not cause repeated controller turns.
7. **Run a trial capsule.** Use the [adoption cases](adoption-cases.md) to check
   correct and incorrect skill activation, branch creation and candidate push,
   all [controller gates](capsule-controller-workflow.md#controller-gates-from-intake-through-closeout),
   command rehearsal, exact-SHA qualification, fresh review, correction, and closeout. Record the
   result before calling the setup reliable.

The [native subagent handoff](capsule-controller-workflow.md#delegate-through-native-subagents)
uses one continuing controller, a capsule planner, a Luna Max implementor, and
a fresh read-only reviewer. Sol Light is the target controller model and the
tested planner and reviewer model; confirm model names, efforts, repository access, and enforced review
permissions in each consuming host before relying on the route.

| Stage | Skill to use when applicable | Owner |
| --- | --- | --- |
| Authenticate capsule, branch, P, and scope | `capsule-preflight` | Controller, planner, and implementor |
| Select and bind source context or P-to-C evidence | `ri-evidence-handoff` | Controller; implementor or reviewer as needed |
| Judge exact pushed candidate independently | `capsule-independent-review` | Fresh reviewer |
| Return planner, implementor, and reviewer results | Native subagent completion | Continuing controller verifies each result |
| Return a long external gate result without native completion | `capsule-queue` with verified destination | Controller verifies retained terminal evidence |

The [skill templates](skill-templates/README.md) are the source to copy. Use
only the skills relevant to the consumer's actual workflow. At each handoff,
give the agent the capsule and exact identities; do not assume skill discovery
or a role name supplies missing evidence.

## Branch closeout

The controller owns branch cleanup after the consumer's guarded integration.
Confirm the reviewed candidate was integrated into the intended target, the
PR or equivalent review is closed, required evidence is retained outside the
branch, and no active capsule, worktree, or follow-up depends on that ref. Then
delete the dedicated capsule branch from the remote and remove unused local
branch copies through the consumer's supported cleanup route. Record the merge
commit and cleanup outcome in the existing closeout record. Do not delete an
unmerged, failed, or still-in-use branch merely because its review finished.

This is a terminal step of each completed capsule, so routine successful work
does not leave a growing collection of capsule branches. Repository settings
such as automatic branch deletion are optional; they do not replace the
controller's verification that cleanup happened.
