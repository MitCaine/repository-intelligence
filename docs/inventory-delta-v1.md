# Structural inventory and candidate delta v1

`repository_intelligence.inventory.inventory_tree(root, stable=False,
logical_root=".")` scans supported Python, Rust, JavaScript, JSX, TypeScript,
TSX, Java, and Go source without query terms. The current inventory schema is
version 4; older packets are incompatible with it.
Every supported in-scope file appears in `files`, including files with zero
mapped callables. Each file carries its exact `source_identity`, parser and
adapter coverage, structural diagnostics, mapping status, and contracted
declaration entries. Excluded hidden/generated directories, symlinks, nested
repositories, and duplicate physical files are reported in normalized relative
scope; other file types are counted separately. This is source-level coverage
for the [current callable contract](tree-sitter-baseline.md), not compiled
program, generated macro, or semantic-call completeness.

The default working-tree walk is `incomplete` because it is not atomic. Pass
`stable=True` only when the caller supplies and is responsible for stable
materialized source bytes on that side of the comparison. RI labels this
`caller_asserted_stable`; it does not verify commit membership or attest to
the checkout. Read/parse/size/adapter failures and duplicate physical files
remain incomplete even with that assertion. Explicit exclusions bound the
logical scan scope and are not silently counted as mapped source.

An inventory includes schema and mapping-contract versions, pinned parser
contract, logical root, relative scan scope and exclusions, materialization
state, failures, and a deterministic SHA-256 `inventory_digest` over normalized
scope plus relative file paths, byte counts, and raw-byte hashes. The digest is
a reproducibility checksum, not a signature or source authenticity proof.
Different absolute checkout paths can have the same logical root and digest.

`compare_inventories(planning, candidate)` returns
`comparable_candidate_delta` only when both sides have compatible schema,
mapping/parser contracts and logical scope, and both are complete under the
caller-stable condition. A mismatch returns `incompatible`; an incomplete
side returns `incomplete`. Neither case emits file or declaration deltas, but
both sides' identities, coverage, exclusions, and failure reasons remain
visible. Comparison rechecks each purportedly complete file's mapping status,
source identity, parser contract, callable accounting, structural diagnostics,
and the normalized inventory checksum; a contradictory packet is incompatible
even if its top-level status says `complete`. Comparison never authorizes edits
or qualifies a candidate on behalf of a controller.
Across sides, an unchanged raw file hash under the same parser contract must
also have identical normalized declaration and coverage evidence. A mismatch
is incompatible, not a declaration modification inside an unchanged file.

Comparable results classify files by relative path and raw file hash as added,
removed, modified, or unchanged, including zero-callable files. Declarations
are classified by `(relative path, declaration_id)` and exact complete-unit
`declaration_sha256`. An unchanged structural identity with a changed hash is
modified, including attached syntax in the hashed range. Moves/renames that
cannot be identified deterministically are add-plus-remove. Anonymous
lambda/closure IDs contain start offsets, so inserting bytes before one can
likewise appear as add-plus-remove rather than a modification.

Example from two separately materialized source roots:

```python
from pathlib import Path
from repository_intelligence.inventory import inventory_tree, compare_inventories

planning = inventory_tree(Path("/snapshots/planning"), stable=True)
candidate = inventory_tree(Path("/snapshots/candidate"), stable=True)
delta = compare_inventories(planning, candidate)
if delta["status"] == "comparable_candidate_delta":
    print(delta["file_changes"], delta["declaration_changes"])
```

The installed package also exposes a controller-facing command. From a
directory where the two roots are separately materialized:

```sh
python3.13 -m repository_intelligence.inventory scan /snapshots/planning \
  --logical-root repository-intelligence --assert-stable-materialization --json
python3.13 -m repository_intelligence.inventory compare \
  /snapshots/planning /snapshots/candidate \
  --logical-root repository-intelligence --assert-stable-materialization --limit 8
```

Without `--assert-stable-materialization`, the command labels both source
walks non-atomic and emits no comparable delta. The flag is a caller assertion
for both roots, **not** RI verification; a warning appears on stderr. Compact
output bounds displayed file/change lines with `--limit` (1–20), but counts
and underlying comparison always use the full inventories. `--json` prints
full evidence without display truncation. Exit code 0 means a complete scan or
comparable factual delta; 2 means incomplete; 3 means incompatible. These
codes do not signify review approval or edit authority.
