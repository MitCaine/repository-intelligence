# Optional capsule workflow skill templates

These templates help a consumer project implement the
[controller workflow](../capsule-controller-workflow.md). They are examples for
agents, not RI package behavior or permission policy. Read each `SKILL.md` and
adapt repository-specific commands, accepted review lanes, supported hosts, and
approval boundaries against the consumer's current capsule contract before
installing it. Keep the capsule and local `AGENTS.md` authoritative.
Start with the [new-project setup checklist](../new-project-setup.md) when
adopting the workflow in a consumer repository.
In the documented handoff, the controller delegates dedicated branch and
capsule creation to a planner subagent, then verifies its remote and planning
state. The implementor pushes candidate commits to that branch for review. A
consumer adaptation should retain this
role split and make any different branch policy explicit.

| Template | Role | Copy when |
| --- | --- | --- |
| [capsule-preflight](capsule-preflight/SKILL.md) | Controller, planner, or implementor | The project has an active capsule workflow with exact base/scope checks. |
| [capsule-scope-review](capsule-scope-review/SKILL.md) | Fresh read-only scope challenger | The impact inventory needs independent challenge before implementation authorization. |
| [ri-evidence-handoff](ri-evidence-handoff/SKILL.md) | Controller, implementor, or reviewer | RI locations or comparisons will enter a handoff. |
| [capsule-independent-review](capsule-independent-review/SKILL.md) | Fresh reviewer | The consumer requires candidate-bound independent review. |
| [capsule-queue](capsule-queue/SKILL.md) | External gate watcher | A long non-subagent job has no native completion and its exact Codex controller destination is verified. Use a tested Work bridge or bounded wait for a Work controller. Native subagent handoffs use their completion events. |

For a project-scoped Codex installation, copy the chosen **whole skill folders**
to that project's `.agents/skills/` (or the skill location supported by its
actual Codex installation). The queue folder includes its required helper
script. For personal local Codex use, install under the local Codex skills
directory instead. Validate each copied folder with the available skill
validator and try one realistic, non-destructive invocation before relying on
it. Do not replace an existing project skill without comparing its instructions.
Record the RI commit and template path used for each copied skill in the
consumer's existing maintenance notes, along with local adaptations. On a
later RI update, compare the installed folder with that recorded template
revision and the new template before editing it. A plain `diff -ru` or Git
comparison is enough; do not automatically overwrite a consumer's authority
rules or change skills during an active attempt. From the actual consuming
workspace, verify that a fresh agent discovers the intended instructions and
selects the intended skill for a representative request.

ChatGPT Work has a separate skill lifecycle; copying files into a Mac checkout
does not make them available in a Work chat. Give the controller, planner,
implementor, and reviewer their applicable instructions through the supported
workspace route, then verify availability. The native subagents return to the
same parent controller. Use the queue template for a long external gate that
lacks native completion and has a verified destination; it is unnecessary for
these subagents.

The preflight folder includes a read-only [evidence checker and adapter contract](capsule-preflight/references/evidence-contract.md).
Its [closeout checks](capsule-preflight/references/evidence-contract.md#closeout-and-installed-workflow-probes)
cover consumer-exported history metadata and required installed-workflow probes.
Copy its supporting resources with the skill and connect it to the consumer's
trusted records before treating it as a blocking gate. The scope-review skill
handles purpose and missing dependencies that deterministic checks cannot infer.

Keep the templates narrow. A project need not install all five, and no skill
creates capsule authority, review independence, or a successful qualification
merely by being present.
