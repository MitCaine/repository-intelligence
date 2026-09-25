# Tree-sitter baseline: first #8 slice

The shared locator now runs a small structural probe before its existing
navigation adapter. This proves a common parser can report Python and Rust
syntax and source envelopes without changing existing navigation fields or
claiming exhaustive language coverage.

Pinned package versions in `pyproject.toml` are `tree-sitter==0.25.0`,
`tree-sitter-python==0.25.0`, and `tree-sitter-rust==0.24.2`. Results record
actual installed distribution versions, grammar ABI, and adapter version 1.
Changing a grammar pin requires reviewing that grammar's upstream generated
`node-types.json` for changed declaration nodes/fields, then running the
Python/Rust fixtures and installed-wheel check before adoption. The wheel
distributions do not ship `node-types.json`; this is an upgrade review step,
not a runtime registry.

Current fixtures cover Python decorated async/nested functions, methods and
lambdas; Rust attributed generic functions, methods and closures; raw-byte
mapping for declared Latin-1 Python; and both `ERROR` and `MISSING` recovery
nodes. The probe returns bounded declaration and diagnostic detail arrays,
with total counts. It is not an exhaustive contract or a replacement for the
native adapters yet.

Remaining #8 work: enumerate every promised body-bearing syntax form, detect
adapter-unhandled nodes, align structural declarations with the existing
navigation fields, verify behavior on grammar upgrades, support explicit
language selection for ambiguous extensions, and make `rust-analyzer`
optional for ordinary structural navigation. #9 owns repository-wide complete
inventories and candidate deltas.
