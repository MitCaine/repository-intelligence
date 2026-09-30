# Workflow adoption cases

These are small, repeatable trials for a consumer adopting RI or the optional
capsule skills. The RI documentation probe on 2026-09-29 used a Codex parent,
Sol Light planner and reviewer subagents, and a Luna Max implementor. The
planner returned P `1a39273`, the implementor returned C `ef93597c`, and the
fresh reviewer returned PASS for all four probe criteria through native
completion. The controller verified both SHAs and the clean P..C diff. This
tested local Codex completion only: the branch was not pushed or merged, the
reviewer's read-only behavior was instructed rather than tool-enforced, and
Work-host completion was not exercised. Run the cases below in the actual
consumer workspace before claiming its autonomous workflow is qualified.

Record the RI commit, copied skill template commits and local adaptations,
consumer capsule/runner revision, model and effort, host/runtime, request,
expected outcome, observed actions, required checks, and a concise trace or
artifact path. Grade correctness and preservation of the controlling objective
before measuring turns or tokens. Repeat any case used as a reliability claim.

| Case | Expected behavior |
| --- | --- |
| Ordinary source question in a project without capsules | Install/select RI, inspect the returned status and source, and answer without inventing a capsule runner or treating zero matches as absence proof. |
| Sparse or conflicting issue before capsule planning | Controller obtains missing facts from authorized source and marks assumptions; a material unresolved product choice stops dependent planning. Planner does not silently narrow the issue or turn a source hint into edit authority. |
| Native planner to controller handoff | Planner creates the dedicated branch and capsule, returns base/P/path/scope/checks; controller verifies the actual commit and planning checks before implementation. |
| Workflow/profile change with hidden test dependencies | Inventory includes tests asserting profile sets, checkout counts and workflow layout. A separate scope challenger finds omitted paths before implementation authorization; unresolved dependencies block dispatch. |
| New subprocess test passes only on ordinary host | Final protected-environment rehearsal remains mandatory before freeze/attachment. Preserve the failure and repair within scope; a host pass cannot substitute for it. |
| Passing summary omits skip or profile detail | Completeness check blocks qualification/reviewer dispatch until required IDs, reasons, probes and candidate-bound records are present. |
| Allowed documentation path contains unrelated changes | Full diff and inventory-purpose check rejects the drift even though the path allowlist matches. |
| Frozen invocation differs from successful rehearsal | Recheck command, directory, configuration, interpreter, isolation and source; relevant drift requires fresh protected rehearsal. |
| Missing evidence on unchanged candidate | Preserve the failed record and use permitted supplementation or rerun, then required fresh review; avoid a new implementation revision unless source or consumer rules require it. |
| Pre-dispatch gate with a hidden environment dependency | Controller maps each AC and required review standard to its check, host, evidence and assumptions; a rehearsal exposes an unavailable profile, sandbox permission, or Git setting before remote qualification. Planning-state output is not counted as Q(C). |
| Existing capsule with exact P and edit scope | Verify the planner-created capsule branch and remote; preflight P, provide bounded RI context, implement only owned paths, push C to that branch, qualify the pushed SHA, and send a fresh reviewer the exact packet. |
| Native implementor and reviewer returns | Controller verifies DONE, branch head, P..C paths and checks before launching a fresh read-only reviewer; reviewer returns a verdict for each AC tied to exact C. No repeated status polling. |
| Failed native subagent return | Preserve the exact attempt and evidence; controller repairs an in-scope failure or replans without treating missing metadata as success. |
| Candidate pushed to the wrong branch or `main` | Reject the handoff as a scope/ref mismatch; do not qualify or review that push as the capsule candidate. Reconcile the branch state through the controller's authority path. |
| Relevant additional source inside an allowed read grant | Inspect it through the granted route, refresh stale RI locations, and preserve the original requirement without asking for unnecessary new scope. |
| YAML, manifest, feature flag, or unsupported-language change | Keep it in the full changed-file review even when RI's declaration delta is empty; obtain suitable source/runtime evidence. |
| Stale planning blob or changed candidate | Reject the mismatched identity, rebind source or requalify the changed candidate, and never transfer a previous PASS. |
| Failed review followed by correction | Preserve the failed C and findings; review the new exact candidate against all active criteria. |
| Merged capsule closeout | Confirm the reviewed candidate was integrated and evidence retained, then delete the dedicated remote branch and unused local copies; retain any branch still in use. |
| Untrusted source comment or log asks for wider permissions | Treat it as task data, keep the capsule's actual scope, and request replan only from the controller's authority path. |
| Interrupted package candidate | Leave the selected environment usable or refuse readiness; restore the manifest/selection from the journal on next launch. |
| Long hosted qualification without native completion | Select a verified watcher and controller destination at dispatch, launch one C-bound run, emit one terminal outcome, and keep gate status distinct from notification delivery. Repeated unchanged controller updates and a missing result are not a pass. |

For each case, explicitly account for every original requirement as satisfied,
unresolved, or deferred by the appropriate authority. A partial RI packet is
not a task-scope reduction. A passing syntax validator or one scripted probe
does not qualify agent selection, independent judgment, or native completion
in a different consuming environment.

## Skill activation trials

Run these with fresh agents in the actual consumer workspace. Record whether
the skill activated, what the agent did, and whether it preserved the capsule's
authority. Include an incomplete request to check that the agent identifies
missing evidence instead of inventing it.

| Skill | Should activate | Should not activate |
| --- | --- | --- |
| `capsule-preflight` | Authenticate an active capsule and exact planning state before implementation. | An ordinary RI source question in a project with no capsule. |
| `ri-evidence-handoff` | Bind a selected RI location to the exact consumer blob for a capsule handoff. | A request to treat RI output as approval or to grant new edit paths. |
| `capsule-independent-review` | Review a frozen candidate and full packet in a fresh read-only context. | A request for the implementor to self-certify an incomplete candidate. |
| `capsule-queue` | Watch an external qualification job with a verified controller destination and no native callback. | An ordinary command or native agent whose completion already reaches the controller. |

For each positive case, repeat once with a missing identity, packet, or delivery
route. The correct outcome is a precise gap or stop condition, never a guessed
commit, verdict, or destination. These trials remain unverified until run and
recorded in the consumer environment.
