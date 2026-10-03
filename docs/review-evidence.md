# Review evidence transport

Use this optional transport when repeated inventory records make a handoff large.
It retains the complete planning inventory, candidate inventory and recomputed
comparison. Repeated JSON objects and arrays are stored once and referenced by SHA-256.
No persistent index, service, compression layer or new approval authority is added.
Inventory schema 16 and mapping v13 describe the current Markdown semantics;
the transport has its own
`review_bundle_schema_version: 1`. Existing consumer contracts require an explicit
adapter/prerequisite before adopting it. A retained 13/v10 consumer must continue
using its compatible runtime until that change is authorized.

## Commands

Supply stable, materialized source through the consumer's existing acquisition
route. RI's stable assertion does not authenticate Git membership.

```sh
python -m repository_intelligence.inventory compare P_SOURCE C_SOURCE \
  --assert-stable-materialization --review-bundle-json > review-bundle.json
python -m repository_intelligence.review_bundle verify review-bundle.json
python -m repository_intelligence.review_bundle index review-bundle.json
python -m repository_intelligence.review_bundle read review-bundle.json \
  --document candidate --path '["files",0,"declarations",0]'
```

Compare retains its existing exit codes: 0 comparable, 2 incomplete, 3
incompatible. Bundle verification checks transport integrity; exit 0 is **not**
a completeness or approval verdict. Inspect its returned comparison status.
The index uses `review_index_version: 2` (separate from bundle schema 1).
It includes counts and at most twenty entries per change kind and coverage/reason
list, with explicit truncation flags and document-path locators. Scope and parser
contracts are locators rather than repeated metadata. Consumers of the older index
shape must explicitly adopt this projection; the retained bundle and inventory
contracts are unchanged. Full records remain accessible by document path.
Each side's `retained_inventory_sha256` hashes its complete canonical inventory,
including unsupported paths and exclusion/failure reasons. The existing
`inventory_digest` covers supported source identities and scan policy only.
Neither digest detects content changes at an unchanged unsupported path: retain
Git/source evidence for those bytes.
Selective reads mechanically validate the entire bundle before selecting data;
the model need not reconstruct pages or repeat every structural record.

Digests cover canonical JSON data, not original JSON whitespace. Each document
reconstructs exactly to that data. POSIX non-UTF-8 filename bytes are retained
through Python filesystem surrogate escapes, serialized as JSON `\udcXX`
escapes. Decoding and filesystem encoding recover the original path bytes;
valid Unicode canonical bytes are unchanged. The verifier rejects missing, extra, cyclic,
overlapping or altered references and recomputes the comparison from both
inventories. These checks prove internal consistency, not source authenticity.
Overlap validation uses component-prefix lookup, preserving ancestor/descendant
rejection in either order without comparing every path to every earlier path.
Consumers still bind P/C, raw source hashes, full Git diff and qualification.
Recomputed comparisons must match canonical JSON bytes, including scalar types:
`0`, `false` and `0.0` are distinct. The 80-level nesting limit is checked on both
the wire envelope and the expanded documents/records; references cannot evade it.
Limits are 64 MB stored and a conservative 128 MB decoded allocation budget,
including reconstructed references. They are RI transport limits, not permission
to increase a consumer's evidence budget. There is no external-file lookup.

Schema 1 already permits array-valued records; the current producer also factors
repeated arrays. Record selection returns the verifier's authenticated resolved
value (including scalar records accepted from external producers), copied for the
caller. Consumers must test their actual readers before selecting the expanded
producer; RI does not automatically upgrade retained consumer runtimes. The bundle
CLI performs one construction comparison and one independent verification
comparison, retaining the latter's status for its exit code.

## Feasibility and handoff gate

This section applies only to projects that explicitly adopted this bundle/export
and report-import mechanism. It adds no gate to ordinary lightweight issue work;
direct source, full diffs and real logs remain sufficient there. The report schema
and transport limits below are selected consumer mechanisms, not universal RI
workflow requirements.

Before final READY/P, measure the actual producer output for the planned scope,
including a large indivisible file. Distinguish stored bytes, decoded bytes and
reviewer context. Source size alone does not predict structural evidence size.
Choose the simplest consumer-authorized route that preserves complete evidence:
a bounded budget correction or deduplication may be enough. Compression and
paging are optional transport choices, not mandatory new workflow stages.

Before allocating the product reviewer, run a synthetic round trip through the
accepted export, read and report-import validators. Confirm raw qualification
logs, applicable Standards, ACs, full diff and source locators are available.
Prepare the report schema/template so the reviewer can write a terminal verdict
rather than repeatedly print inventories. A bounded summary is orientation;
missing mandatory evidence or dispositions still blocks approval. Changing a
consumer's per-declaration disposition requirement needs its own authorization.

Keep source read-only and provide the consumer-supported report output location
separately. Deliver a small terminal status with candidate, report path and digest
through native completion or the queue. While awaiting completion, the controller
sleeps unless there is concrete independent work; it does not invent activity.

## Trial lessons and consumer boundaries

The Poker and Nutrition trials exposed consumer integration issues that this RI
transport alone cannot repair:

- Validate launch wrappers before publishing final planning state, or explicitly
  record recoverable preparation stages; publishing a branch is not readiness.
- Rehearse exact commands with final logs, environment and sandbox. A runtime
  startup probe or host-only test does not prove the full evidence command works.
- Put toolchain scratch outside the execution checkout and check untracked files
  before capture. Preserve unrelated work and failed-attempt evidence.
- Make retained source/history objects retrievable in a fresh checkout before
  branch cleanup. A local clone's objects are not a portable evidence route.
- Supply current role instructions explicitly when installed skills lag. Keep
  runtime compatibility separate from skill freshness.
- Send prerequisite code repairs to an authorized implementor. Controller
  inspection and evidence assembly do not grant implementation authority.

The [controller workflow](capsule-controller-workflow.md) owns the sequence.
These are checks of existing gates, not additional universal approval rounds.
Production consumer adoption and guarded closeout must be tested separately;
RI-side unit tests do not establish Work-host wake-up or consumer acceptance.

## Measured replay

The [offline Poker/Nutrition replay](archive/review-evidence-replay-2026-09-30.md) demonstrated storage savings, but no faster review. Replacing only primary inventories does not fix aggregate caps when consumers retain duplicate raw views or embed RI again in qualification receipts. Prefer removing redundant views through an authorized consumer contract change before requiring additional transport machinery.
