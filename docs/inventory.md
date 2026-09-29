# Inventory and comparison reference

`repository_intelligence.inventory.inventory_tree(root, stable=False,
logical_root=".")` scans supported Python, Rust, JavaScript, JSX, TypeScript,
TSX, Java, Go, C#, C, C++, and Markdown source without query terms. The current inventory
schema is version 14; older packets are incompatible with it. `.mts` and `.cts`
use the TypeScript adapter. Ambiguous `.h` files are not guessed: pass
`language_choices={"include/api.h": "cpp"}` (or `"c"`) for exact relative
header paths in both directory queries and inventories. Unselected `.h` files
are listed in `observed_unsupported_paths`.
Mapping contract v11 adds Markdown front matter, section and checklist units
to the existing source-callable mappings documented in
[navigation reference](navigation.md).
Every supported in-scope file appears in `files`, including files with zero
mapped units. Each file carries its exact `source_identity`, parser and
adapter coverage, structural diagnostics, mapping status, and contracted
declaration entries. Excluded hidden/generated directories, symlinks, nested
repositories are reported in `observed_exclusions`; two distinct relative paths
hardlinked to the same bytes are both included. Source-like unsupported paths
are named in `observed_unsupported_paths`; other file types are counted.
This is source-level coverage
for the [current mapping contract](language-support.md), not compiled
program, generated macro, or semantic-call completeness.

The default working-tree walk is `incomplete` because it is not atomic. Pass
`stable=True` only when the caller supplies and is responsible for stable
materialized source bytes on that side of the comparison. RI labels this
`caller_asserted_stable`; it does not verify commit membership or attest to
the checkout. Read/parse/size/adapter failures
remain incomplete even with that assertion. Explicit exclusions bound the
logical scan scope and are not silently counted as mapped source.

## Identity and scan policy

An inventory includes schema and mapping-contract versions, pinned parser
contract, logical root, relative scan policy, materialization
state, failures, and a deterministic SHA-256 `inventory_digest` over normalized
policy plus relative file paths, byte counts, and raw-byte hashes. Observed
exclusions are separate scan evidence and do not affect the digest. They
block comparison when they overlap files mapped on the opposite side. The digest is
a reproducibility checksum, not a signature or source authenticity proof.
Different absolute checkout paths can have the same logical root and digest.
The policy includes selected header languages and caller-selected excluded
directory names; the default excluded names include `target`, `node_modules`,
`venv`, and `__pycache__`. A file that becomes excluded at the same relative
path blocks comparison with `coverage_lost`, rather than looking like a normal
source deletion. Conversely, a candidate file hidden by a planning-side
exclusion blocks comparison with `planning_coverage_missing`; missing baseline
coverage is not proof that the file was added. Checks include excluded parent
directories and exact file paths, without confusing sibling path prefixes.

## Comparison results

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
Repeated named declarations with the same syntactic identity carry
`identity_ambiguous`; in a changed file, these are conservatively reported as
removed and added even when their positional IDs coincide. Java, C#, and C++
overloads use syntactic parameters, not resolved compiler symbols, for identity.
The current mapping contract also distinguishes Java declarator array dimensions,
C# generic arity and indexer parameter ownership, and C++ member cv/ref
qualifiers. Out-of-class C++ constructor/destructor/operator kinds follow terminal syntax.
This remains source-level identity, not semantic type resolution.

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

## Command-line output

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

## Compact JSON

For machine consumers that need a smaller comparison packet,
`compare --compact-json` projects the same completed comparison into shared per-file
metadata, file-path change lists, counts for every declaration category, and
changed-declaration references with hashes and ranges. Unchanged declaration
records are omitted from that projection, not from the comparison itself.
Use `--json` when full declaration evidence is needed; the compact projection
does not change qualification, ranking, or the underlying inventory digest.
Parser and pinned-version setup is reused only during one directory
navigation or inventory invocation. RI does not keep a persistent source cache;
each invocation reads and parses current files again.

The CLI accepts repeatable `--header-language include/api.h=cpp` and
`--exclude-directory generated` for either `scan` or `compare`. Pass the same
choices to both sides of a comparison. A supported declaration delta is not a
complete changed-file list: always inspect the full Git diff alongside RI,
because configuration, imports, initializers, unsupported source, and other
files can change with no mapped callable delta. RI does not reconcile Git
changes itself.
