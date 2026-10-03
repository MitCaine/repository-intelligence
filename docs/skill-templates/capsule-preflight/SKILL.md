---
name: capsule-preflight
description: Authenticate an active task capsule and its exact repository state before capsule implementation, qualification, or review. Use when a consumer project runs a capsule workflow; do not apply to ordinary standalone RI work.
---

# Capsule preflight

Follow the [current controller workflow](../../start-an-issue.md).
Read the bounded task and project-root `docs/local_project_map.md`; authenticate objective, current phase,
base/branch/source, permitted scope, runtime compatibility and required commands.
Initial dispatch starts at planning; correction dispatch starts at the authenticated
recovery parent. Do not require nonexistent future candidate or review records.

Inspect relevant source, callers and tests to check scope and criterion coverage.
Require affected current documentation/link updates (or an evidenced not-applicable
conclusion) in scope and acceptance. Resolve specification gaps before dispatch.
Use the project's existing task record, not a new packet/schema. Independent scope
challenge is optional unless a separately adopted project requirement needs it.

Uninspected evidence is not failed authentication. Use bounded clarification and
read-only diagnosis without another human approval. Hold execution at a blocker,
consolidate supported findings and unknowns, and use the smallest authorized
recovery. STOP_REPLAN is last resort, never opening progress. Preserve actual
terminal stops and allowances; diagnosis does not resume stopped execution.

Return authenticated identities, criteria/check mapping, gaps and permitted next
action. Keep source edits with the implementor. RI evidence is not acceptance.
The [evidence checker](scripts/evidence_preflight.py) and
[adapter contract](references/evidence-contract.md) are optional extended helpers;
use only when separately selected by the consumer. Their checks do not add gates
to this lightweight route.
