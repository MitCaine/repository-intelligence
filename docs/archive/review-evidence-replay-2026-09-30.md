# Evidence handoff replay — 2026-09-30

This is a local offline experiment, not consumer qualification or acceptance.
It replays retained Poker #250 and Nutrition #246 candidates without changing
either consumer, importing a review receipt, or rerunning native qualification.

## Source and method

| Case | Planning P | Candidate C |
| --- | --- | --- |
| Poker #250 | `d9a9bda480b4e8131438c89ffbf6e1871f64f7be` | `b623da24a6ef007abfbd4b9ee9201059c13e4511` |
| Nutrition #246 | `eee171d11fd95d0696198883b899c722490bed64` | `be9ae5505150576c1d0ceb0ac626f889f573b4fe` |

Changed files and standards were read from exact Git objects into disposable
scratch. Structural capture selects the same Python/Rust changed paths as the
retained consumers; Markdown and workflow files remain available through source
and full diff, rather than silently expanding this experiment's selected scope.
The current RI reader produced both arms' inventories from identical bytes.
Nutrition's retained legacy inventories and comparison were also independently
packed and reconstructed exactly. This transport test does not upgrade a
consumer's runtime or approve legacy execution under current RI.

The old arm gets its existing compact comparison; the new arm gets the bounded
index and verified selective reads. Both arms retain full source, full diff,
capsule, standards and available qualification evidence. Both use the same
AC/Standards report requirements, without manual per-declaration dispositions.
This isolates transport; it does not establish equivalence to a consumer contract
that requires those dispositions. Review contexts are separate and use the same
inherited model/effort. Read boundaries are instructions, not enforced isolation.

An instrumented local helper logs successful accesses, emitted bytes and read
latency. Tool-call counts and approximate reviewer wall time are self-reported.
Five fresh Python processes measure each mechanical operation; times include
JSON loading and reconstruction but exclude interpreter startup/imports. Peak
RSS is process-wide Darwin RSS. No reviewer output is imported into a consumer.

## Mechanical results

| Measurement | Poker | Nutrition |
| --- | ---: | ---: |
| Expanded canonical three-document JSON | 441,482 bytes | 1,018,394 bytes |
| Deduplicated bundle | 250,163 bytes | 503,155 bytes |
| Reduction | 43.3% | 50.6% |
| Existing compact navigation | 58,847 bytes | 59,933 bytes |
| New bounded navigation | 16,623 bytes | 23,595 bytes |
| Median bundle construction | 41 ms | 92 ms |
| Median bundle verification | 17 ms | 43 ms |
| Median verified selected read | 16 ms | 43 ms |
| Old selected read, without reference verification | 1.4 ms | 2.8 ms |
| Peak RSS during bundle verification | 33.8 MB | 37.0 MB |
| Peak RSS during old parse/comparison check | 33.3 MB | 36.2 MB |

Both reconstructed documents equal their expanded inputs. Ten Poker and twenty
Nutrition source snapshots match their Git-derived hashes. Current inventories
contain 18/183 Poker and 214/238 Nutrition declarations at P/C. Nutrition's
retained/current declaration names and exact byte ranges match. The existing
controller test is 107,363 bytes with 193 mapped declarations.

The retained Nutrition legacy three-document input is 1,018,142 canonical bytes;
its exact reconstruction bundle is 503,293 bytes, and its comparison equals the
retained comparison. Small differences from the current rescan are contract
metadata, not missing source or declarations. Eight focused transport tests pass,
including corruption, missing/extra references, cycles, duplicate paths, bounds,
incomplete/incompatible status retention and CLI round trip.

## What the original cap actually counts

Nutrition retains twelve artifacts totaling 2,623,001 bytes. `raw.json` alone is
1,134,161 bytes and embeds exactly the planning, candidate, comparison and compact
views also retained as four standalone files. Replacing only the three primary
files with the legacy bundle leaves **2,108,189 bytes**, still above the 2 MB cap.
Thus the new RI bundle alone does not solve the installed consumer contract.

Retaining one copy of those views rather than the redundant raw capture would
leave 1,488,840 bytes even before RI deduplication. This is a sizing observation,
not permission to delete a required artifact: any consumer adoption must preserve
complete reconstruction, provenance, original digest/receipt requirements and
its accepted report-import contract. A bounded budget correction is another
simple consumer-authorized option. Paging/compression is not intrinsically needed.

Poker's qualification receipt is about 1.38 MB and embeds RI evidence again.
A smaller standalone bundle does not automatically shrink that receipt. Avoid
printing whole receipts when a reviewer needs command results or source bindings.

## Reviewer replay

The initial six-minute stages used 46 old-arm and 35 new-arm successful helper
reads, emitting 3,502,093 and 2,260,670 bytes respectively. Navigation accounts
for 118,780 versus 40,218 bytes. Much of the remaining difference came from
reviewer choices to reread qualification JSON, not the transport alone.
Old/new first-stage wall times were approximately 340/360 seconds, with 10/14
self-reported tool calls (the new count includes a coordination message).
**These results do not demonstrate faster review.**

Both reviewers identified Poker AC-01 proof gaps and the AC-02 street-only factor
cancelling during normalization. The old reviewer additionally flagged replay of
a folded opponent missing from the live range map; the new reviewer failed AC-04
for missing production-boundary fallback proof. These are source-inspection
findings on retained C, not test-confirmed defects or new consumer verdicts.
Both kept Nutrition hosted qualification and installed canaries unresolved.

Several broad reads were truncated in both arms. The experiment added a generic
JSON selector equally to both arms to avoid dumping whole qualification receipts.
Initial first stages left full diff/Standards coverage incomplete; both reviewers
were asked to finish those reads separately. A small index does not make an
unbounded whole-file selection safe or prove full review coverage automatically.

## Interpretation

Storage and navigation savings are demonstrated. Faster review and a complete
production guarded workflow are not. Prefer removing duplicate consumer views,
small command/log locators and a concise terminal report before introducing more
transport machinery. Automated completeness checks can cover every retained
record while the reviewer assesses actual behavior, ACs and Standards. Changing
mandatory per-declaration reporting remains a separate consumer decision.

Raw measurements, scratch snapshots, access logs and reviewer reports are local
under `/private/tmp/ri-evidence-replay`; they are disposable trial data. This small
record preserves the source identities, method, outcomes and limitations.

### Completed follow-up coverage

Both reviewers finished the supplied full diff and named Standards after the
initial time box. The old arm added approximately 240 seconds and eight tool
calls; the new arm added approximately 272 seconds and nine calls. Combined
self-reported totals are about **580/632 seconds and 18/23 calls** (old/new).
Both final reports fail Poker AC-01 through AC-04 on behavior or required-fixture
proof, and preserve Nutrition's absent protected/remote/installed proof as
unresolved. Poker's supplied exact-C qualification records/logs and Nutrition's
ancillary literal launcher results were inspected. Missing original issue bodies
and live acceptance authority remain explicit evidence gaps; these trial verdicts
cannot be used as production acceptance receipts.

The new transport did not reduce elapsed time or tool calls in this sample.
Its smaller orientation output is real, but reviewer choices, broad selections,
output truncation and incomplete packet orientation dominated the run. Provide
small named qualification/log locators and clearly enumerated input files; do
not expect deduplication alone to solve reviewer behavior. All 84 snapshot input
files remained unchanged after both reviews. The two final reports are local
`old-review-final.md` and `new-review-final.md` in the scratch directory.

Final successful helper access counts were 90 old / 86 new, emitting 4,116,488 /
2,843,052 bytes. Logged helper operation time was 0.119 / 0.213 seconds, excluding
interpreter startup. Failed invocations do not enter that access log and are
included only in reviewer self-reports. Fewer emitted bytes do not establish
fewer model tokens: tool-output truncation and independent retrieval choices
prevent that inference. These small mechanical costs were negligible compared
with reviewer reasoning and tool-round-trip time.
