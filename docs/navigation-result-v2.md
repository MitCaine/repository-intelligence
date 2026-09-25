# Navigation result v2

`repository_intelligence.locator.index_file(path, root=...)` identifies one
source file before language parsing. `query_path(path, terms, root=...)` adds
bounded matches; `root` is optional for direct files and defaults to the file's
parent. The shared file and directory results return `schema_version: 2`.
Consumers must check that version before interpreting fields. The older
`rust_index.query_tree` result instead says `result_kind: legacy_rust_query`;
it has different traversal and is
**not** this versioned result. New consumers use the shared locator.
Version 2 retains the navigation fields from interim version 1 but adds the
`excluded` status and display `column`; consumers accepting only version 1
must not silently treat these as version-1 results.

`source_identity` contains a canonical relative path within the supplied root,
raw-byte SHA-256, byte count, and an optional computed Git blob object ID tagged
with the repository's storage algorithm (`sha1` or `sha256`). An unsupported
source extension still gets this identity. The computed blob ID says what Git
would hash for those bytes; it does **not** prove membership in a commit or an
unchanged checkout. Legacy `git_blob_sha1` fields remain temporarily on parsed
Rust/Python results for existing consumers; new consumers should use the tagged
identity instead.

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

The directory command currently scans `.py` and `.rs` files. Its `scan_scope`
states these extensions and labels the source `working_tree_non_atomic`: files
may change during a scan. It reports excluded hidden/generated directories,
symlinks, nested repositories, and duplicate physical files. Other file types
are counted as outside this structural scan. Directory results are navigation
packets, not exhaustive inventories or P→C candidate deltas.
Paths are normalized to `/` separators and canonical resolved spelling inside
the supplied root; the underlying filesystem determines case treatment. Direct
symlinks and paths resolving outside an explicit root are excluded rather than
silently mapped. Directory scans omit symlinks, duplicate physical files,
hidden/generated directories, and nested repositories with reported reasons.

The parser metadata names the current adapter and parser version when
available. Python uses the running interpreter's AST parser; Rust uses the
installed `rust-analyzer`. `parser.name` identifies the provider of the
`lexical_call_candidates`; these are syntactic observations, not resolved
relationships. Rust's separately identifiable grammar version is unavailable
and recorded as null rather than guessed. The controller still chooses task
scope and confirms relevant source. Ranking has no project-directory special
cases; it scores complete extracted evidence before the displayed packet is
truncated.

For supported files within the size limit, `structural` adds a pinned
Tree-sitter probe: actual runtime/grammar versions and grammar ABI, raw-byte
declaration envelopes, `ERROR`/`MISSING` counts and diagnostic samples. Its
`coverage` is `partial_navigation_evidence`, not a contracted complete
inventory. Detail arrays are bounded at 100 declarations and 50 diagnostics;
counts and `details_truncated` disclose omissions from those arrays. Python
declared encodings are decoded and parsed as UTF-8, with reported offsets mapped
back to the original raw bytes. If Tree-sitter reports syntax errors, the
shared result is `incomplete` even if the native navigation adapter returned
some matches. The existing `parser` and navigation fields still come from the
native adapters during the #8 parity phase.

Parsed callable entries include a `declaration_id` synthesized from kind and
qualified name. Named functions also carry a source-order ordinal among
same-kind, same-qualified-name declarations, so unrelated preceding edits do
not change their ID; inserting another duplicate may change those ordinals.
Anonymous lambda IDs include their starting byte offset, which can change
when preceding source moves. Entries also include a half-open `byte_range` in the
exact `source_identity` bytes; and `declaration_sha256` over that range.
Display `line`/`column` (one-based Unicode-character navigation coordinates)
and `end_line` are not identities. Python
function ranges include attached decorators and the complete function body;
Rust function ranges come from the analyzer's `FN` node, including attached
attributes and doc comments. A declaration hash changes with behavior-affecting
source in that range, but does not attest to a checkout or imply exhaustive
callable coverage. Calls remain lexical candidates from these adapters, not
resolved relationships. Rust analyzer version is recorded when available;
its grammar version is not separately exposed, so that field is null rather
than guessed.

RI #8 owns exhaustive per-language declaration coverage and RI #9 owns
repository-wide complete inventories and candidate structural deltas. This
navigation result must not be used as proof that no other callable exists.
