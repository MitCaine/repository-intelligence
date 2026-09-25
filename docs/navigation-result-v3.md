# Navigation result v3

`repository_intelligence.locator.index_file(path, root=..., language=...)` identifies one
source file before language parsing. `query_path(path, terms, root=..., language=...)` adds
bounded matches; `root` is optional for direct files and defaults to the file's
parent. The shared file and directory results return `schema_version: 3`.
Consumers must check that version before interpreting fields. The older
`rust_index.query_tree` compatibility function instead says
`result_kind: legacy_rust_query`; it has different traversal and is **not**
this versioned result. New consumers use the shared locator; the `rust_index`
command remains an opt-in native parsing route.
Version 3 retains navigation fields from version 2 but changes structural
declaration evidence to adapter-owned accounting. Consumers accepting only
version 2 must not silently treat these as version-2 results.

`source_identity` contains a canonical relative path within the supplied root,
raw-byte SHA-256, byte count, and an optional computed Git blob object ID tagged
with the repository's storage algorithm (`sha1` or `sha256`). An unsupported
source extension still gets this identity. The computed blob ID says what Git
would hash for those bytes; it does **not** prove membership in a commit or an
unchanged checkout. Legacy `git_blob_sha1` fields remain temporarily on parsed
results for existing consumers and are computed by common source handling;
new consumers should use the tagged
identity instead.

Directory results include one `files` record keyed by the match's `path`
string (absolute only when the queried root is absolute). Each record carries
the same parser, structural, preprocessing,
source-identity, adapter-coverage, mapping-status and parse-error evidence as a
direct-file result, without copying that record into every match. C/C++
preprocessing remains raw-source-only in both JSON and compact presentation.
Failed reads/parses retain a file record when a packet was produced, alongside
the directory `failures` list. Match entries refer to records by their `path`.

`mapping_status` is one of:

- `navigation_only`: the current parser returned results, but no exhaustive
  declaration-coverage claim is made;
- `incomplete`: parsing, reading, or the 4 MB per-file parser limit prevented
  a complete navigation pass; byte identity is retained when reading succeeded;
- `unsupported`: the bytes were identified but no structural parser is shipped
  for the file type;
- `excluded`: a direct path was outside the supplied root or was a symlink
  (including dangling links and links to directories),
  so its bytes were not read, `source_identity` is null, and `excluded_reason`
  states why (`outside_root` or `symlink_path`).

`complete` is deliberately not emitted by current adapters. It would mean
that a stated structural declaration contract was exhaustively covered in the
exact supplied bytes. A zero parse-error count does not establish this.
Semantic resolution completeness would require a separate native-analysis
question, configuration, and provider result; there is no such claim here.
`navigation_only`, `incomplete`, `unsupported`, and `excluded` never support
an absence claim. An `incomplete` result may still contain usable matches.
For a direct file with an ambiguous extension, `language="python"`,
`"rust"`, `"javascript"`, `"typescript"`, `"tsx"`, `"java"`, `"go"`,
`"csharp"`, `"c"`, or `"cpp"` explicitly chooses a shipped adapter; without it, the file
is `unsupported` with `unsupported_reason: no_language_adapter_selected`.
A conflicting selection for a known supported extension returns
`unsupported` with `unsupported_reason: language_extension_mismatch`.
Unknown language names are rejected. For directories, `language_choices`
selects `c` or `cpp` per relative `.h` path; the direct-file `language` argument
does not apply to a directory. Selecting Rust for `.h` does not interpret C/C++
syntax; select `c` or `cpp` for a C/C++ header.

The directory command currently scans `.py`, `.rs`, `.js`, `.jsx`, `.mjs`,
`.cjs`, `.ts`, `.mts`, `.cts`, `.tsx`, `.java`, `.go`, `.cs`, `.c`, `.cc`, `.cpp`,
`.cxx`, `.hh`, `.hpp`, and `.hxx` files. `.h` is ambiguous and appears in
`unsupported_paths` unless selected through `language_choices`. Its `scan_scope`
states these extensions and labels the source `working_tree_non_atomic`: files
may change during a scan. It reports observed exclusions for hidden/generated
directories and files, symlinks, nested repositories, and caller-excluded
directories. Distinct in-scope hardlinked paths are each scanned and reported;
they are not excluded as duplicate physical files. Other file types are counted
as outside this structural scan. Directory results are navigation
packets, not exhaustive inventories or P→C candidate deltas.
Relative source-identity paths use `/` separators inside the supplied root;
the underlying filesystem determines case treatment. Direct symlinks and paths
resolving outside an explicit root are excluded rather than silently mapped.
Directory scans omit symlinks, hidden/generated directories, and nested
repositories with reported reasons.

The parser metadata names the current adapter and parser version when
available. Ordinary supported-language navigation uses the pinned Tree-sitter
runtime and their language grammars. The standard-library Python AST adapter
remains available directly as a reference/fallback API.
The separate rust-analyzer route remains available as opt-in escalation.
`parser.name` identifies the provider of the
`lexical_call_candidates`; these are syntactic observations, not resolved
relationships. The controller still chooses task
scope and confirms relevant source. Ranking has no project-directory special
cases; it scores complete extracted evidence before the displayed packet is
truncated.

For supported files within the size limit, `structural` adds pinned
Tree-sitter evidence: actual runtime/grammar versions and grammar ABI, independent
`ERROR`/`MISSING` counts and diagnostic samples. The declaration envelopes and
count are presented from the language adapter's own mapping/coverage, not from
a second classifier. Its `coverage` is `adapter_owned_callable_accounting`;
agreement with `adapter_coverage` is by construction and is not independent
proof of completeness. Detail arrays are bounded at 100 declarations and 50
diagnostics; counts and `details_truncated` disclose omissions from those arrays.
`declaration_count` counts promised adapter syntax, while `declarations` lists
mapped entries only; `adapter_coverage.unhandled_node_count` explains any
unmapped promised nodes. `details_truncated` means a bounded detail array was
actually cut short, not merely that an unhandled node exists. Python
declared encodings are decoded and parsed as UTF-8, with reported offsets mapped
back to the original raw bytes. If Tree-sitter reports syntax errors, the
shared result is `incomplete` even if navigation returned some matches. Python,
Rust, JavaScript, TypeScript, Java, Go, C, C++, and C# navigation use the same
Tree-sitter parse as this structural evidence.
The adapters report promised Python function/lambda and Rust
`function_item`/`closure_expression` nodes they cannot handle as incomplete;
the JavaScript/TypeScript adapter does the same for its documented callables.
This remains navigation evidence, not complete coverage.
Successfully parsed supported direct-file `adapter_coverage` reports
`promised_node_count`, `mapped_node_count`,
`unhandled_node_count`, and `bodyless_excluded_count` for the documented
source-level contract. Rust trait and foreign bodyless signatures are excluded;
unhandled promised nodes make the mapping incomplete. See
`docs/tree-sitter-baseline.md` for the exact syntax families and policy.

Parsed callable entries include a `declaration_id` synthesized from kind and
qualified name. Java, C#, and C++ overloads also include a syntactic parameter
discriminator (including C++ pointer/reference shape and C# parameter modifiers),
without compiler type resolution. Named functions carry a
source-order ordinal only among identical kind/name/discriminator groups.
Those groups are marked `identity_ambiguous` when repeated; a changed file's
ambiguous entries are conservatively reported as removed and added rather than
silently paired by position.
Anonymous lambda IDs include their starting byte offset, which can change
when preceding source moves. Entries also include a half-open `byte_range` in the
exact `source_identity` bytes; and `declaration_sha256` over that range.
Display `line`/`column` (one-based Unicode-character navigation coordinates)
and `end_line` are not identities. Python
function ranges include attached decorators and the complete function body;
Rust function ranges come from Tree-sitter `function_item` nodes, including attached
attributes and doc comments. A declaration hash changes with behavior-affecting
source in that range, but does not attest to a checkout or imply exhaustive
callable coverage. Calls remain lexical candidates from these adapters, not
resolved relationships. The opt-in rust-analyzer route has a separate result
shape and records its own parser metadata where available.

The inventory API supplies repository-wide candidate structural deltas. This
navigation result must not be used as proof that no other callable exists.
