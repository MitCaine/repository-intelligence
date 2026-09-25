# Install and verify in another project

RI is a local Python package. The normal path needs no hosted account, service,
database, generated dictionary, or native language analyzer. Keep one RI checkout;
install that checkout into each consumer environment rather than copying its
`src/` tree into other repositories.

From an unrelated project directory on a host with Python 3.12 or 3.13:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install "/path/to/Repository Intelligence"
.venv/bin/python -m repository_intelligence.locator . --query 'calculate total' --json
```

Replace the checkout path and query with your own. This install uses ordinary
package downloads if its pinned wheels are not cached. The nine grammar wheels
and one Tree-sitter runtime wheel are required baseline dependencies; native
analyzers such as `rust-analyzer` are not. Direct result JSON reports the
installed runtime, grammar, grammar ABI, and adapter version. The separate
`repository_intelligence.inventory` command reports source-level coverage and
candidate deltas; it does not attest to a Git checkout or authorize edits.

## Offline verification and exercised hosts

The repository's installed-package test builds a wheel, installs it with
`--no-index` in a fresh environment, and queries an unrelated mixed-language
consumer. It checks every pinned Tree-sitter distribution and each shipped
language family's runtime/grammar/adapter version. Supply the local wheelhouse and two
build-dependency wheels as shown in the [README](../README.md#verify), then run
the full test suite with `RI_REQUIRE_STANDALONE=1`.

The full suite and offline installed-wheel check have passed on macOS ARM64
with Python 3.12.13 and 3.13.15. The package metadata allows Python 3.12 and
newer, but other Python/host combinations have not been qualified here;
particularly, do not infer Windows support from wheel availability alone.
Rust-analyzer 1.97.1 was available for its separate optional fixture tests on
this host. Ordinary structural queries and the offline consumer test did not
require it. Other native analyzers are not bundled or claimed as tested.

## Redistribution note

The ten installed baseline wheels each contain a license file in their
distribution metadata; the grammar distributions identify MIT in their
metadata, while the Tree-sitter runtime wheel's metadata carries a license
file without a `License` field. This is a packaging observation, not a legal
clearance. RI itself has no project license file yet. Before any public release
or redistribution, decide RI's license and review the exact bundled and
transitive license notices. Private local use does not require publishing RI.
