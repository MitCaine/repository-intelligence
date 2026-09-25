# Navigation result v5

This is the standalone current navigation reference. The public functions are `repository_intelligence.locator.index_file` and `query_path`; the latter also provides the locator CLI. They emit `schema_version: 5`. The associated inventory schema is 11, mapping contract is `python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v5`, and adapter version is 5. Adapter version 5 corrects nested C++ lambda traversal, reference declarators, comment extras in identities, and C# constructor modifiers without changing the packet shape.

Check versions before interpreting saved packets. The package metadata version alone is not a result contract. Earlier navigation documents describe historical behavior; the separate `rust_index.query_tree` result remains `legacy_rust_query`, not v5. Read [known limitations](known-limitations.md) with this specification: intended mapping contracts do not eliminate implementation defects.

## Entry points and selection

`index_file(path, *, root=None, language=None)` reads a file and returns its complete extracted callable list under `functions`. The default identity root is the file's parent. `query_path(source, terms, limit=8, *, root=None, language=None, language_choices=None, excluded_directories=())` accepts a direct path or directory and returns ranked `matches`; limits range from 1 through 20. Internal scan-setup/object-format parameters are implementation seams, not needed for normal consumers.

For direct files, `language` can select `python`, `rust`, `javascript`, `typescript`, `tsx`, `java`, `go`, `csharp`, `c`, or `cpp`. A known-extension conflict returns `unsupported` with `language_extension_mismatch`; an unknown language is rejected. Unselected unknown/ambiguous extensions return `unsupported` with `no_language_adapter_selected`, provided acquisition succeeds. A direct symlink or a path resolving outside its root is `excluded`, without byte identity.

Directory scans use `.py`, `.rs`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.mts`, `.cts`, `.tsx`, `.java`, `.go`, `.cs`, `.c`, `.cc`, `.cpp`, `.cxx`, `.hh`, `.hpp`, and `.hxx`. Exact relative `.h` paths can additionally be mapped to `c` or `cpp` through `language_choices` / `--header-language`. Direct-file `root` and `language` options do not apply to a directory query.

## Status and byte identity

`mapping_status` is `navigation_only` after the current adapter and syntax checks succeed; `incomplete` when acquisition, parsing, or promised mapping fails; `unsupported` when no appropriate adapter is selected; or `excluded` for an excluded direct path. Navigation never emits inventory's `complete` status. An incomplete packet may contain useful neighboring declarations. No navigation status makes a zero-match result an absence proof.

`source_identity` contains `relative_path` using `/` separators, `byte_count`, `raw_sha256`, and optional `git_blob`. The Git object is algorithm-tagged (`sha1` or `sha256`) and computed from observed bytes. It does not verify a checkout or commit. Parsed results retain the legacy untagged `git_blob_sha1` compatibility field; new consumers should use `source_identity`.

The shared scanner has two independent limits, in decimal bytes:

| Condition | Result |
| --- | --- |
| Supported regular source at or below 4,000,000 bytes | Identity, then a parsing attempt. |
| Supported regular source above 4,000,000 and at or below 32,000,000 bytes | Identity retained; incomplete with `SourceLimitExceeded`. |
| Source above 32,000,000 bytes | Incomplete with `SourceReadLimitExceeded`; identity is null. |
| Non-regular source | Not read; incomplete when returned as a direct packet, or reported as a scan failure. |
| Read failure | Incomplete; identity is null. |
| Excluded direct path | Not read; excluded; identity is null. |

Unsupported regular files within the acquisition limit still receive byte identity, without structural interpretation. Do not assume every incomplete packet has `structural`, parser metadata, or a hash. The limits above do not redefine legacy/native API reads.

## Callable records

Successful `index_file` results include `function_count`, `functions`, `parse_error_count`, `adapter_coverage`, parser metadata, structural evidence, and raw identity. Callable records contain `name`, `qualified_name`, display `line`/`column`/`end_line`, `signature`, `docs`, `lexical_call_candidates`, `declaration_kind`, `declaration_id`, half-open raw `byte_range`, and `declaration_sha256`. Additional fields are adapter-specific; consumers must not require a JavaScript alias or C++ preprocessing record from every language.

Named IDs use kind, qualified owner/name, optional syntactic signature, and an ordinal among identical keys. Repeated keys set `identity_ambiguous`; inventory compares them conservatively in changed files. Anonymous identities include source positions and may move after unrelated preceding edits. These IDs are structural, not resolved compiler symbols.

Display coordinates are navigation hints, not identity. Raw ranges and hashes bind the observation to its source bytes. Python function ranges include attached decorators; Rust named functions include applicable outer attributes/docs; C++ ranges include attached template/friend chains rather than whole containers. Supported Python encodings use incremental decoder boundaries to map parsed UTF-8 back to raw source. Unmappable boundaries are incomplete; a UTF-8 BOM-only file is valid empty source.

JavaScript/TypeScript named function expressions may retain an internal name and provide `binding_aliases` for the directly assigned binding. Search ranks aliases as names without duplicating declarations or widening their range to the assignment. `export_kind` describes direct syntactic export, not nested reachability or resolved module exports. Lexical call candidates and module-binding observations remain syntax, not a call graph.

## Syntax and coverage evidence

Parser metadata records actual installed Tree-sitter runtime and grammar versions, grammar ABI, and adapter version. A per-invocation `ScanSetup` reuses setup; files are still read and parsed afresh.

`structural` includes source encoding, raw-byte coordinate space, ERROR/MISSING and total diagnostic counts, diagnostic samples, a declaration count and bounded declaration summary, `details_truncated`, and `coverage: adapter_owned_callable_accounting`. Diagnostic samples are bounded at 50; declaration summaries at 100. Their total counts remain available. The summary derives from adapter records and is not an independent classifier.

`adapter_coverage` reports `promised_node_count`, `mapped_node_count`, `unhandled_node_count`, and `bodyless_excluded_count`. The accounting check requires promised = mapped + unhandled and rejects duplicate exact ranges. Syntax ERROR/MISSING and unhandled promised nodes make navigation incomplete. Bodyless detail arrays differ by adapter; use the [language contracts](tree-sitter-baseline.md) rather than inferring a universal bodyless-record schema.

## Query and directory packets

A direct query preserves index metadata, replaces `functions` with bounded `matches`, and adds `query` and `total_matches`. Ranking uses full extracted evidence before display truncation. Selected signatures and docs are compacted, and displayed lexical-call lists are shortened. The query packet is not the full callable inventory.

A directory result has `root`, `query`, `mapping_status`, `scanned_files`, syntax/adapter error aggregates, `failures`, `total_matches`, `matches`, `scan_scope`, and a `files` mapping. Each matched entry's `path` references its file record. Those records preserve source identity, parser/structural evidence, preprocessing, adapter coverage, mapping status, and parse-error count when available. Do not add `scanned_files` and failure counts to infer total scope; inspect the records and scope directly.

`scan_scope` reports root, default supported extensions, `working_tree_non_atomic`, observed excluded paths, recognized unsupported paths, and the count of other file types. The navigation packet is not the complete comparison policy; inventory carries logical root, header choices, and exclusion configuration for compatibility. Hidden names, default/caller-excluded directory names, symlinks, and nested repositories are excluded. Distinct hardlinked relative paths remain distinct sources. This traversal does not implement `.gitignore` or Git-tracked-file selection.

## Failure handling and compatibility

Direct exclusion packets include `excluded_reason`; acquisition/adapter failures provide `failures` where supported. Not all exceptions are converted to packets: invalid source/query/configuration and some operational errors can raise. A directory with no selected supported paths, recognized unsupported paths, or traversal failures raises a no-source `ValueError`, even when exclusions were observed.

The locator CLI does not map `mapping_status` to special exit codes. Machine consumers must inspect JSON. The separate [inventory API and CLI](inventory-delta-v1.md) controls complete/incomplete/incompatible comparison and its own exit codes.

Relative to v4, v5 changes decoded raw-position mapping, C++ attached source envelopes and bodyless/try-block classification, token-preserving identity, Java nested overload ownership, direct export and constructor classification, I/O limits, and declaration packet validation. It does not add compiler resolution, snapshot attestation, or project authorization.
