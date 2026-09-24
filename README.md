# Repository intelligence (Poker checkout)

The reusable orientation surface is `repository_intelligence.rust_index`: it indexes one Rust file with `rust-analyzer parse --json`, returns source-bound function locations, and formats a compact query result. It does not resolve a call graph or attest a Git checkout. The other modules in this distribution are legacy Poker pilot machinery and are not the planned standalone core; see [the seam decision](docs/standalone-core-seam.md).

Supported Python: 3.12 and 3.13 on the tested macOS controller. `rust-analyzer` must be installed separately. Windows and older Python versions are not qualified yet.

## Offline installed-package check

From the Poker repository root, set `RI_SETUPTOOLS_WHEEL` and `RI_WHEEL_WHEEL` to local wheel files matching the pinned build requirements in `pyproject.toml`, then run:

```sh
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 python3.12 scripts/test_repository_intelligence_standalone.py
```

The command makes isolated build and install environments, builds a wheel without network access, installs it without `PYTHONPATH`, and indexes a Rust file in an unrelated temporary consumer directory. It fails if the offline wheels or `rust-analyzer` are missing. It does not build Poker or WASM. The same command can use `python3.13`; use the desired interpreter explicitly. Ordinary test discovery skips this integration check if the wheel inputs are absent.

This checkout has not been separated or published. Do not treat the legacy pilot records, receipts, schemas, or historical benchmark evidence as a general-purpose package contract.
