# Source-derived Rust function locator pilot

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

## Capsule-first comparison to run next

For each fixed task and source snapshot, prepare three executor starts:

1. Ordinary navigation: task capsule without a function packet; Codex may
   inspect the source with normal tools.
2. Dictionary: controller-selected, source-blob-verified dictionary excerpt
   included in the capsule; Codex may expand into current source.
3. Repository intelligence: controller-generated, source-hash-verified function
   packet included in the capsule; Codex may ask the locator for more context.

Record controller preparation time and packet bytes separately from Codex's
time to a correct, source-verified answer, follow-up tool calls, and total
model-visible context. A stale dictionary is an invalid preloaded packet, not
a valid control answer. This is the workflow question the five-file on-demand
check did not test.
