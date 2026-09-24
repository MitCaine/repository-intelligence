# Repository Intelligence

A small, source-derived function locator for AI-assisted repository navigation.
It parses current Rust files with `rust-analyzer`, returns compact function
locations and source hashes, and can attach candidate guidance from an
existing authored authority directory. It creates no database or maintained
function dictionary. It does not grant edit authority, resolve a call graph,
or replace checking the relevant source.

This is the reusable core extracted from the [Poker App](https://github.com/MitCaine/poker-app)
pilot. Poker-specific authority maps, capsule rules, and consumer configuration
belong to Poker, not this package. Earlier benchmark and security machinery is
preserved in Git history but is not part of the current package.

## Use

Python 3.12 or 3.13 and a local `rust-analyzer` executable are required. No
hosted service or Python runtime dependency is needed. From this repository:

```sh
PYTHONPATH=src python3.13 -m repository_intelligence.rust_index \
  /path/to/rust/project --query 'pause resume clock' --limit 8
```

For one large file, pass its path instead of a directory. Add `--json` for
structured output. Add `--authority-dir /path/to/project/authority` only if the
consumer has authored `Anchors:` entries; these are candidate guidance, not
source truth. Results report parse errors and files that could not be indexed.
The raw SHA-256 identifies bytes read, not a verified Git checkout. Lexical
call candidates are not resolved relationships.

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

The [pilot report](docs/rust-function-locator-pilot.md) records Poker navigation
trials and their measurement limits. The [extraction decision](docs/standalone-core-seam.md)
explains why the earlier research modules are not included.
