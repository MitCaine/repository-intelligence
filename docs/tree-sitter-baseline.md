# Tree-sitter baseline: first #8 slice

The shared locator runs a small structural probe. Ordinary Python and Rust
navigation now come from the same Tree-sitter parse as the probe. The Python
standard-library AST adapter remains available directly as a reference or
fallback; the separate rust-analyzer route is
preserved as an opt-in escalation for richer source/metadata questions. No
exhaustive language coverage is claimed.

Pinned package versions in `pyproject.toml` are `tree-sitter==0.25.0`,
`tree-sitter-python==0.25.0`, and `tree-sitter-rust==0.24.2`. Results record
actual installed distribution versions, grammar ABI, and adapter version 1.
Changing a grammar pin requires reviewing that grammar's upstream generated
`node-types.json` for changed declaration nodes/fields, then running the
Python/Rust fixtures and installed-wheel check before adoption. The wheel
distributions do not ship `node-types.json`; this is an upgrade review step,
not a runtime registry.

Current fixtures cover Python decorated async/nested functions, methods and
lambdas; Rust attributed generic functions, trait/impl methods, nested
functions and closures; raw-byte
mapping for declared Latin-1 Python; and both `ERROR` and `MISSING` recovery
nodes. The probe returns bounded declaration and diagnostic detail arrays,
with total counts. It is not an exhaustive contract. Rust navigation parity
with the optional analyzer is fixture-tested for names, locations, docs, and
lexical call candidates. Python Tree-sitter navigation is fixture-compared with
the standard-library AST adapter for signatures, docs, calls, and raw-byte
ranges, including declared Latin-1 source.

Remaining #8 work: enumerate every promised body-bearing syntax form across
both languages, broaden parity fixtures, verify behavior on grammar upgrades,
and support
explicit language selection for ambiguous extensions. Rust `function_item`
and `closure_expression` nodes are handled or visibly marked incomplete, but
this is not proof of exhaustive Rust syntax coverage. #9 owns repository-wide
complete inventories and candidate deltas.
