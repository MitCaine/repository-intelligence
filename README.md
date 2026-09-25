# Repository Intelligence

The [project direction](docs/project-direction.md) shows the intended
controller/Codex review workflow, source-evidence pipeline, coverage invariant,
and what RI deliberately does not own. The capabilities below describe the
current implementation, which is narrower than that end state.

A small, source-derived function locator for AI-assisted repository navigation.
The common query interface currently supports Python (`ast` plus Tree-sitter
syntax evidence) and Rust (Tree-sitter navigation) files in any local project.
It returns compact function
locations and source hashes without a database or maintained function
dictionary. It does not grant edit authority, resolve a call graph, or replace
checking the relevant source. Other languages are not yet supported.

This is currently a navigation tool, **not yet a complete structural inventory**.
Zero parse errors do not prove every declaration was mapped. Do not use an
absence result or a before/after query difference to qualify all candidate
changes until the explicit per-language mapping contracts and completeness
checks are implemented.

This is the reusable core extracted from the [Poker App](https://github.com/MitCaine/poker-app)
pilot. Poker-specific authority maps, capsule rules, and consumer configuration
belong to Poker, not this package. Earlier benchmark and security machinery is
preserved in Git history but is not part of the current package.

## Use

Python 3.12 or 3.13 is required. The package pins the Tree-sitter runtime
and Python/Rust grammar wheels. Ordinary Rust navigation now uses Tree-sitter
without `rust-analyzer`. The analyzer remains available as an opt-in Rust
source and metadata route when needed. No hosted service is needed. From this
repository:

```sh
PYTHONPATH=src python3.13 -m repository_intelligence.locator \
  /path/to/project --query 'pause resume clock' --limit 8
```

Pass one file instead of a directory to narrow the scan. Add `--json` for
structured output. For a direct file, `--root /path/to/project` confines
identity to that root; a path outside it or a symlink is reported as excluded
without reading bytes. An unsupported file still returns its byte identity, marked
`unsupported`. Directory results report files that could not be indexed and
explicit scan exclusions. A directory scan covers supported files only, so no
result is **not** proof that an unsupported language has no relevant function.
The raw SHA-256 identifies
bytes read, not a verified Git checkout. Lexical call candidates are not
resolved relationships.

The shared command's [versioned result contract](docs/navigation-result-v2.md)
explains source identity, incomplete results, and directory scope. It is for
navigation, not candidate-change qualification.

The Rust-only analyzer command remains available as an opt-in escalation,
`python3.13 -m repository_intelligence.rust_index`. Its output uses a distinct
unversioned result shape (`legacy_rust_query`); that label distinguishes the
protocol, not support status. RI does not interpret project-specific authority
Markdown; callers can combine RI's source locations with their own documents.

## Verify

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3.13 -m unittest discover -s tests
```

The optional installed-wheel check uses two local build-dependency wheels and
the three pinned Tree-sitter wheels and never downloads packages:

```sh
RI_SETUPTOOLS_WHEEL=/path/to/setuptools-79.0.1-py3-none-any.whl \
RI_WHEEL_WHEEL=/path/to/wheel-0.47.0-py3-none-any.whl \
RI_TREE_SITTER_WHEELHOUSE=/path/to/pinned-tree-sitter-wheels \
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 \
python3.13 -m unittest discover -s tests -p test_installed_package.py
```

The [pilot report](docs/rust-function-locator-pilot.md) records earlier Poker
navigation trials and their measurement limits. The
[extraction decision](docs/standalone-core-seam.md) explains why the earlier
research modules are not included.

The [Tree-sitter baseline note](docs/tree-sitter-baseline.md) records pinned
versions, current parity evidence, and the remaining #8 adoption work.
