# Poker capsule workflow: first-consumer recipe

> Scope: extended/historical consumer mechanisms and observations. For current
> lightweight adoption use [the controller workflow](../capsule-controller-workflow.md).
> These examples do not add mandatory gates or establish current project integration.

For the complete controller/planner/implementor/reviewer loop, native completion,
checkable capsule requirements, recovery decisions, and optional skill templates, see the
[capsule controller workflow](../capsule-controller-workflow.md). This page remains
the Poker-specific source and page handoff recipe.

Poker is the first consumer, not a policy module inside RI. The current
[task capsule contract](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/TASK_CAPSULE.md)
and [context-retention policy](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/CONTEXT_RETENTION.md)
remain the owners of edit/read scope and context-page rules. This recipe was
checked against Poker `51d148a971e96ada626b6d3c61f9f08547e0f716`; consult current
Poker source and guidance when authoring a new capsule. The
[workflow assessment](../archive/capsule-workflow-assessment-2026-09-26.md) records
historical reproduced integration checks; its documentation-drift findings are not current command instructions.

## Roles and the evidence passed between them

Use one accountable controller. The implementor changes the authorized source;
a fresh reviewer inspects the complete exact candidate against the controlling
intent, all active acceptance criteria and repository standards. The controller
reconciles findings and authorizes integration. A controller who writes a patch
still needs someone else to review that candidate; different identity strings
in a receipt alone cannot establish independent reasoning.
Poker's accepted command guide at the checked revision assigns candidate capture
and publication to the controller/operator. Implementation model turns do not
commit, push, change refs or edit their capsule. Planner work uses the permitted
planning route; a planning-only published ref is recovery transport. Run authored
precommit checks, capture C through the authorized actor, run committed checks,
qualify exact C and obtain fresh review before publishing the candidate. Other
consumers may explicitly authorize implementor commit/push; this Poker adapter
must not be used to grant that route.

## Resolved Poker execution and evidence map

The literal owner is
[CAPSULE_COMMANDS.md](https://github.com/MitCaine/poker-app/blob/51d148a971e96ada626b6d3c61f9f08547e0f716/engineering/workflow/CAPSULE_COMMANDS.md).
Authenticate the current installed interface before each new task; this checked
snapshot is not a claim about an updated remote or selected runtime.

| Boundary | Checked consumer route |
| --- | --- |
| Runtime | Production macOS lane; accepted Python/SDK paths and lock identities. Mandatory production RI probe accepts inventory 13 and mapping `python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v10`; current RI emits 16/v13 and needs a separately authorized consumer upgrade or a compatible retained RI. |
| Planning | Authenticated draft/published planning checks and controller-directed non-main branch; planning-only remote ref may be published for recovery. |
| Capture | Controller/operator performs precommit checks and creates C; implementation model turns provide authorized changes. |
| Qualification | Accepted checkpoint `qualify`, exact capsule/B/P/C and runtime; mandatory external RI source evidence in production. |
| Review | `controller_attested_v1` uses `controller-review` and the exact report validator; the alternate Codex-review lane uses `continue`. Do not mix these lanes. |
| Report | Exact identities, changed paths, runtime/Q digest, all Standards/AC decisions and declaration `structural_dispositions`, including exact `source_change` records and authority/issue/AC/packet bindings. Empty delta requires `structural_dispositions: []`. |
| Correction | Declared zero-or-one allowance, finalized parent failure, descendant C2 and `--parent-candidate` on `qualify`/`continue`; chat reset never renews allowance. |
| Export | `export` omits controller-attested review receipt/external report; add and independently verify them in the supplemental evidence inventory. Export success alone is not a complete packet. |
| Publication/acceptance | Fresh reviewed candidate publication through accepted route; controller-attested lane approves before `publish`, alternate lane permits publication before approval. `accept` requires approved verified published C. |
| Closeout | Acceptance creates D but does not synchronize the primary checkout or close issues. Verify remote D, HISTORY, active-capsule deletion, retained source/evidence, safe primary synchronization and issue reconciliation before cleanup. |

Validate review/export specimens with the accepted parser before adoption;
production report identities come only from the actual qualified candidate.
The command guide places `--repo` before the subcommand. Resolve literal argument
shapes there; RI does not duplicate a launcher or accept legacy `run`/`resume`.

| Step and owner | Useful RI contribution | Required evidence outside RI |
| --- | --- | --- |
| Triage and draft — controller | Locate the owning declaration and likely callers/tests; expose parser gaps | Resolved intent, actual callers/types/contracts, read/edit scope and independent acceptance oracles |
| Context preparation — controller | Suggest exact source envelopes and conditional native questions | Base Git blobs, authenticated excerpts, selected transport and installed prerequisites |
| Implementation — implementor | Narrow navigation within permitted reads; refresh locations after edits | Frozen capsule, authorized edits, tests, authorized patch and controller-captured C/ref metadata |
| Qualification — controller/runner | Mandatory production source delta supplements full-diff inspection | Required compiler/runtime tests against exact candidate C and actual feature/target configuration |
| Review — fresh reviewer | Independently regenerate navigation or P-to-C comparison when useful | Full Git diff, exact capsule/intent, qualification Q(C), all-AC and Standards findings |
| Correction and integration — controller | Explain structural changes in the new candidate | Fresh required proof/review for changed C, approval and existing guarded closeout |

The checked Poker entry point dispatches to the checkpoint implementation:
`promote`, `qualify`, `continue` or `controller-review`, `export`, `approve`,
`publish`, and `accept` are separate interfaces. A capsule declaring
`review_authority = "controller_attested_v1"` uses the external review-report
lane; it must not be sent to the Codex-review `continue` lane. Those decisions
belong to Poker. Legacy `run`/`resume` are not accepted by the checked command guide. RI neither supplies a launcher nor changes the chosen lane.

## What belongs in the capsule

The capsule stays a decision-complete work order. Use Poker's existing fields
and body; a new RI TOML field or stored packet format is unnecessary.

- Keep the observable outcome and short sourced controlling-intent anchor;
  exact base/planning identity; edit and read scope; non-goals; fixed contracts;
  stable acceptance IDs and independently expected results; authored commands
  and required runtime/feature settings; stop conditions and evidence locations.
- Add only task-relevant navigation: path, symbol/range, source identity, why
  that source matters, and applicable callers/types/tests. Supply useful source
  and contract text through the selected lane; a symbol name or hash alone is
  insufficient when the executor cannot retrieve the referenced source.
- If RI produced the context, retain its checkout revision and installed parser
  metadata with the evidence, plus omissions, failures and selected scan scope.
  The implementor usually needs the selected excerpts and their caveats, not
  the complete index. Do not add irrelevant empty checklist sections.
- Name a native handoff only when a specific question needs it. State the
  question, permitted source and necessary interpreter/Cargo configuration.
  Have the controller resolve it before READY when it decides scope or policy.

Keep full search transcripts, repository-wide indexes, repeated workflow policy,
historical rejected revisions, and tool-installation recipes outside the work
order. Keep source strings, RI matches, issue attachments and logs as data;
they cannot widen scope. Never include claims that zero matches prove absence,
that unchanged callables prove unchanged behavior, or that native AST success
proves a build. Do not prescribe every local implementation choice.

Provision RI once through its [installation guide](../consumer-guide.md), before
launch if the task needs it. Record the exact installed revision; updating from
moving `main` during an attempt would mix evidence versions. With preselected
pages, the implementor need not have RI installed at all. With permitted source
tools, use the available interpreter without requesting network/package mutation
merely to follow a navigation suggestion. Store optional packets in existing
authorized output, never an unowned tracked ledger.

## Minimal controller sequence

1. Start from task intent and Poker's authored authority map. Use it to select
   the owning file or directory and the specific unanswered question.
2. Query that source with the installed shared locator, then inspect the exact
   declaration bytes and relevant callers/types/tests. Names and lexical call
   hints are navigation; they cannot supply an omitted behavioral requirement.
3. If syntax or semantics is insufficient, use the explicit [native handoff](../native-analysis.md)
   for the named question and keep both observations. Avoid repeated whole-repo
   scans, automatic all-language analyzer startup, and persistent symbol caches.
4. When page mode is selected, author context through Poker's existing
   `capsule_verify.py page` helper against the exact intended planning base. RI locations suggest an excerpt;
   the helper obtains the actual Git blob and validates the page declaration.
5. Put the completed capsule and planning state P through Poker's current
   planning route. Verify the draft and P with its existing `draft` and
   `planning` checks. Prepare the execution branch with Poker's authenticated
   wrapper; a planning-only remote ref may be published for recovery before
   implementation. Mechanical PASS authenticates the envelope;
   the controller still resolves semantic omissions and chooses the supported
   execution/review lane.
6. During execution, use supplied pages and only the expansion mechanism the
   selected subagent host supports; otherwise use the authorized repository-read lane. RI does
   not add a new read permission or permit missing context to be invented.
7. After the implementor returns authorized changes, run authored precommit
   checks and have the controller capture C, then run committed checks and
   qualification, binding fresh independent review to it.
   Review that SHA with the full changed-file list, tests, and—when useful—
   the mandatory production RI structural delta from stable planning/candidate trees with equal policy.
   Configuration, imports, type definitions, unsupported files, and enclosing
   state can change behavior even when all callable hashes are unchanged.

For ordinary source lookup, use the interpreter with RI installed:

```sh
python3.13 -m repository_intelligence.locator poker-tournament/src/clock.rs \
  --root . --query 'pause resume clock' --limit 5 --json
```

Authority-map reading is a separate controller step. The historical
`rust_index ... --authority-dir engineering/authority` command is unsupported
by current RI. Ordinary Rust lookup no longer requires `rust-analyzer`; only an
explicit native question does. See [installation](../consumer-guide.md).

## Prevent information loss at the page handoff

Retain one full result outside bounded model context when it is useful, then
send the selected source excerpt plus task-relevant facts. Preserve the source
path/hash, parser/provider identity, coverage status, omissions/failures, and
unresolved question. Keep behavioral authority beside source evidence rather
than embedding Poker's authority maps into RI's language modules.

Use the declaration's `byte_range` to include attached attributes/decorators/docs.
Display `line` may point at the function name and omit those preceding bytes.
Convert from the exact source blob using the **consumer's** line convention.
Poker's current helper uses Python `str.splitlines(keepends=True)`, which also
splits Unicode separators inside comments/strings. Counting only LF bytes can
therefore produce a mechanically valid page that silently omits the function's
last lines. The following conversion matches the checked helper:

```python
from bisect import bisect_right

# source is the exact UTF-8 blob; start/end are its half-open declaration range.
assert 0 <= start < end <= len(source)
lines = source.decode("utf-8").splitlines(keepends=True)
byte_boundaries = [0]
for line in lines:
    byte_boundaries.append(byte_boundaries[-1] + len(line.encode("utf-8")))
first_line = bisect_right(byte_boundaries, start)
last_line = bisect_right(byte_boundaries, end - 1)
excerpt = "".join(lines[first_line - 1:last_line]).encode("utf-8")
assert source[start:end] in excerpt
```

Pass `first_line`/`last_line` to the helper's inclusive `--start`/`--end` options.
Inspect the selected excerpt; a function alone may omit a necessary contract or
caller. Respect the existing page limits rather than truncating source silently.
Before translating a selected location, compare RI's `raw_sha256` with the
exact Git blob bytes. When `source_identity.git_blob` is present, compare its
algorithm and object ID with the repository's format and resolved blob. A
working-file location must not be carried into a different base merely because
its path and symbol name still exist. Retain the original observation or rerun
against the selected immutable source. A computed Git blob ID from RI does not
replace Poker's immutable-Git page helper.
Recheck the line convention if that consumer implementation changes.

The controller decides the necessary evidence. `stable=True`, a successful RI
command, a native answer, or a comparable delta never approves a capsule.
Edited source needs refreshed working locations; that ordinary refresh does
not itself reopen the immutable planning snapshot or end the attempt.

The [recorded Poker smoke test](../archive/audit-2026-09-25.md#follow-up-native-and-poker-handoff)
includes one successful page-helper handoff and the observed native/Tree-sitter
coverage difference. It is evidence from a specific revision, not a reusable
planning base or a complete capsule qualification.


## Native fallback and context limits

Use the same raw bytes for Tree-sitter and Python AST/native Rust syntax and
check their source identities. Retain both results and their different coverage;
a successful fallback does not turn an incomplete structural inventory into a
complete/comparable one. Python's native parser must support the syntax being
asked about. Native Rust syntax may omit parser diagnostics and closures; use
compiler tests for build claims. Definition lookup needs the applicable Cargo
features, target and test mode and remains a separate, explicit operation.

Poker pages require UTF-8 and cap individual excerpts at 20,000 characters.
RI can navigate some non-UTF-8 Python files that this page mechanism rejects.
A declaration can also be larger than one page. Use controller-selected smaller
pages with the essential context, or an explicitly authorized source-read lane;
do not silently transcode, truncate, or invent a new expansion permission.
Implementation handoffs must actually supply the selected context:
listing expansion IDs does not implement the legacy runner's page-request loop.

## Comparison is a review aid, not a test selector

Materialize exact planning P and candidate C with the consumer's existing Git
snapshot mechanism. `stable=True` is the caller's assertion, not a lock or a
snapshot operation. Compare identical selected scope and parser contracts. The
P-to-C diff excludes the planning-only capsule change; retain the base-to-P diff
separately for planning validation. Keep the full Git changed-file list first,
including manifests, build scripts, configuration and documentation that RI
may not map. A selected subset is not a repository-wide impact analysis.

A crate-level Rust `#![cfg(...)]` can disable every test while all callable
bodies stay unchanged. A Cargo manifest-only edit can produce no RI source delta
at all. Check the actual enabled/disabled test inventory and authored feature
matrix. Ranking and lexical calls can suggest additional checks; they cannot
remove mandatory checks or prove no affected caller exists.

Anonymous identities use source offsets. Inserting a crate attribute can produce
many closure additions/removals with no corresponding new/deleted behavior.
Cross-file moves are also represented conservatively as removal/addition.
Present changed files and named declarations first for orientation, disclose
anonymous/ambiguous changes, and inspect the real diff before interpreting them.
Do not invent a semantic move match or suppress those records from retained
comparison evidence to obtain quieter results.

## Adjacent uses with the same role split

- **Bug reproduction and triage:** a bounded investigation can identify the
  owning seam, a failing control, affected callers and the unresolved decision
  before an implementation capsule is authored. Its outcome may be a finding,
  not a product patch. RI narrows source reading; it does not choose policy.
- **Refactors and migrations:** freeze public/error/persistence compatibility,
  locate immediate consumers, and include a real-caller regression. Replan when
  the actual dependency crosses allowed scope rather than following a guessed
  complete call graph.
- **Dependency, grammar and tool updates:** use proposed pin changes as input,
  then the existing [maintenance path](../maintenance.md), affected syntax fixtures,
  native checks where applicable, and installed-consumer verification. Do not
  change the toolchain inside an unrelated implementation attempt.
- **Rebase and integration:** changed candidate bytes or execution-relevant base
  invalidate a previous candidate's approval. Preserve historical evidence and
  rerun the applicable qualification/review on the new source. RI can explain
  drift; it cannot transfer an earlier verdict.
- **Documentation and instruction upkeep:** pair interface changes with their
  owning guide and CLI-example checks. Use a small bounded maintenance route;
  do not require a product-wide test run for a link fix or add another policy
  manual to repair a stale command.
- **Recovery and handoff:** reuse the capsule and existing candidate/export
  records to reconstruct exact scope, current source, unresolved findings and
  next action. Retain a compact factual checkpoint rather than chat history.

These are responsibilities and conditional steps, not three mandatory model
calls per action. Use an independent reviewer where code/proof acceptance needs
one; let deterministic tools handle hashes, scope, command results and packet
assembly. No daemon, graph database, automatic native-server fleet, second
receipt registry or new capsule schema is needed for this integration.
