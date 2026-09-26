# Language support and callable contracts

The shared locator runs a small structural probe. Ordinary Python and Rust
navigation now come from the same Tree-sitter parse as the probe. The Python
standard-library AST adapter remains available directly as a reference or
fallback; the separate rust-analyzer route is
preserved as an opt-in escalation for richer source/metadata questions. No
exhaustive language coverage is claimed.
The syntax probe owns parser metadata and `ERROR`/`MISSING` diagnostics only.
Each language adapter alone owns callable selection, promised/unhandled counts,
names, kinds, ownership, and source slices. Structural declaration
details are a bounded presentation of adapter entries, not a second independent
classifier. Fixed expected-source fixtures, not agreement between two counters,
test the mapping promise.

## Shared accounting

Each successfully parsed supported direct-file result's `adapter_coverage`
counts promised syntax nodes, mapped entries,
adapter-unhandled nodes, and explicitly excluded bodyless signatures. The first
count must equal mapped plus unhandled; a duplicate mapped source range is a
failure, not a second callable. Unhandled detail is bounded to 50 entries, while
counts remain exact. `ERROR` and `MISSING` syntax diagnostics independently
make a result incomplete, even when valid neighboring declarations are mapped.
These are commitments over the grammar's recognized node kinds, not proof that
every possible language construct or generated macro expansion was inventoried.

CR/LF handling follows each language. Python, JavaScript/TypeScript, Java,
C#, and C/C++ treat lone CR as a line terminator; RI normalizes it to LF only in
the parse input, retaining the same byte width and the original source slices.
Rust and Go retain lone CR as whitespace rather than a line break, including in
display columns. CRLF and LF retain their normal line behavior. This does not
expand Java Unicode escapes, C/C++ preprocessing, or generated source.

## Python

For the pinned Python grammar, the navigation adapter promises every
`function_definition` and `lambda` node that Tree-sitter exposes, including
top-level, class methods, nested/local functions, decorated and async functions,
and nested/assigned lambdas. A `decorated_definition` contributes its attached
decorator bytes to the function range; the underlying function maps once, not
twice. Classes and decorators themselves are containers or attachments, not
callables. Python has no bodyless declaration in this contract. An absent or
zero-width function/lambda body, missing name, or missing function-header colon
is adapter-unhandled, not a successful map.
Declared encodings are decoded into Tree-sitter input with raw-byte positions
mapped from the actual decoder output. Ambiguous character boundaries make the
file incomplete rather than assigning an approximate declaration slice.

Python identifiers follow the interpreter's NFKC normalization, including
containing class names; raw spelling is retained in signatures and source bytes.
LF, CRLF, and lone CR physical lines are supported, including coding cookies on
the second physical line. Parsing normalization never rewrites the identified
source or its declaration hashes. The native AST handoff uses the same encoding
rules while keeping its distinct source-envelope contract.

## Rust

For the pinned Rust grammar, the adapter promises every `function_item` and
`closure_expression` node exposed by Tree-sitter, including top-level, nested,
trait default and impl methods, generic functions, and nested closures.
Applicable outer attributes and doc comments, including across blank lines and
ordinary comment trivia, are included in named
function source ranges. `function_signature_item` is intentionally bodyless:
inside a `trait_item` or `foreign_mod_item` it is counted as excluded from the
callable map. Elsewhere it is treated as adapter-unhandled and makes the result
incomplete. Missing/zero-width bodies or names on promised nodes do likewise.
Rust, like the other non-Python adapters, requires valid UTF-8; invalid bytes
make mapping incomplete while the scanner retains exact raw-byte identity.

## JavaScript and TypeScript

For pinned JavaScript and TypeScript grammars, `.js`, `.jsx`, `.mjs`, `.cjs`,
`.ts`, `.mts`, `.cts`, and `.tsx` promise every body-bearing `function_declaration`,
`generator_function_declaration`, `function_expression`, `generator_function`,
`arrow_function`, and `method_definition` node. This includes nested and
anonymous functions, class/object methods, true non-static class constructors,
and accessors. Object methods and static methods named `constructor` remain
ordinary methods. Callable export labels describe direct syntactic bindings,
not nested methods or callbacks. Nested helpers inherit class-member static/instance
ownership and getter/setter kind, so a valid accessor pair does not make its
separate helpers ambiguous.
Anonymous functions get source-position-based structural IDs; overload and
interface/abstract signatures without bodies are separately counted as
bodyless, not implementations. Source ranges are exact UTF-8 byte ranges.
`module_bindings` reports syntactic imports/exports only; call candidates are
lexical, not resolved. `ERROR`, `MISSING`, and unhandled promised nodes make
the result incomplete.
Nearby syntactic comments are small search hints for callable terms; they are
not authority metadata or resolved documentation links.

## Java

For pinned Java, `.java` promises every body-bearing `method_declaration`,
`constructor_declaration`, `compact_constructor_declaration`, and
`lambda_expression` node. Classes, interfaces, records, enums, annotation
types, enum-constant class bodies, local classes, and anonymous classes provide
qualified ownership. Bodyless interface/abstract methods and annotation-type
members are counted separately, not mapped as executable callables. Static
and instance initializer blocks are deliberately not callables. Their source
bytes still change the containing file hash, so inventory comparison reports
the file as modified even if no callable declaration changes.
Syntactic overload identity includes array dimensions attached to a formal
parameter's variable declarator, not just its base type.
Varargs local parameter names do not contribute to identity. Members in local
classes inside overloaded methods retain display ownership but include the
enclosing overload discriminator in their internal identity.

## Go

For pinned Go, `.go` promises body-bearing `function_declaration`,
`method_declaration`, and `func_literal` nodes, including `init`, generic
functions, pointer/value receiver methods, and nested anonymous literals.
The package and exact receiver syntax contribute to qualified identities;
anonymous literals receive source-position-based IDs. Interface `method_elem`
nodes and valid bodyless external function declarations are counted as
bodyless, not as executable functions. Interface entries retain their owner.
This is syntax coverage, not Go type/package resolution.

## C#

For pinned C#, `.cs` promises body-bearing methods, constructors (including
static), destructors, operators/conversions, local functions, lambdas,
anonymous methods, and `accessor_declaration` nodes. Expression-bodied
properties/indexers without explicit accessor nodes map as executable getters.
Namespaces, classes, structs, interfaces, records, and property/indexer/event
containers contribute ownership. Bodyless interface/abstract methods and
semicolon accessors are counted separately, not as executable declarations.
Attributes and modifiers within each callable node's source range affect its
hash. This is syntax navigation, not Roslyn semantic resolution.
C# syntactic identity includes method and containing-type generic arity.
Explicit interface properties, indexers, and events retain their interface
discriminator. Indexer accessor owners include parameter types, and nested local
callables inherit every enclosing callable owner, including getters/setters,
operators, and anonymous bodies. Generic parameter names and comments do not
change the arity discriminator. Parameter keys preserve `ref` and `out` token
boundaries for syntactic identity; RI does not determine whether a pair of
overloads is legal C#. Conversion labels come from the
actual `implicit` or `explicit` token rather than annotation/comment text.

## C and C++

For pinned C/C++, the source-level contract promises every Tree-sitter
body-bearing `function_definition`, plus C++ `lambda_expression`;
declarations/prototypes and intentionally defaulted/deleted definitions without
ordinary bodies are recorded separately. Constructor function-try-blocks count
as body-bearing implementations. C/C++ `.h` queries require an explicit
`c` or `cpp` language choice, including per-path choices in directory scans;
RI does not guess. `.c` uses C;
`.cc`, `.cpp`, `.cxx`, `.hh`, `.hpp`, and `.hxx` use C++. Attached chains of
template and friend wrappers are included in declaration byte ranges; container
class/namespace bytes are not. Namespace/class owners
locate C++ members. `preprocessing` reports directives in unexpanded raw text.
Member cv/ref qualifiers distinguish syntactic overload identities. Members of
local classes inside callable bodies also inherit their enclosing callable's
parameter, cv/ref, and template-specialization discriminator. An unrelated edit
does not turn those distinct nested members into removals and additions.
Out-of-class constructor, destructor, and operator kinds use their terminal
declarator nodes. Parameter keys preserve syntax-token boundaries and omit
local parameter names; they do not resolve compiler types.
Conditional branches, macros that generate declarations, includes, and build
flags mean this is **not** a claim about the effective compiled program. Ask
Clang with the actual flags/includes when effective declarations are needed;
ordinary structural navigation does not require Clang.

## Grammar maintenance

[`pyproject.toml`](../pyproject.toml) is the authoritative dependency pin list.
Results record actual installed runtime/grammar/ABI versions and the current
adapter version. Grammar upgrades require reviewing the exact upstream
`node-types.json` and relevant grammar rules, then running language fixtures
and the installed-wheel check. Wheels do not ship `node-types.json`; this is
maintainer work, not a runtime registry. See [maintenance](maintenance.md).

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
language coverage. The [inventory/delta contract](inventory.md)
describes the implemented query-independent comparison workflow.
