# Source-derived Rust function locator pilot

## Post-cleanup usability smoke (2026-09-24)

Two current-source navigation questions still resolved to narrow production
functions after the reviewer-security cleanup. A whole-repository query for
`pause resume clock` indexed 308 Rust files with zero parse errors or failed
files and led to `TournamentHybridLevelControllerV1::resume_clock` and
`TournamentClock::resume`, with tournament-timing authority hints. Reading those
small source spans confirmed the first delegates to the logical clock and can
enter final-table mode, while the second restores the clock phase. A direct
query of the 5,000-line `poker-app/src/tournament.rs` for `restore saved pair`
led first to `validate_hybrid_pair_common` and
`validate_hybrid_pair_for_launch`; the returned lines contained the saved-state
checks. No maintained dictionary was used.

The first query also exposed an inline `tests` module ranking above production
code. The locator now recognizes a leading `tests::` owner as test code, and a
regression test covers that case. This smoke check supports continued practical
use; it does not remeasure agent token use or prove that every semantic
relationship can be inferred from source.

> **Workflow correction:** The intended use is capsule-first. The controller
> runs this locator before dispatch, selects a small source-bound function
> packet, and puts that packet in the capsule. Codex starts with the packet and
> may run the locator again only if it needs more context. The on-demand checks
> below exercised the locator as an executor lookup, so their tool timings and
> initial-output comparisons **must not** be used as evidence that the intended
> capsule workflow is faster or uses less model context than its controls.

This is a disposable, source-derived navigation aid, not another maintained
dictionary. It reads one Rust file's bytes, asks a locally installed
`rust-analyzer` to parse them, and prints a bounded set of function matches:

```sh
PYTHONPATH=repository-intelligence/src python3 -m repository_intelligence.rust_index \
  poker-game/src/lib.rs --query 'blind seat' --limit 5
```

The response includes the raw SHA-256 of the **file bytes read** (and JSON
also includes the Git blob SHA-1). These identify that source snapshot only; they do not certify a clean
checkout or resolve Git filters. The index is regenerated on each invocation,
not saved in the repository. Existing Rustdoc is surfaced as nearby authored
context, but is not promoted to an authority claim. Reported call names are
lexical candidates, not a resolved call graph. A nonzero parse-error count
means results may be incomplete.

The default output is a compact navigation packet (one line per match). Add
`--json` for the full structured record, including signatures, both hashes,
and up to 12 lexical call candidates per function. The compact packet shows
the raw SHA-256, only call candidates that match the query, and the total
match count so a truncated result is visible.

This pilot deliberately requires the local `rust-analyzer` executable and has
no network or new Python dependency. It does not consume the hand-written
source dictionary. If practical navigation trials do not improve on ordinary
search, keep the comments and retire this locator rather than maintain two
maps.

## First compact-output check

On the 6,566-line `poker-game/src/lib.rs` snapshot with SHA-256
`84ec4998fa7b47c805267f0444f057756a0488c66cdcfe33a61830d2dfdb7565`,
the generated packet for `movement burden` was 10 lines/1,159 bytes. A literal
`movement|burden` search of the existing dictionary returned 15 lines/2,892
bytes; a manually narrowed symbol search returned 5 lines/1,356 bytes. For
`tournament settlement elimination`, the generated packet was 10 lines/1,202
bytes, versus 76 lines/16,869 bytes for the literal dictionary search and 7
lines/1,274 bytes for a manually narrowed symbol search. These are output-size
observations, **not** measured model-token or task-time savings. The dictionary
still contains behavioral explanations absent from the source comments; the
generated packet must lead to narrow source inspection for those claims.

## Five-file navigation check

The same natural-language location question was tried three ways for each
file: ordinary `rg` over the Rust source (first 40 result lines), `rg` over its
source dictionary (first 40), and this locator (first eight functions). The
questions concerned destination movement burden, seat-private canonical
export, causal presentation grouping, entrant-seat assignment, and hybrid
saved-pair validation, respectively. All five local source blobs matched the
remote `main` blobs. Numbers below are **model-visible initial result bytes**
and median local tool round-trip milliseconds over three repeats; they are not
model tokens or agent task-completion times.

| Rust file | Source search | Dictionary search | Locator | Dictionary source match? |
| --- | ---: | ---: | ---: | --- |
| `poker-game/src/lib.rs` | 2,726 B / 56 ms | 3,369 B / 51 ms | 1,186 B / 233 ms | No |
| `poker-session/src/holdem.rs` | 2,493 B / 49 ms | 5,488 B / 49 ms | 1,582 B / 163 ms | Yes |
| `poker-client/src/presentation.rs` | 2,425 B / 50 ms | 2,295 B / 50 ms | 872 B / 161 ms | Yes |
| `poker-tournament/src/domain.rs` | 1,994 B / 50 ms | 4,273 B / 50 ms | 1,027 B / 132 ms | Yes |
| `poker-app/src/tournament.rs` | 2,316 B / 50 ms | 3,557 B / 51 ms | 1,235 B / 214 ms | No |

Across these five prompts, the locator returned the primary production entry
point in its first eight matches every time. The first 40 ordinary source hits
missed the primary declaration for assignment and hybrid validation, requiring
refinement. The two stale dictionaries cannot be trusted for current line
numbers or behavioral claims: `poker-game/src/lib.rs` is now 6,566 lines versus
the dictionary's 6,554, and `poker-app/src/tournament.rs` is 5,259 versus
4,885. A correct dictionary-assisted workflow must check its recorded blob
and fall back to current source for those files.

Initial result output totaled 11,954 B for ordinary source search, 18,982 B
for dictionary search, and 5,902 B for the locator. Reading the same focused
source spans to verify all five answers adds 11,309 B to **each** route; under
that deliberately uniform verification rule, totals are 23,263 B, 30,291 B,
and 17,211 B. This makes the locator a useful navigation and freshness aid in
this sample. It does **not** show faster agent completion or prove that it can
replace the dictionary's richer behavioral descriptions. Search terms and
limits were fixed for this trial, but one agent conducted all routes, so this
is an engineering smoke test rather than a blinded A/B/C model evaluation.

## Capsule-first agent comparison

Before this trial, the two stale source dictionaries identified above were
refreshed and merged in PR #400. Their source blobs and function line ranges
were checked against current Rust source. The other three dictionaries already
matched. Thus no condition was penalized by a known stale dictionary.

For each of the same five source files and navigation questions, three fresh
read-only executor agents received the same source path, raw source SHA-256,
question, and source-verification requirement. Only the navigation instruction
varied:

1. **Undirected:** use ordinary source navigation; no dictionary or locator.
2. **Dictionary-directed:** consult the existing source dictionary first,
   verify its pinned source blob, then inspect current source; no locator.
3. **Capsule-first locator:** start with a small function/line-range packet
   generated by the controller from `rust-analyzer`, then verify current
   source; optional locator follow-up was allowed, but none was needed.

Every executor produced a correct, source-cited answer and confirmed the
scoped source hash. The numbers are per-agent shell reads, returned shell
output characters, and elapsed wall-clock time from its first to final tool
call. They exclude prompt text, model-internal tokens, controller planning,
and executor startup before the first tool call; actual runner token telemetry
is reported below. The dictionary condition
read the dictionary at execution time; it did **not** receive a controller-
selected dictionary excerpt in advance.

| File | Undirected reads / chars / s | Dictionary reads / chars / s | Preloaded locator reads / chars / s |
| --- | ---: | ---: | ---: |
| `poker-game/src/lib.rs` | 3 / 18,036 / 8.5 | 2 / 23,586 / 6.4 | 2 / 6,970 / 7.3 |
| `poker-session/src/holdem.rs` | 4 / 20,333 / 15.7 | 6 / 28,699 / 20.7 | 3 / 10,021 / 9.1 |
| `poker-client/src/presentation.rs` | 5 / 37,790 / 18.7 | 4 / 29,815 / 15.9 | 3 / 23,626 / 15.0 |
| `poker-tournament/src/domain.rs` | 5 / 14,438 / 16.7 | 4 / 13,835 / 12.7 | 1 / 3,979 / 1.7 |
| `poker-app/src/tournament.rs` | 4 / 25,504 / 13.7 | 3 / 16,213 / 9.9 | 2 / 5,889 / 8.3 |
| **Total** | **21 / 116,101 / 73.3** | **19 / 112,148 / 65.5** | **11 / 50,485 / 41.4** |

Controller locator calls took 261, 148, 154, 122, and 203 ms respectively
(888 ms total). This is measured tool time only, not the human-like selection
and capsule-writing effort. The preloaded packet text also consumed prompt
context that is absent from the shell-output column. These observations
therefore support a narrower conclusion: in these five navigation tasks, a
pre-generated, source-bound function packet reduced follow-up reading and
first-to-final-tool elapsed time while preserving answer quality. They do not
by themselves establish model-token savings, statistical reliability, or a general
speed advantage over a well-selected dictionary excerpt. Maintaining stale
dictionaries had a separate, nontrivial cost, and remains outside the executor
timings.

## Expanded context-read trial

Five more matched questions were run across the same five source snapshots:
human-clock settlement, quiescent session reconstruction, presentation
interruption/gap handling, assignment release, and tournament elapsed-time
settlement. Each condition used a fresh read-only executor with the same
question and source SHA-256. The locator condition received controller-selected
function ranges from a fresh `rust-analyzer` parse before its executor began.
All executors cited current source; one dictionary answer did not inspect the
clock's internal validation and is incomplete on that requested detail.

| New task | Undirected returned chars | Dictionary returned chars | Preloaded locator returned chars |
| --- | ---: | ---: | ---: |
| Human clock | 42,253 | 41,931 | 22,547 |
| Quiescent rebuild | 20,978 | 24,971 | 19,343 |
| Presentation boundary | 23,383 | 25,601 | 6,770 |
| Assignment release | 8,612 | 13,558 | 4,328 |
| Tournament elapsed time | 43,967 | 53,627 | 21,179 |
| **All ten questions, including the first five** | **255,294** | **271,836** | **124,652** |

The preloaded route returned less shell-output text in **10/10 paired tasks**.
Its aggregate returned text was 51.2% below undirected and 54.1% below
dictionary-directed navigation. Its median per-task ratio was 48.7% of
undirected output and 35.6% of dictionary output. Across all ten tasks it
made 27 shell reads, versus 42 and 45, respectively. Summed first-to-final
tool-call elapsed time was approximately 113, 161, and 171 seconds, but these
agent timings were not run in a controlled isolated environment and are weaker
evidence than the returned-text counts.

**Measurement boundary:** Returned characters are a proxy for context
presented through shell tools, not tokenizer or billing counts. The locator
packets and condition-specific prompt text also enter model context. The ten
questions were deliberately selected from five files, not a random sample of
future work; the five-file clustering and one answer-quality miss preclude a
general statistical performance claim.

### Recorded token usage

The Codex runner wrote a `token_usage_record` for each of the 30 read-only
executor turns. The final record's cumulative `turn_token_usage` was extracted
for each turn from local session logs. These are runner-reported model tokens,
not model guesses or character-to-token conversions. They include repeated
context across multiple model calls; a turn total may therefore exceed the
model's context-window size without any individual call doing so.

| Ten matched tasks | Undirected | Dictionary-directed | Preloaded locator |
| --- | ---: | ---: | ---: |
| Input tokens, including cached | 2,556,023 | 2,824,209 | 1,938,746 |
| Of those, cached input tokens | 2,420,352 | 2,683,776 | 1,852,928 |
| Input tokens excluding cached | 135,671 | 140,433 | 85,818 |
| Output tokens | 8,625 | 8,987 | 7,154 |
| Total tokens | 2,564,648 | 2,833,196 | 1,945,900 |

The preloaded route used fewer recorded input tokens in **10/10 matched
tasks**: 24.1% fewer than undirected and 31.4% fewer than dictionary-directed.
Its non-cached input was 36.7% and 38.9% lower, respectively. The smaller
all-in percentage than the shell-text percentage reflects shared instructions,
tool definitions, prompt text, and context replay. Cached tokens remain input
tokens and are not free; these totals are not a cost or billing estimate.
Controller packet generation and prompt preparation are outside the executor
turns. Local logs contain more than usage data, so only aggregates are
published here.
