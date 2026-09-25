# Navigation result v4

The shared `index_file` and `query_path` APIs return `schema_version: 4`.
Version 4 retains the [v3 source identity, scan scope, parser, and coverage
contract](navigation-result-v3.md), but changes some syntactic callable
records. Consumers must check the schema version and must not interpret a v4
packet as v3. The separate `rust_index.query_tree` compatibility result remains
`legacy_rust_query`, not a shared navigation packet.

For a named JavaScript or TypeScript function expression with a direct
assignment binding, RI keeps the internal syntactic `name` and
`qualified_name`, and adds `binding_aliases` with the externally visible
syntactic binding. For example, `const locateInvoice = function worker() {}`
emits one callable named `worker` with `binding_aliases: ["locateInvoice"]`.
Search ranks the alias as a name. It does not duplicate the declaration or
expand its byte range to the assignment. These aliases are syntactic
observations, not resolved imports or exports.

JavaScript/TypeScript `export_kind` describes a callable's direct syntactic
export only. A nested helper inside an exported outer function has
`export_kind: null`; the directly exported outer function remains `named` or
`default`, and direct CommonJS assignment remains `commonjs`. Lexical ownership
in `qualified_name` does not itself export a nested callable.

Java, C#, and C++ overload `declaration_id` values include a syntactic
parameter discriminator. Version 4 additionally distinguishes Java declarator
array dimensions, C++ member `const` and ref qualifiers, and C# generic arity
and parameter modifiers. C# indexer accessors include the enclosing indexer
parameter types in qualified ownership; nested local C# callables inherit a
syntactic owner discriminator. C++ out-of-class constructors, destructors, and
operators derive their kind from terminal declarator syntax, not a flattened
qualified name. These are source-level identities, not compiler type or
overload resolution. Identical kind/name/discriminator groups remain marked
`identity_ambiguous` and are compared conservatively by inventory.

Inventory schema 10 and mapping contract
`python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v3`
incorporate these record changes. Compare only matching inventory contracts.
The full Git changed-file list remains necessary beside structural RI
evidence. RI does not resolve modules, bundlers, runtime reachability, or
semantic call relationships.
