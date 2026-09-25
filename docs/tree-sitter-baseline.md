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

For pinned JavaScript and TypeScript grammars, `.js`, `.jsx`, `.mjs`, `.cjs`,
`.ts`, and `.tsx` promise every body-bearing `function_declaration`,
`generator_function_declaration`, `function_expression`, `generator_function`,
`arrow_function`, and `method_definition` node. This includes nested and
anonymous functions, class/object methods, constructors, and accessors.
Anonymous functions get source-position-based structural IDs; overload and
interface/abstract signatures without bodies are separately counted as
bodyless, not implementations. Source ranges are exact UTF-8 byte ranges.
`module_bindings` reports syntactic imports/exports only; call candidates are
lexical, not resolved. `ERROR`, `MISSING`, and unhandled promised nodes make
the result incomplete.

For pinned Java, `.java` promises every body-bearing `method_declaration`,
`constructor_declaration`, `compact_constructor_declaration`, and
`lambda_expression` node. Classes, interfaces, records, enums, annotation
types, enum-constant class bodies, local classes, and anonymous classes provide
qualified ownership. Bodyless interface/abstract methods and annotation-type
members are counted separately, not mapped as executable callables. Static
and instance initializer blocks are deliberately not callables. Their source
bytes still change the containing file hash, so inventory comparison reports
the file as modified even if no callable declaration changes.

For pinned Go, `.go` promises every `function_declaration`,
`method_declaration`, and `func_literal` node, including `init`, generic
functions, pointer/value receiver methods, and nested anonymous literals.
The package and exact receiver syntax contribute to qualified identities;
anonymous literals receive source-position-based IDs. Interface `method_elem`
nodes are counted as bodyless, with their interface owner, not as executable
functions. This is syntax coverage, not Go type/package resolution.

Pinned package versions in `pyproject.toml` are `tree-sitter==0.25.0`,
`tree-sitter-python==0.25.0`, `tree-sitter-rust==0.24.2`,
`tree-sitter-javascript==0.25.0`, `tree-sitter-typescript==0.23.2`, and
`tree-sitter-java==0.23.5`, and `tree-sitter-go==0.25.0`. Results record
actual installed distribution versions, grammar ABI, and adapter version 1.
Changing a grammar pin requires reviewing that grammar's upstream generated
`node-types.json` for changed declaration nodes/fields, then running the
language fixtures and installed-wheel check before adoption. The wheel
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
ranges, including declared Latin-1 source. For lexical call candidates, the
Python adapter uses the standard-library AST only to normalize a Tree-sitter
identified call target's display text, preserving search terms that source
spelling (such as string-escape variants) could otherwise change. If a target
cannot be normalized, its source text remains a lexical candidate. This is
not AST-based declaration discovery or a resolved call graph. RI's current
Python modules match the AST reference for call text and search tokens; that
fixture does not promise identical presentation for every possible source.

Explicit language selection is available for ambiguous direct files. The pinned upstream node types have been
checked with the documented maintainer command; future grammar upgrades must
repeat that review and fixtures. Broader consumer-project parity may still find
unhandled syntax. This contract is not proof of exhaustive Python or Rust
language coverage. #9 owns repository-wide complete inventories and candidate
deltas.
