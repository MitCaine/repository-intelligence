# Navigation result v1 (interim)

`repository_intelligence.locator.index_file(path)` identifies the exact file
bytes before attempting language parsing. `query_path(path, terms)` adds bounded
matches. Both return `schema_version: 1`; callers must not silently reinterpret
fields if this version changes.

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
  for the file type.

The directory command currently scans `.py` and `.rs` files. Its `scan_scope`
states these extensions and labels the source `working_tree_non_atomic`: files
may change during a scan. It reports excluded hidden/generated directories,
symlinks, nested repositories, and duplicate physical files. Other file types
are counted as outside this structural scan. Directory results are navigation
packets, not exhaustive inventories or P→C candidate deltas.

The parser metadata names the current adapter and parser version when
available. Python uses the running interpreter's AST parser; Rust uses the
installed `rust-analyzer`. No native semantic relationship is claimed by this
result. The controller still chooses task scope and confirms relevant source.

Parsed callable entries include a `declaration_id` synthesized from kind and
qualified name. Named functions also carry a source-order ordinal among
same-kind, same-qualified-name declarations, so unrelated preceding edits do
not change their ID; inserting another duplicate may change those ordinals.
Anonymous lambda IDs include their starting byte offset, which can change
when preceding source moves. Entries also include a half-open `byte_range` in the
exact `source_identity` bytes; and `declaration_sha256` over that range.
Display `line`/`end_line` are not identities and may be less precise. Python
function ranges include attached decorators and the complete function body;
Rust function ranges come from the analyzer's `FN` node, including attached
attributes and doc comments. A declaration hash changes with behavior-affecting
source in that range, but does not attest to a checkout or imply exhaustive
callable coverage. Calls remain lexical candidates from these adapters, not
resolved relationships. Rust analyzer version is recorded when available;
its grammar version is not separately exposed, so that field is null rather
than guessed.

RI #4 will refine byte ranges, declaration identity, completeness vocabulary,
and version compatibility. RI #9 owns complete inventories and candidate
structural deltas. This interim result must not be used as proof that no other
callable exists.
