# Consumer guide

RI supplies source evidence. The caller owns source materialization, full diff review, project policy, and acceptance. Use a separate installed RI package rather than copying its modules into each consumer repository. Pin the checkout revision and keep the emitted parser and contract metadata with saved observations.

For the surrounding capsule handoff, qualification, independent review, and
native subagent completion, see the [controller workflow](capsule-controller-workflow.md).

## Install into a consumer environment

Python 3.12 or newer is required. From the project being inspected:

```sh
python3.14 -m venv .venv-ri
.venv-ri/bin/python -m pip install "/path/to/Repository Intelligence"
.venv-ri/bin/python -m repository_intelligence.locator . --query 'calculate total'
```

The pinned Tree-sitter runtime and nine grammar distributions are normal
installation dependencies. Native analyzers are optional. Keep one RI checkout
and install it into each consumer environment instead of copying source modules.
A non-editable install must be reinstalled after changing that checkout. Record
the selected RI revision; keep it fixed during a planning/candidate comparison.

For an offline install, provide a compatible RI wheel and its dependency wheels:

```sh
.venv-ri/bin/python -m pip install --no-index --find-links /path/to/wheelhouse \
  /path/to/repository_intelligence-0.1.0-py3-none-any.whl
```

The [retained bundle recipe](maintenance.md#retained-wheel-bundles) creates that
wheel alongside its pinned dependencies and a checksum receipt. Check the
receipt's commit, `clean_checkout`, interpreter/platform, and wheel hashes
before adoption. RI still declares package version `0.1.0`, so a wheel built
from a newer commit can have the same filename as an older one.

For an existing consumer, prepare a fresh candidate environment at its final
path and install the selected bundle there. Run `pip check` and the consumer's
real compatibility tests before changing its interpreter setting. Keep the old
environment as the rollback target. If an in-place update is unavoidable,
reinstall the wheel explicitly even when its package version is unchanged:

```sh
candidate/bin/python -m pip install --force-reinstall --no-index \
  --find-links /path/to/bundle \
  /path/to/bundle/repository_intelligence-0.1.0-py3-none-any.whl
candidate/bin/python -m pip check
```

After installation, confirm the installed RI dependency metadata and parser
versions match the bundle receipt. Generate both sides of a new planning/candidate
comparison with the same accepted RI environment; do not compare observations
from different parser pins.

[Maintenance](maintenance.md#offline-package-verification) describes building and
verifying that distribution offline. Its [host record](maintenance.md#verification-scope)
distinguishes exercised environments from package metadata compatibility.

## Navigate before expanding scope

Below, `python` means the interpreter into which RI was installed (for example
`.venv-ri/bin/python`); activate that environment or substitute its full path. Replace the example paths and query words with the consumer's paths and task terms.

```sh
python -m repository_intelligence.locator /path/to/project \
  --query 'pause resume clock' --limit 8
python -m repository_intelligence.locator /path/to/project/src/clock.py \
  --root /path/to/project --query 'pause resume clock' --json
```

Search tokenizes Unicode words and identifiers, including common camel-case boundaries. It ranks full extracted names, aliases, qualified names, documentation, and lexical call candidates before shortening displayed fields. This is lexical ranking, not embeddings, type resolution, or a guarantee that all relevant code was found. Query limits are 1-20, default 8.

For full per-file callable records without a query, use the library API:

```python
from pathlib import Path
from repository_intelligence.locator import index_file, query_path

root = Path('/path/to/project')
packet = index_file(root / 'src/clock.py', root=root)
assert packet['schema_version'] == 7
if packet['mapping_status'] == 'navigation_only':
    for entry in packet['functions']:
        print(entry['qualified_name'], entry['byte_range'])

result = query_path(root, 'pause resume clock', limit=8)
# Inspect mapping_status, failures, scan_scope, and each matched file's metadata.
```

Do not use the bounded `structural.declarations` array as a full inventory. Directory query JSON also contains per-file evidence for the scan, so a small match limit does not impose a small total JSON size. The [navigation reference](navigation.md) explains these shapes.

For a normal capsule task, carry the relevant generated matches, exact source
identity, and parser/coverage status into **Source and scope**, then inspect those
locations and related callers/interfaces/tests directly. Link each implementation
step to its proof entry under **Checks**. The [daily source-preparation contract](start-an-issue.md#task-directed-source-preparation)
defines the required invocation, retained output, reuse and exception handling.

## Choose headers and exclusions deliberately

A direct header query accepts `--language c` or `--language cpp`. A directory scan accepts exact relative header paths instead:

```sh
python -m repository_intelligence.locator /path/to/project \
  --header-language include/api.h=cpp \
  --exclude-directory generated --query 'calculate total' --json
```

`--header-language` is repeatable; it is not automatic language detection. `--exclude-directory` accepts a simple directory name and excludes every directory with that name, not one path or a glob. Hidden names, `target`, `node_modules`, `venv`, `__pycache__`, symlinks, and nested repositories are already excluded by the shared traversal policy. Do not assume RI applies `.gitignore` or scans only Git-tracked files.

Unsupported source-like paths are reported for the recognized suffix set; other file types are counted. This does not enumerate every possible programming language. A direct supported-extension/language conflict returns an unsupported packet, rather than silently changing parsers. Direct-file queries do not apply the directory exclusion/header-selection options.

## Compare stable source trees

Prepare planning and candidate trees through the consumer's existing workflow. Keep both stable for the entire scan. RI does not create or lock those snapshots.

```sh
python -m repository_intelligence.inventory scan /snapshots/planning \
  --logical-root app --assert-stable-materialization --json
python -m repository_intelligence.inventory compare \
  /snapshots/planning /snapshots/candidate --logical-root app \
  --header-language include/api.h=cpp --exclude-directory generated \
  --assert-stable-materialization --compact-json
```

The compare command applies the selected policy to both roots. Absolute paths may differ; logical scope, contracts, and parser metadata must agree. Actual observed excluded directories can differ without changing the policy. Exclusions overlapping mapped files on the opposite side block comparison in
either direction, so unobserved source is not treated as an addition or deletion.

The library equivalent is:

```python
from pathlib import Path
from repository_intelligence.inventory import inventory_tree, compare_inventories

policy = dict(stable=True, logical_root='app',
              language_choices={'include/api.h': 'cpp'},
              excluded_directories=('generated',))
planning = inventory_tree(Path('/snapshots/planning'), **policy)
candidate = inventory_tree(Path('/snapshots/candidate'), **policy)
assert planning['inventory_schema_version'] == 16
assert candidate['inventory_schema_version'] == 16
delta = compare_inventories(planning, candidate)
if delta['status'] != 'comparable_candidate_delta':
    raise RuntimeError((delta['status'], delta['mismatches']))
# Review delta['file_changes'] and delta['declaration_changes'] with the full diff.
```

A declaration marked unchanged has the same structural identity and hashed source unit, not necessarily unchanged program behavior. Imports, enclosing containers, configuration, build conditions, and unsupported files can affect behavior. File-level changes remain important when the declaration delta is empty.

## Handle results and failures

The locator's successful process exit means it emitted a packet, not that the packet is complete. Read `mapping_status` and evidence fields. Incomplete navigation can still provide useful matches. Inventory scan/compare uses exit codes 0 for complete/comparable, 2 for incomplete, and 3 for incompatible; invalid CLI arguments and unexpected errors have separate failure paths. Do not convert every nonzero exit into an empty result.

A supported file larger than 4,000,000 but no larger than 32,000,000 bytes retains identity and reports `SourceLimitExceeded`. A file beyond 32,000,000 bytes reports `SourceReadLimitExceeded` without identity. Non-regular files report `NonRegularFile` when that check is reached. Read failures also have no byte identity. Unsupported files receive identity only when acquisition succeeds within its limit.

A source root with no selected supported paths, recognized unsupported paths, traversal failures, or exclusions raises `ValueError`; do not interpret that as proof of absent functionality. An exclusion-only root returns an `excluded` packet with its observed scope. Invalid paths, query terms, limits, or selection configuration may also raise. The API is not a universal malformed-input-to-JSON converter.

For parser gaps, use the explicit [native syntax handoff](native-analysis.md) and
retain the original structural result. For established-project issue execution, use
[Start an issue](start-an-issue.md).

Escalate to the [optional Rust lookup](native-analysis.md) only when a reference definition is needed. Supply Cargo features, the default-feature choice, and target explicitly. Its result and resource behavior are separate from the shared scanner, and ordinary navigation does not require it.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| Command or field differs from this guide | Check which environment imports RI and its pinned checkout revision; reinstall an intentionally updated checkout |
| Zero or irrelevant matches | Refine task terms or narrow to the owning source; inspect code rather than assuming absence |
| Incomplete syntax with usable neighbors | Retain partial evidence; ask a specific native syntax or semantic question if needed |
| Empty/no-source directory error | Inspect the selected root, supported suffixes, header choices, exclusions, and traversal failures |
| Incompatible inventory pair | Compare the returned mismatch reasons; regenerate both sides with equal contracts and policy |
| Outdated line locations after edits | Refresh the working-source result while retaining immutable planning observations |

Poker's former `--authority-dir` example does not apply to the current shared
locator. Authored authority remains a separate consumer input; see the
[issue-start procedure](start-an-issue.md).
