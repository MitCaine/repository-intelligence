# Tree-sitter baseline and callable coverage contract

The shared locator runs a small structural probe. Ordinary Python and Rust
navigation now come from the same Tree-sitter parse as the probe. The Python
standard-library AST adapter remains available directly as a reference or
fallback; the separate rust-analyzer route is
preserved as an opt-in escalation for richer source/metadata questions. No
exhaustive language coverage is claimed.

## Promised source-level forms

For the pinned Python grammar, the navigation adapter promises every
`function_definition` and `lambda` node that Tree-sitter exposes, including
top-level, class methods, nested/local functions, decorated and async functions,
and nested/assigned lambdas. A `decorated_definition` contributes its attached
decorator bytes to the function range; the underlying function maps once, not
twice. Classes and decorators themselves are containers or attachments, not
callables. Python has no bodyless declaration in this contract. An absent or
zero-width function/lambda body, missing name, or missing function-header colon
is adapter-unhandled, not a successful map.

For the pinned Rust grammar, the adapter promises every `function_item` and
`closure_expression` node exposed by Tree-sitter, including top-level, nested,
trait default and impl methods, generic functions, and nested closures.
Immediately attached outer attributes and doc comments are included in named
function source ranges. `function_signature_item` is intentionally bodyless:
inside a `trait_item` or `foreign_mod_item` it is counted as excluded from the
callable map. Elsewhere it is treated as adapter-unhandled and makes the result
incomplete. Missing/zero-width bodies or names on promised nodes do likewise.

Each successfully parsed supported direct-file result's `adapter_coverage`
counts promised syntax nodes, mapped entries,
adapter-unhandled nodes, and explicitly excluded bodyless signatures. The first
count must equal mapped plus unhandled; a duplicate mapped source range is a
failure, not a second callable. Unhandled detail is bounded to 50 entries, while
counts remain exact. `ERROR` and `MISSING` syntax diagnostics independently
make a result incomplete, even when valid neighboring declarations are mapped.
These are commitments over the grammar's recognized node kinds, not proof that
every possible language construct or generated macro expansion was inventoried.

Pinned package versions in `pyproject.toml` are `tree-sitter==0.25.0`,
`tree-sitter-python==0.25.0`, and `tree-sitter-rust==0.24.2`. Results record
actual installed distribution versions, grammar ABI, and adapter version 1.
Changing a grammar pin requires reviewing that grammar's upstream generated
`node-types.json` for changed declaration nodes/fields, then running the
Python/Rust fixtures and installed-wheel check before adoption. The wheel
distributions do not ship `node-types.json`; this is an upgrade review step,
not a runtime registry.

For that review, download the generated files from the exact pinned grammar
tags ([Python 0.25.0](https://raw.githubusercontent.com/tree-sitter/tree-sitter-python/v0.25.0/src/node-types.json),
[Rust 0.24.2](https://raw.githubusercontent.com/tree-sitter/tree-sitter-rust/v0.24.2/src/node-types.json))
outside the repository and run
`python scripts/check_grammar_nodes.py PYTHON_NODE_TYPES RUST_NODE_TYPES`.
The check flags missing nodes and changed required fields used by the adapters;
also inspect declaration-node additions/field type changes and run the full
fixtures before changing any pin. It does not run on ordinary queries.

Current fixtures cover Python decorated async/nested functions, methods and
lambdas, plus navigation parity across RI's own Python modules; Rust attributed
generic functions, trait/impl methods, nested functions and closures; raw-byte
mapping for declared Latin-1 Python; and both `ERROR` and `MISSING` recovery
nodes. The probe returns bounded declaration and diagnostic detail arrays,
with total counts. It is not an exhaustive contract. Rust navigation parity
with the optional analyzer is fixture-tested for names, locations, docs, and
lexical call candidates. Python Tree-sitter navigation is fixture-compared with
the standard-library AST adapter for signatures, docs, calls, and raw-byte
ranges, including declared Latin-1 source.

Explicit language selection is available for ambiguous direct files, but only
Python and Rust adapters are shipped. The pinned upstream node types have been
checked with the documented maintainer command; future grammar upgrades must
repeat that review and fixtures. Broader consumer-project parity may still find
unhandled syntax. This contract is not proof of exhaustive Python or Rust
language coverage. #9 owns repository-wide complete inventories and candidate
deltas.
