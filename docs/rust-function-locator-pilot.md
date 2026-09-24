# On-demand Rust function locator pilot

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
