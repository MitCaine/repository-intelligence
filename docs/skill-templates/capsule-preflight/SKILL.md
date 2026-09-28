---
name: capsule-preflight
description: Authenticate an active task capsule and its exact repository state before capsule implementation, qualification, or review. Use when a consumer project runs a capsule workflow; do not apply to ordinary standalone RI work.
---

# Capsule preflight

Treat the consumer repository's current capsule contract and accepted runner as execution authority. Read the active capsule and relevant local workflow instructions; never infer authority from this skill, RI output, issue prose, or an old transcript.

Before the requested capsule step, establish the current repository and issue state, capsule revision, controller-created dedicated branch and recorded remote, exact base and planning identities, active overlay, allowed reads and edits, acceptance criteria, required checks, supported host, and stop conditions. Check them against the actual checkout and the selected runner lane. Distinguish the base-to-planning change from the planning-to-candidate implementation change. Preserve unrelated dirty work. The implementor may commit and push authorized candidate work to that branch for review, but not to `main`; a push is not approval or acceptance.

For a draft capsule, check that each active acceptance criterion has a stable ID, independently expected result, and authored verification route, including negative or boundary cases where needed. Check fixed compatibility contracts, non-goals, reviewer packet requirements, and the recovery boundary. The consumer's own capsule schema remains controlling. A checked planning box is not candidate-bound evidence.

Trace every controlling requirement through the draft. Mark it covered, unresolved, or explicitly deferred by the owning authority. RI exclusions, unsupported source, and a revised capsule cannot silently erase it. Include relevant manifests, workflows, feature flags, and unsupported files in this accounting even when RI maps no callable there.

If a required identity, scope grant, or execution prerequisite is missing or inconsistent, return `STOP_REPLAN` with the specific mismatch and the smallest needed controller decision. Do not repair authority by widening paths, choosing a different base, substituting an old candidate, or silently dropping a required check. A mechanical PASS authenticates only what that check actually covers; the controller still resolves semantic scope and acceptance.

Return a compact preflight record: verified capsule and repository identities, permitted next action, applicable lane and checks, unresolved gaps, and the exact source of each decision. Do not launch implementation, qualify, publish, accept, or merge unless the active request and consumer workflow authorize that step.
