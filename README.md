# Repository Intelligence

A small, source-derived function locator for AI-assisted repository navigation.
The common query interface currently supports Python (`ast`) and Rust
(`rust-analyzer`) files in any local project. It returns compact function
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

Python 3.12 or 3.13 is required. A local `rust-analyzer` executable is also
required when scanning Rust; Python source needs no external parser. No hosted
service or Python runtime dependency is needed. From this repository:

```sh
PYTHONPATH=src python3.13 -m repository_intelligence.locator \
  /path/to/project --query 'pause resume clock' --limit 8
```

Pass one `.py` or `.rs` file instead of a directory to narrow the scan. Add
`--json` for structured output. Directory results report files that could not
be indexed; an unsupported single-file type is rejected explicitly. A directory
scan covers supported files only, so no result is **not** proof that an
unsupported language has no relevant function. The raw SHA-256 identifies
bytes read, not a verified Git checkout. Lexical call candidates are not
resolved relationships.

The earlier Rust-only command remains available as
`python3.13 -m repository_intelligence.rust_index`. Its optional
`--authority-dir` consumes Poker-style authored Markdown anchors as *candidate*
guidance. A project-neutral guidance format for the shared command is still
planned; guidance is never needed to use source-derived lookup.

## Verify

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3.13 -m unittest discover -s tests
```

The optional installed-wheel check uses two local build-dependency wheels and
never downloads packages:

```sh
RI_SETUPTOOLS_WHEEL=/path/to/setuptools-79.0.1-py3-none-any.whl \
RI_WHEEL_WHEEL=/path/to/wheel-0.47.0-py3-none-any.whl \
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 \
python3.13 -m unittest discover -s tests -p test_installed_package.py
```

The [pilot report](docs/rust-function-locator-pilot.md) records earlier Poker
navigation trials and their measurement limits. The
[extraction decision](docs/standalone-core-seam.md) explains why the earlier
research modules are not included.
