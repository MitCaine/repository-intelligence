# Start an issue in an established project

**Read the complete directed orientation material before acting.** Before task
decisions, edits or role dispatch, read this procedure, the project-root `docs/local_project_map.md`,
the complete live issue and its required linked specifications/decisions, and
applicable project instructions. Follow references necessary to understand them;
do not replace unread requirements with summaries or assumptions. Resolve
contradictions and identify missing information before dependent work proceeds.
This is bounded task orientation, not a requirement to read the whole repository.

This is the complete daily execution entrypoint for a controller in a project
with an adopted RI map. Read this page, `docs/local_project_map.md`, and the live issue. Read
relevant source and standards as needed. You do not need RI architecture, parser
contracts, adoption history or the setup guide to execute an ordinary issue.

The map always lives at `docs/local_project_map.md` relative to the consumer
repository root. Its filename and location are the same in every adopted project.
The project README/AGENTS entrypoint points there. Do not search for another map
and silently substitute it. If it is missing, report the missing adoption input;
authorize/create the bounded map before issue dispatch, rather than guessing.

## Intake

- Check the map's selected instruction identity, compatible runtime, role/model
  settings, commands, standards and permitted Git/issue actions. Use the adopted
  version throughout the attempt; do not silently select new instructions,
  reinstall skills or upgrade the runtime. Resolve a conflicting map first.
- Authenticate the live issue, current base/branch and checkout. Preserve unrelated
  edits. Check for an active task/checkpoint before starting a duplicate attempt.
- Resolve missing product decisions; do not invent requirements or parameters.
  Only a concrete changed setup input or failed capability needs setup diagnosis.

## Capsule format

RI owns this shared capsule format for every adopting project. Use one ordinary
Markdown task file with these headings:

- **Objective:** live issue and original required specifications/decisions.
- **Source and scope:** base revision, task branch, authorized edit paths and
  affected current documentation; preserve unrelated work.
- **Acceptance:** individual checkboxes stating observable outcomes and each
  outcome's concrete test or inspectable evidence, including documentation.
- **Checks:** literal required commands, intended environment and results to retain.
- **Prerequisites:** known dependencies, unresolved decisions, and any genuinely
  post-installation obligation with its satisfaction method.
- **Handoff and closeout:** authorized actor/actions, exact returned source/results,
  pending work and verification before issue closure and safe branch cleanup.

Keep these headings and their meaning the same across projects. The local map
supplies project values, commands, standards, permissions and the capsule storage
location; it points to this section in the selected RI instructions. Projects may
add necessary fields but must not replace the shared structure or duplicate its
instructions in a competing local template. No extra schema or historical runner
template is implied. Preserve frozen historical task formats without applying
them to new tasks.

## Execute serially

```text
Controller -> capsule builder -> controller checks plan
           -> implementor    -> controller checks candidate/results
           -> reviewer       -> controller integrates and closes
                        findings -> bounded correction -> review
```

Run one assignment at a time, with fresh contexts by default. Each role receives
this selected procedure, its bounded task, relevant map/standards/source locations
and actual evidence it needs. No automatic full RI documentation read is required.

Before planner dispatch, supply the builder with the original issue and required
orientation sources, their selected identities/locations, confirmed requirements
and unresolved questions. A controller summary alone is insufficient. Each role
reads its directed orientation before acting; inaccessible required material is
a reported gap, not permission to guess.

Before builder dispatch, identify the branch-creation actor from the map. If the
controller owns Git, it creates the dedicated branch and supplies its identity to
the builder. Otherwise explicitly grant only the needed branch action to the
builder. The builder cannot infer Git permission from its role or these instructions.

1. **Capsule builder:** work on the supplied dedicated task branch (or create it
   only under the explicit branch grant), and use the
   [shared RI capsule format above](#capsule-format). Include issue/objective, base/branch, authorized
   paths, independently checkable acceptance criteria, required commands,
   known prerequisites and affected current docs/examples/maps/links. Require
   stale wording to be corrected, or justify why documentation is unaffected.
   Identify genuinely post-installation checks and how to satisfy them.
2. **Controller:** check the returned plan against the original orientation, issue
   and relevant source, including scope, criteria, documentation and proof routes.
   Resolve scope/specification gaps and confirm the next role's actual command
   environment. Rehearse only known fragile commands. Independent scope challenge
   is conditional, not an automatic fourth assignment.
3. **Implementor:** make only authorized changes, including affected docs, and run
   relevant checks. Return source/branch identity, changes, results/skips and gaps.
   Commit/push only when the map grants that action. Keep useful work for corrections.
4. **Controller:** inspect the full diff, scope, documentation and criterion evidence;
   capture the exact candidate when assigned that responsibility. Supply the
   reviewer with that source, the full diff, capsule, standards and actual test/log
   evidence.
5. **Independent reviewer:** remain read-only and review the full change, not just
   RI declarations or a summary; return concise evidence-backed
   dispositions for every criterion and applicable standard. Check docs too.
   Missing evidence already due cannot pass. For post-installation obligations,
   assess the implementation/check plan now; installed proof remains due at closeout.
6. **Controller:** return in-scope findings to an implementor, then obtain affected
   checks and independent review. Approval must cover the actual integrated result.
   Use authorized integration, verify it and any pending installed checks, record
   necessary evidence, close only when all outcomes pass, and safely delete the
   verified merged branch. Preserve unrelated work and unmerged recovery evidence.

RI is navigation/comparison support. Direct source, full diffs and ordinary logs
suffice; RI gaps do not prove absence. No special runner, exporter, per-declaration
verdict or new mandatory record is required. Already-satisfied work can receive
independent no-change review and authorized closeout without an artificial commit.

## Wait, recover and resume

Before dispatch, select the terminal delivery route for the exact controller.
For native subagents, default to the host's supported event-based blocking wait.
Native result delivery to the parent and starting a new turn in an idle parent
are separate capabilities. Built-in subagent support does not by itself establish
idle wake-up. Keep the controller turn in the blocking wait; do not end it on an
assumption that a terminal result will start another turn. End the turn only when
idle wake-up has been verified for the selected route.

Queue is for external jobs lacking a reliable completion channel, or another
route with a supported watcher and verified wake-up; it is not the default for
native subagents. Before relying on it, verify that queue delivery actually wakes
the intended controller on this host. A small harmless delivery probe must reach
the exact idle controller and be consumed without a human nudge; CLI acceptance
alone is insufficient. Reuse that observation for the same host/controller route
until the route changes or delivery fails. Do not add duplicate notifications to
a verified native route. If neither route has verified idle wake-up, keep the
supported bounded blocking wait and state the limitation. Do not restart a job
to attach a watcher or claim an untested native-subagent watcher is supported.

Do not repeatedly poll or invent work to avoid waiting. Choose task-appropriate
host-supported deadlines.

After dispatch, wait for the terminal handoff. Reading the active workspace,
source diff, logs or interim test results to track progress is monitoring too;
it is not an alternative to status polling. Do not repeatedly restate the
contract or produce interim acceptance judgments while a role is working.
Controller candidate/scope/evidence verification begins after terminal delivery.
Unsolicited progress may be received without starting a monitoring loop.

Early intervention is limited to an actionable blocker/clarification delivered
by the role, a concrete safety concern, failed completion delivery or a direct
owner status request. Use only the reads necessary for that intervention, then
return to waiting. Independent preparation must be a specific already-authorized
activity that does not inspect or depend on the active role's unfinished work;
do it once, not as a recurring excuse to stay active. Supported wait resumptions
at host time limits are allowed; they do not authorize extra progress checks.

At a blocker, hold consequential work and do one bounded authorized read-only
sweep to consolidate real failures and unknowns. Routine clarification, diagnosis
and in-scope correction need no repeated human approval. STOP_REPLAN is a last
resort for an established blocker, not opening progress. Preserve terminal stops;
a diagnostic-only follow-up may explain one but cannot resume it. Request new
authority only for uncovered scope, permission, disclosure or reserved actions.

Corrections start from authenticated recovery source, not necessarily the original
planning HEAD. Preserve outcome identities; reused evidence is not newly executed.
Changed integration source needs affected checks/review. Lost delivery or a timeout
requires checking actual completion/cleanup before repeating any operation.

Keep phase, selected instructions, source, active job, results, pending obligations
and next action in the existing checkpoint across compaction. Authenticate it on
resume; do not duplicate dispatch. If fresh agents cannot be created or freed,
last-resort idle-context reuse is permitted with a complete handoff. The candidate
implementor/author must never be its reviewer. If independence is unavailable,
report that blocker. No allowance reset or self-approval is permitted.
