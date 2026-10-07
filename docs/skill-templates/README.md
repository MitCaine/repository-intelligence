# Optional capsule workflow skill templates

Controllers use [Start an issue](../start-an-issue.md); workers use their
[selected worker instructions](../worker-instructions.md#role-index).
These current skill templates are optional resources, not five mandatory installations
or a reason to add packet/export/protected-launcher gates. Adopt only instructions
needed by the selected consumer route; an ordinary role handoff can carry the
lightweight instructions directly.

These templates help a consumer project implement the
[controller workflow](../capsule-controller-workflow.md). They are examples for
agents, not RI package behavior or permission policy. Read each `SKILL.md` and
adapt repository-specific commands, accepted review lanes, supported hosts, and
approval boundaries against the consumer's current capsule contract before
installing it. Use the project map to distinguish shared RI instructions from independently required local controls. Resolve contradictions before dispatch; do not silently select a conflicting procedure.
Start with the [new-project setup checklist](../new-project-setup.md) when
adopting the workflow in a consumer repository.
Follow the [daily publication sequence](../start-an-issue.md#execute-serially):
the controller creates and publishes the task branch; the authorized actor publishes
the planning capsule before implementation and the exact candidate before review.
The project map assigns actors, tracked capsule storage and commands; implementor
commit/push requires an explicit grant. Keep private operational records out of
publication unless authorized. Keep planning, implementation and fresh review
roles separate; no subagent publishes directly to main.

| Template | Role | Copy when |
| --- | --- | --- |
| [capsule-preflight](capsule-preflight/SKILL.md) | Controller, planner, or implementor | The project has an active capsule workflow with exact base/scope checks. |
| [capsule-scope-review](capsule-scope-review/SKILL.md) | Fresh read-only scope challenger | The impact inventory needs independent challenge before implementation authorization. |
| [ri-evidence-handoff](ri-evidence-handoff/SKILL.md) | Controller, implementor, or reviewer | RI locations or comparisons will enter a handoff. |
| [capsule-independent-review](capsule-independent-review/SKILL.md) | Fresh reviewer | The consumer requires candidate-bound independent review. |
| [capsule-queue](capsule-queue/SKILL.md) | External gate watcher | A long non-subagent job has no native completion and its exact Codex controller destination is verified. Use a tested Work bridge or bounded wait for a Work controller. Native subagent handoffs use their completion events. |

For a project-scoped Codex installation, copy the chosen **whole skill folders**
to that project's `.agents/skills/` (or the skill location supported by its
actual Codex installation). Every folder includes `references/project-procedure.md`, which resolves the
caller’s selected role instructions through its handoff and the project map. The queue folder
also includes its required helper script. For personal local Codex use, install under the local Codex skills
directory instead. After copying, check every relative resource link in the installed folder, then
from the consuming workspace resolve the selected role resource through the
existing handoff/map and verify its recorded identity. Workers read only their
role/task inputs and relevant shared rules; the controller reads the full procedure. Template-tree validation alone does not prove
installed-layout validity. Validate each copied folder with the available skill
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
does not make them available in a Work chat. Give the conditional scope challenger, controller, planner,
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

## Mechanical validation boundary

The offline checker supports inline and reference links, same-page fragments
and visible inline-code words in heading anchors. RI template frontmatter uses
a deliberately narrow YAML subset: exactly one top-level `name` and
`description`, each a nonempty single-line plain or quoted string. Complex YAML,
extra/nested fields, duplicate keys and ambiguous scalars are rejected; double
quoted strings use JSON-compatible escapes. This subset is not a general YAML
parser or validation of arbitrary installed skills. Linked helpers must exist.
Installation trials still check actual copied resources and skill behavior.
