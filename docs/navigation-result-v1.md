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

RI #4 will refine byte ranges, declaration identity, completeness vocabulary,
and version compatibility. RI #9 owns complete inventories and candidate
structural deltas. This interim result must not be used as proof that no other
callable exists.
