# Capsule and RI workflow assessment — 26 September 2026

Assessment source: Poker planning commit
[`b84eacf9fd4450bc1a3bfe142c21d784c0b251bc`](https://github.com/MitCaine/poker-app/commit/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc),
RI `4d69f0e595acb71e31886cc9745e3775abeb7eb7`, plus the guide and two
regressions accompanying this report. Poker's working tree moved independently
during this assessment; its scripts were frozen before fixture testing. No
Poker source, capsule, ref or review receipt was changed by this assessment.
This is an integration assessment, not approval of a product candidate.

The current RI usage owner is the [capsule integration guide](../poker-capsule-workflow.md).
This dated report records findings and evidence; it is not another capsule contract.

## Findings and disposition

| Finding | Evidence and implication | Disposition |
| --- | --- | --- |
| Poker's RI setup instructions are stale | Its consumer guide recommends `rust_index ... --authority-dir`, which current RI rejects with exit 2; it describes the shared locator as Rust/Python only. Source-path injection also does not install RI's required grammar dependencies. | RI's guide now points at installed shared navigation and separate authored authority. Repair Poker's consumer guide through a bounded documentation task. |
| Workflow prose lags the accepted checkpoint implementation | `capsule_run.py` dispatches to `entrypoint.py`; `run --help` rejects `run`. CAPSULE_COMMANDS still gives legacy `run`, `resume`, and positional `accept` examples. FUTURE_WORKFLOW still labels checkpoint work prospective. | Reconcile the command owner, routing/evidence descriptions and adoption status against accepted code. Link other guides to that owner. Do not execute legacy prose through the new entry point or revive historical work from its old status. |
| Context authoring fits RI without another schema | The real page/draft/planning/candidate helpers accepted RI-selected exact source ranges in an isolated Git fixture; stale blobs and unowned candidate paths failed. | Keep the existing seven-field pages and consumer scope checks. RI supplies source facts; the controller supplies behavior and authority. |
| Context transports have different capabilities | Legacy context pages support declared expansions; direct implementation launch does not implement that handler. UTF-8 and character limits belong to the consumer page loader. | Supply the needed material before launch or choose an explicitly authorized local read route. Do not make a capsule depend on a missing expansion handler. |
| Callable deltas are insufficient proof for feature/test work | A real `rustc --test` fixture listed one test before a crate guard, zero with the feature disabled, and one enabled. RI reported one changed file with one unchanged callable. A manifest-only edit produced no RI source change. | Retain full Git diff and required feature/runtime tests. Added two permanent RI regressions documenting these limits. |
| Anonymous deltas can distract reviewers | The actual 34-file Poker candidate produced 106 closure additions and 106 removals because offsets changed; its named moved test also appeared as removal/addition. | Guide now explains conservative identity and recommends changed files/named declarations first, retaining all comparison records. No heuristic move matching or weakened identity contract was added. |

The existing capsule contract already calls for a sourced controlling-intent
anchor, decision-complete contracts, independent acceptance oracles, exact
source, bounded edits and a fresh candidate review. These are the right core.
The improvement is making creation and operation follow those requirements
consistently, with current navigation and current launcher instructions.

## Source and workflow observations

The inspected capsule was `PA-TEST-FEATURE-GATES-001` revision 3, with 34 owned
paths and `review_authority = "controller_attested_v1"`. Its planning envelope
received read-only `MECHANICAL_PASS`. It used the repository-read lane with no
context pages. Its task-local instruction correctly preferred top-of-file
feature attributes over needless function navigation. RI need not run for every
capsule merely because it is available.

The inspected checkpoint implementation separates candidate inspection,
qualification and review. Controller-attested review requires its declared
lane, exact candidate/capsule/runtime/qualification bindings, complete Standards
and acceptance results, a distinct implementor/reviewer identity, and no claimed
post-review provider effects. These checks do not prove that two differently
named identities represent independent work; the accountable controller still
owns actual reviewer independence and intent/semantic assessment.

During the assessment, the separate Poker task accepted
[`aad23ca1ef940d81024f4c2eb075ad936d48c4cd`](https://github.com/MitCaine/poker-app/commit/aad23ca1ef940d81024f4c2eb075ad936d48c4cd)
and closed it in
[`4e56f69348f46734fbd65614e0101076341e9f32`](https://github.com/MitCaine/poker-app/commit/4e56f69348f46734fbd65614e0101076341e9f32).
A final remote refresh observed `f43a39d38eda85206ae1f945c4bb4e4672acbfb3`,
which adds the next annotation capsule only; issue #424 was closed.
The change from the inspected planning object through closeout touched that task's 34 test files,
its active capsule and HISTORY; the workflow/RI guide findings above remained.
This report does not rerun or attest that task's product qualification.

## Exercised integration

On macOS ARM64, Python 3.13.15, with RI's unchanged dependency pins:

- RI's full source/native/offline installed-consumer suite, including the two
  added regression tests: **241 passed**, zero skips. Documentation checks
  resolved 88 local links/anchors and parsed six Python examples; whitespace
  checks passed.
- Poker's authoring/verifier suite: **20 passed**, zero skips.
- Frozen Poker's qualification/controller-review suite: **20 passed**, zero skips,
  including stale/malformed reports, review-axis contradictions, wrong review
  lane, failed proof, reviewer identity and approval-before-publication cases.
  These are fixture tests, not a live model review or production acceptance.
- A temporary Git fixture ran RI navigation → exact-byte-to-page conversion →
  page authentication → draft validation → capsule-only planning commit → owned
  candidate validation. A Unicode separator before a decorated Python function
  correctly selected consumer lines 3–5 and the same Git blob. A stale blob and
  an unowned candidate edit were rejected; one body edit yielded one modified
  declaration. The separate current checkpoint candidate inspector also accepted
  the owned candidate's exact path set.
- Valid Latin-1 Python was usable source for RI but rejected by Poker's UTF-8
  page loader; an oversized whole-file excerpt was rejected at 20,000 characters.
  A separate CRLF fixture attempt reached Git's independent whitespace gate,
  which rejected CR-at-EOL under the fixture's default policy; the successful
  end-to-end candidate fixture used LF. No production guard was relaxed.
- Native `rustc --test` independently demonstrated test suppression by a crate
  feature guard: **1 / 0 / 1** listed tests before / disabled / enabled, despite
  the unchanged callable body. The permanent RI tests preserve the file change
  and explicitly document manifest-only changes outside source inventory scope.
- Exact P-to-C inspection of the independently completed Poker task passed
  candidate scope. RI compared immutable materializations of **only the 34 changed
  source paths**, with both inventories complete: 34 modified files; 620 unchanged
  declarations; four modified declarations; 107 additions and 107 removals. Each
  add/remove side consists of 106 closures and one named test moved across files.
  This is not a full impact graph, semantic move proof or test-execution inventory.

Temporary probe scripts/logs were kept under
`/private/tmp/ri-capsule-assessment-20260926`; that location is diagnostic and not
permanent workflow authority. No live model launch, approve/publish/accept call,
package upgrade or full Poker product qualification was performed here.

## Recommended next adoption step

Repair Poker's RI consumer guide and the canonical checkpoint command/routing
instructions together as a bounded documentation task. Verify every shown CLI
shape against the accepted parser, preserve unique policy and historical evidence,
and make future/adoption pages distinguish accepted behavior from remaining work.
Do not alter an already frozen capsule to retrofit these instructions.

Then use one ordinary capsule as a controller-owned comparison: keep requirements,
source, model/effort and mandatory proof fixed; record selected context size,
context requests, avoidable discovery, first-pass findings and total controller /
implementor / reviewer effort. Include a failure/caller or feature case so fewer
reads cannot be mistaken for better correctness. Existing task artifacts suffice;
a new benchmark registry, daemon or more standing agents is unnecessary.

## Primary-source research for adjacent steps

These sources support the recommendations in the current integration guide;
they do not certify this repository's implementation or an optimal capsule size.

- [Git diff](https://git-scm.com/docs/git-diff) distinguishes endpoint, working/index
  and merge-base comparisons. Preserve the complete exact-source diff alongside
  RI's language-selected comparison.
- [Tree-sitter parsing](https://tree-sitter.github.io/tree-sitter/using-parsers/2-basic-parsing.html)
  and [query syntax](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html)
  describe syntax recovery including ERROR and MISSING. Navigation must disclose
  incomplete syntax instead of turning missing matches into absence claims.
- [rust-analyzer architecture](https://rust-analyzer.github.io/book/contributing/architecture.html)
  separates syntax and semantics. Native syntax fallback does not replace build
  qualification or establish exhaustive call/dependency coverage.
- Google's review guidance on [small changes](https://google.github.io/eng-practices/review/developer/small-cls.html),
  [tests and context](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
  supports cohesive scope, independently meaningful tests and review of actual
  changed code. It does not prove that more model turns improve results.
- [GitHub merge-queue behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
  illustrates testing integrated source against the current target. Requalify
  a changed candidate/base through Poker's existing process; adopting a queue
  service is not required.
- [Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
  supports the existing update proposals. Use them as inputs to bounded maintenance
  and reviewed proof, not permission to change an in-flight task's environment.

## Repository evidence at the inspected revision

- [Capsule contract](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/engineering/workflow/TASK_CAPSULE.md)
  and [template](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/engineering/capsules/TEMPLATE.md).
- [RI consumer guide](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/engineering/tooling/repository-intelligence-consumer.md),
  [command guide](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/engineering/workflow/CAPSULE_COMMANDS.md)
  and [future-workflow guide](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/engineering/workflow/FUTURE_WORKFLOW.md).
- [Default entry point](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/scripts/capsule_run.py),
  [checkpoint interface](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/scripts/capsule_engine/entrypoint.py),
  [review receipts](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/scripts/capsule_engine/review_receipt.py)
  and [context loader](https://github.com/MitCaine/poker-app/blob/b84eacf9fd4450bc1a3bfe142c21d784c0b251bc/scripts/capsule_engine/context.py).
