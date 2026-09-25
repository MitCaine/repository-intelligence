# Consumer guide

RI supplies source evidence. The caller owns source materialization, full diff review, project policy, and acceptance. Use a separate installed RI package rather than copying its modules into each consumer repository. Pin the checkout revision and keep the emitted parser and contract metadata with saved observations.

## Navigate before expanding scope

Run the examples with the Python interpreter into which RI was installed. Replace the example paths and query words with the consumer's paths and task terms.

```sh
python3.13 -m repository_intelligence.locator /path/to/project \
  --query 'pause resume clock' --limit 8
python3.13 -m repository_intelligence.locator /path/to/project/src/clock.py \
  --root /path/to/project --query 'pause resume clock' --json
```

Search tokenizes Unicode words and identifiers, including common camel-case boundaries. It ranks full extracted names, aliases, qualified names, documentation, and lexical call candidates before shortening displayed fields. This is lexical ranking, not embeddings, type resolution, or a guarantee that all relevant code was found. Query limits are 1-20, default 8.

For full per-file callable records without a query, use the library API:

```python
from pathlib import Path
from repository_intelligence.locator import index_file, query_path

root = Path('/path/to/project')
packet = index_file(root / 'src/clock.py', root=root)
assert packet['schema_version'] == 5
if packet['mapping_status'] == 'navigation_only':
    for entry in packet['functions']:
        print(entry['qualified_name'], entry['byte_range'])

result = query_path(root, 'pause resume clock', limit=8)
# Inspect mapping_status, failures, scan_scope, and each matched file's metadata.
```

Do not use the bounded `structural.declarations` array as a full inventory. Directory query JSON also contains per-file evidence for the scan, so a small match limit does not impose a small total JSON size. The [v5 reference](navigation-result-v5.md) explains these shapes.

## Choose headers and exclusions deliberately

A direct header query accepts `--language c` or `--language cpp`. A directory scan accepts exact relative header paths instead:

```sh
python3.13 -m repository_intelligence.locator /path/to/project \
  --header-language include/api.h=cpp \
  --exclude-directory generated --query 'calculate total' --json
```

`--header-language` is repeatable; it is not automatic language detection. `--exclude-directory` accepts a simple directory name and excludes every directory with that name, not one path or a glob. Hidden names, `target`, `node_modules`, `venv`, `__pycache__`, symlinks, and nested repositories are already excluded by the shared traversal policy. Do not assume RI applies `.gitignore` or scans only Git-tracked files.

Unsupported source-like paths are reported for the recognized suffix set; other file types are counted. This does not enumerate every possible programming language. A direct supported-extension/language conflict returns an unsupported packet, rather than silently changing parsers. Direct-file queries do not apply the directory exclusion/header-selection options.

## Compare stable source trees

Prepare planning and candidate trees through the consumer's existing workflow. Keep both stable for the entire scan. RI does not create or lock those snapshots.

```sh
python3.13 -m repository_intelligence.inventory scan /snapshots/planning \
  --logical-root app --assert-stable-materialization --json
python3.13 -m repository_intelligence.inventory compare \
  /snapshots/planning /snapshots/candidate --logical-root app \
  --header-language include/api.h=cpp --exclude-directory generated \
  --assert-stable-materialization --compact-json
```

The compare command applies the selected policy to both roots. Absolute paths may differ; logical scope, contracts, and parser metadata must agree. Actual observed excluded directories can differ without changing the policy. A previously included source becoming excluded at the same path blocks comparison instead of masquerading as ordinary deletion.

The library equivalent is:

```python
from pathlib import Path
from repository_intelligence.inventory import inventory_tree, compare_inventories

policy = dict(stable=True, logical_root='app',
              language_choices={'include/api.h': 'cpp'},
              excluded_directories=('generated',))
planning = inventory_tree(Path('/snapshots/planning'), **policy)
candidate = inventory_tree(Path('/snapshots/candidate'), **policy)
assert planning['inventory_schema_version'] == 11
assert candidate['inventory_schema_version'] == 11
delta = compare_inventories(planning, candidate)
if delta['status'] != 'comparable_candidate_delta':
    raise RuntimeError((delta['status'], delta['mismatches']))
# Review delta['file_changes'] and delta['declaration_changes'] with the full diff.
```

A declaration marked unchanged has the same structural identity and hashed source unit, not necessarily unchanged program behavior. Imports, enclosing containers, configuration, build conditions, and unsupported files can affect behavior. File-level changes remain important when the declaration delta is empty.

## Handle results and failures

The locator's successful process exit means it emitted a packet, not that the packet is complete. Read `mapping_status` and evidence fields. Incomplete navigation can still provide useful matches. Inventory scan/compare uses exit codes 0 for complete/comparable, 2 for incomplete, and 3 for incompatible; invalid CLI arguments and unexpected errors have separate failure paths. Do not convert every nonzero exit into an empty result.

A supported file larger than 4,000,000 but no larger than 32,000,000 bytes retains identity and reports `SourceLimitExceeded`. A file beyond 32,000,000 bytes reports `SourceReadLimitExceeded` without identity. Non-regular files report `NonRegularFile` when that check is reached. Read failures also have no byte identity. Unsupported files receive identity only when acquisition succeeds within its limit.

A source root with no selected supported paths, no recognized unsupported paths, and no traversal failures raises `ValueError`; do not interpret that as proof of absent functionality. Invalid paths, query terms, limits, or selection configuration may also raise. The API is not a universal malformed-input-to-JSON converter.

Escalate to the [optional Rust lookup](rust-semantic-definition.md) only when a reference definition is needed. Supply Cargo features, the default-feature choice, and target explicitly. Its result and resource behavior are separate from the shared scanner, and ordinary navigation does not require it.
