# On-demand Rust function locator pilot

This is a disposable, source-derived navigation aid, not another maintained
dictionary. It reads one Rust file's bytes, asks a locally installed
`rust-analyzer` to parse them, and prints a bounded set of function matches:

```sh
PYTHONPATH=repository-intelligence/src python3 -m repository_intelligence.rust_index \
  poker-game/src/lib.rs --query 'blind seat' --limit 5
```

The response includes the raw SHA-256 and Git blob SHA-1 of the **file bytes
read**. These identify that source snapshot only; they do not certify a clean
checkout or resolve Git filters. The index is regenerated on each invocation,
not saved in the repository. Existing Rustdoc is surfaced as nearby authored
context, but is not promoted to an authority claim. Reported call names are
lexical candidates, not a resolved call graph. A nonzero parse-error count
means results may be incomplete.

This pilot deliberately requires the local `rust-analyzer` executable and has
no network or new Python dependency. It does not consume the hand-written
source dictionary. If practical navigation trials do not improve on ordinary
search, keep the comments and retire this locator rather than maintain two
maps.
