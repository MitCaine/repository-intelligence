# Navigation result v4

The shared `index_file` and `query_path` APIs return `schema_version: 4`.
Version 4 retains the [v3 source identity, scope, parser, and coverage
fields](navigation-result-v3.md), but changes JavaScript/TypeScript callable
records and export classification. Consumers must check the schema version;
they must not interpret a v4 packet as v3.

For a named function expression with an assignment binding, RI keeps the
function's internal syntactic `name` and `qualified_name`, and adds
`binding_aliases` with the externally visible syntactic binding. For example,
`const locateInvoice = function worker() {}` emits one callable named `worker`
with `binding_aliases: ["locateInvoice"]`. Search ranks the alias as a name;
the declaration is not duplicated, and its byte range remains the function
expression rather than the containing assignment. Other JavaScript/TypeScript
callables have an empty alias list unless a distinct direct binding is present.
Aliases are syntactic observations, not resolved imports or exports.

`export_kind` describes a callable's **direct** syntactic export only. A nested
helper inside an exported outer function has `export_kind: null`, while its
directly exported outer function remains `named` or `default`. Direct CommonJS
assignment remains `commonjs`. Enclosing lexical ownership remains visible in
`qualified_name`; it does not imply that the nested callable is itself
exported. RI does not resolve modules, bundlers, or runtime reachability.

Inventory schema 10 and mapping contract
`python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v3` incorporate
this record change. Compare only matching inventory contracts. The full Git
changed-file list remains necessary beside structural RI evidence.
