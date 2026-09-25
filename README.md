# Repository Intelligence

Repository Intelligence (RI) is a local Python package for source navigation and structural change review. It reads current source, locates callables, and compares caller-supplied planning and candidate trees. It does not maintain a database, run a service, grant edit permission, or replace reading the source and full Git diff.

Ordinary operation uses pinned Tree-sitter grammars for Python, Rust, JavaScript/JSX, TypeScript/TSX, Java, Go, C#, C, and C++. A separate, optional Rust API asks `rust-analyzer` to resolve one reference. Native analyzers are not required for ordinary navigation or inventories.

## Current state

The current result contracts are navigation schema **5**, inventory schema **11**, adapter version **5**, and mapping contract `python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v5`. Package metadata remains version `0.1.0`; use the result contracts and a pinned RI revision, not the package version alone, to identify behavior.

PR #61 records 139 passing pinned tests, including the offline installed-wheel check and live Rust lookup. That is recorded verification for that revision, not a guarantee of exhaustive language coverage. Four subsequent C++/C# and identity-handling findings have parser-integrated fixes; [known limitations](docs/known-limitations.md) still apply to declaration deltas.

## Install and navigate

Python 3.12 or newer is required. The recorded exercised hosts are macOS ARM64 with Python 3.12 and 3.13; other platforms are not qualified merely because compatible wheels exist.

From an unrelated consumer project, install one RI checkout into the consumer environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install /path/to/repository-intelligence
.venv/bin/python -m repository_intelligence.locator . \
  --query 'calculate total' --limit 8 --json
```

Installation may download pinned dependencies. [Install and verify](docs/install-and-verify.md) explains the offline path and recorded host details. A non-editable installation must be reinstalled after changing the RI checkout.

Pass a file to narrow a query. Use `--root` to set its identity root. Ambiguous C/C++ headers need an explicit parser:

```sh
.venv/bin/python -m repository_intelligence.locator include/api.h \
  --root . --language cpp --query 'calculate total'
```

For a directory, use repeatable `--header-language include/api.h=cpp` instead. Unselected `.h` files remain visible as unsupported. The locator emits useful partial results, but a zero-match result is not an absence proof. Read JSON status and failure fields; the locator does not encode mapping completeness in its exit status.

## Compare planning and candidate source

Supply stable source trees and the same scan policy on both sides:

```sh
.venv/bin/python -m repository_intelligence.inventory compare \
  /snapshots/planning /snapshots/candidate \
  --assert-stable-materialization --compact-json
```

The stability flag is the caller's assertion, not RI snapshot verification. Without it, inventories are marked non-atomic/incomplete and no comparable delta is emitted. The inventory command returns 0 for complete/comparable results, 2 for incomplete results, and 3 for incompatible results; argument or execution errors can fail separately.

Inventory includes supported in-scope files with zero callables. It reports file and declaration additions, removals, modifications, and unchanged entries. Anonymous positions can shift, and genuinely ambiguous named identities are compared conservatively. Always reconcile with the full changed-file list, including configuration, unsupported languages, imports, and initializers.

## Limits and evidence

The shared scanner limits source acquisition to **32,000,000 bytes**. Larger files are incomplete without byte identity. Its separate **4,000,000-byte** parser-input limit means readable supported files above that limit retain byte identity but are not parsed. Non-regular files are not read. These limits describe the shared scanner, not every legacy/native API.

Raw SHA-256 and declaration hashes identify observed bytes. Computed Git blob IDs do not prove commit membership. Directory reads are non-atomic. C/C++ uses unexpanded source; macro-generated and build-configured program coverage is not claimed. Lexical call candidates are not resolved calls.

## Verify

With pinned dependencies installed, run from the RI checkout:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests
```

The installed-wheel test requires local build wheels and a grammar wheelhouse:

```sh
RI_SETUPTOOLS_WHEEL=/path/to/setuptools-79.0.1-py3-none-any.whl \
RI_WHEEL_WHEEL=/path/to/wheel-0.47.0-py3-none-any.whl \
RI_TREE_SITTER_WHEELHOUSE=/path/to/pinned-tree-sitter-wheels \
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests -p test_installed_package.py
```

A green discovery run can contain skipped optional tests. [Maintenance](docs/maintenance.md) explains verification expectations and contract changes.

## Documentation

Start with the [documentation index](docs/README.md), [consumer guide](docs/consumer-guide.md), [navigation v5 reference](docs/navigation-result-v5.md), or [inventory/delta contract](docs/inventory-delta-v1.md). [Architecture](docs/architecture.md) describes implementation ownership; [callable contracts](docs/tree-sitter-baseline.md) define per-language promises.

RI was extracted from [Poker App](https://github.com/MitCaine/poker-app). Project authority maps, capsule rules, and review decisions remain consumer-owned. The [project direction](docs/project-direction.md), [extraction decision](docs/standalone-core-seam.md), and [historical pilot](docs/rust-function-locator-pilot.md) explain the intent and history, not additional current capabilities. RI has no project license file yet; public redistribution requires a separate licensing decision.
