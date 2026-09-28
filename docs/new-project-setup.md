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
   consumer repository's `.agents/skills/`, including the queue helper script
   if using `capsule-queue`. Compare any existing skill before replacing it.
   Record the RI template revision and project adaptations. Check that Codex
   discovers the skills from that repository and try a harmless invocation.
4. **Make the Work roles able to read their instructions.** The controller needs
   the adapted `capsule-preflight` and `ri-evidence-handoff` instructions. The
   separate, fresh reviewer needs `capsule-independent-review` and may use
   `ri-evidence-handoff` for source inspection. Provide these through the
   supported ChatGPT Work workspace skill or plugin route, or explicitly in the
   role's handoff packet. A local `.agents/skills/` copy does not install skills
   in a Work chat. Verify availability in both Work roles before relying on
   automatic activation.
5. **Configure terminal delivery only where needed.** `capsule-queue` is for an
   external job that otherwise needs polling. Use native agent completion when
   it already wakes the controller. If the controller is in Work, verify an
   actual Work completion route or tested bridge; a local `codex queue` target
   alone is insufficient. Test one completed job and one failed delivery.
6. **Run a trial capsule.** Use the [adoption cases](adoption-cases.md) to check
   correct and incorrect skill activation, branch creation and candidate push,
   exact-SHA qualification, fresh review, correction, and closeout. Record the
   result before calling the setup reliable.

For the first trial, choose the [Work-to-Codex chat or terminal transport](capsule-controller-workflow.md#launch-the-codex-implementor-from-a-terminal).
The Work route gives the Codex chat the exact capsule, branch and P. The CLI
route uses the consumer's owning launch command. If none exists, the minimal
terminal example requests `gpt-6-luna` with Max reasoning; build and validate
the missing preflight, result capture and candidate transaction before adopting
it. Poker App owns a different exact direct wrapper in its
[command guide](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/CAPSULE_COMMANDS.md).

| Stage | Skill to use when applicable | Owner |
| --- | --- | --- |
| Authenticate capsule, branch, P, and scope | `capsule-preflight` | Controller and implementor |
| Select and bind source context or P-to-C evidence | `ri-evidence-handoff` | Controller; implementor or reviewer as needed |
| Judge exact pushed candidate independently | `capsule-independent-review` | Fresh reviewer |
| Notify one terminal external-job outcome | `capsule-queue` | Verified watcher route; controller receives result |

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
