# Repository Intelligence

The [project direction](docs/project-direction.md) shows the intended
controller/Codex review workflow, source-evidence pipeline, coverage invariant,
and what RI deliberately does not own. The capabilities below describe the
current implementation, which is narrower than that end state.

A small, source-derived navigation and structural-inventory package for
AI-assisted work in unrelated repositories.
The common query interface currently supports Python, Rust, JavaScript, JSX,
TypeScript, TSX, Java, Go, C#, C, and C++ through
Tree-sitter navigation in any local project. The Python standard-library AST
adapter remains available directly as a reference/fallback.
It returns compact function
locations and source hashes without a database or maintained function
dictionary. It does not grant edit authority, resolve a call graph, or replace
checking the relevant source. Other languages are not yet supported.

Direct queries are navigation-only; a zero-match result is not an absence
proof. The separate inventory command checks the documented source-level
callable contract for supported files and compares stable materializations
supplied by the caller. Neither result proves semantic resolution or, for
C/C++, which declarations a configured build will compile.

This is the reusable core extracted from the [Poker App](https://github.com/MitCaine/poker-app)
pilot. Poker-specific authority maps, capsule rules, and consumer configuration
belong to Poker, not this package. Earlier benchmark and security machinery is
preserved in Git history but is not part of the current package.

## Use

The package requires Python 3.12 or newer; macOS ARM64 Python 3.12 and 3.13
are the combinations verified so far. The package pins the Tree-sitter runtime
and pinned language grammar wheels. Ordinary navigation uses Tree-sitter
without `rust-analyzer`. The analyzer remains available as an opt-in Rust
source and metadata route when needed. No hosted service is needed. From this
repository:

```sh
PYTHONPATH=src python3.13 -m repository_intelligence.locator \
  /path/to/project --query 'pause resume clock' --limit 8
```

For a separate project, follow the [local install and verification guide](docs/install-and-verify.md).

Pass one file instead of a directory to narrow the scan. Add `--json` for
structured output. For a direct file, `--root /path/to/project` confines
identity to that root; a path outside it or a symlink is reported as excluded
without reading bytes. An ambiguous direct file (for example, `snippet.h`)
stays `unsupported` unless an explicit shipped `--language` selects its parser.
Conflicting selections for known extensions are rejected. `.h` is deliberately
ambiguous: choose `--language c` or `--language cpp` for a C/C++ header; a
directory scan does not guess its language. An unsupported file still returns
its byte identity, marked `unsupported`.
Directory results report files that could not be indexed and
explicit scan exclusions. A directory scan covers supported files only, so no
result is **not** proof that an unsupported language has no relevant function.
The raw SHA-256 identifies
bytes read, not a verified Git checkout. Lexical call candidates are not
resolved relationships.

The shared command's [versioned result contract](docs/navigation-result-v4.md)
explains source identity, incomplete results, and directory scope. It is for
navigation, not candidate-change qualification.

Parsed entries carry exact byte ranges and declaration hashes, plus the
installed parser/runtime/grammar/adapter versions. Anonymous-callable IDs
include source positions and may shift after unrelated preceding edits.
Unsupported files have byte identity but no structural interpretation;
excluded paths are reported without reading their bytes. Directory scans read
a mutable working tree non-atomically. The [callable contracts](docs/tree-sitter-baseline.md)
state each language's source-level promise and limits.

The query-independent [structural inventory and candidate delta](docs/inventory-delta-v1.md)
records all supported in-scope source files, including zero-callable files.
Planning-to-candidate comparison requires compatible, caller-supplied stable
materializations; RI reports factual changes and does not authorize them. The
`python3.13 -m repository_intelligence.inventory` command provides bounded
compact or full JSON output for controller inspection.

The public locator is the normal navigation interface. Its shared scan seam
selects files, records exclusions/failures, reads exact bytes, and invokes the
explicit adapter registry; navigation ranks the resulting callables while
inventory records and compares them. The 4 MB limit bounds parser input, not
file identity acquisition: RI still reads an oversized file to report its
exact byte hash and an incomplete mapping. A pre-read size skip would discard
that identity and is not part of this seam. The Rust-only
`rust_index` command remains an opt-in native parsing route with its existing
distinct unversioned directory result (`legacy_rust_query`). RI does not
interpret project-specific authority Markdown; callers can combine RI's
source locations with their own documents.

For a specific Rust reference whose definition matters, the separate
[semantic definition proof](docs/rust-semantic-definition.md) asks
`rust-analyzer` one opt-in question and labels its answer separately from
structural or lexical candidates.

## Verify

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3.13 -m unittest discover -s tests
```

The optional installed-wheel check uses two local build-dependency wheels and
the ten pinned Tree-sitter wheels and never downloads packages:

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

[Cross-project observations](docs/adoption-observations.md) show read-only
navigation in two non-Poker, mixed-language repositories. The closed
[project charter issue #1](https://github.com/MitCaine/repository-intelligence/issues/1)
records the extraction-era Rust baseline; the current shared contracts and
language adapters supersede that historical package description.

The [Tree-sitter baseline note](docs/tree-sitter-baseline.md) records pinned
versions, current coverage contracts, and fixture evidence.
