# Standalone orientation core: retention decision

Historical record. Commands, capabilities, counts, and source locations below
describe the recorded revision. Use the [current documentation](../README.md)
for operation; these observations do not establish current qualification.

Historical extraction record: this describes the #391 decision at that revision,
not the current package inventory. See [architecture](../architecture.md) for the
current shared scanner and language adapters.

This records the #391 scope decision and its implementation. The working tree
now retains only the Rust locator in the Python package. Historical pilot code,
security modules, and extraction ledgers remain recoverable from Git history.
This does not by itself qualify publication of a separate repository.

## Small interface to retain

The working orientation module is `rust_index.py`: `index_file(path)` reads one
Rust file, asks the locally installed `rust-analyzer` to parse those exact
bytes, and returns function locations with a raw SHA-256 and Git-blob digest.
`query(index, terms, limit)` selects a bounded packet; `format_compact` and the
CLI present it. The caller still supplies task intent and edit authority and
checks current source before making behavioral claims. This interface does not
certify that a worktree equals a Git commit, resolve calls semantically, or
store a durable index. The ten-task capsule-first trial in
`rust-function-locator-pilot.md` supports retaining this module.

The standalone package keeps this module and its direct tests as its initial
executable core. Add authored meaning only where a real task or the
Poker sweep shows it is needed; authored Poker authority remains in Poker's
source/comments and consumer configuration, not in generic Python code.

## Historical modules retired from the working tree

The former extracted package contained `acquisition`, `attempts`,
`authority`, `conformance`, `evidence`, `harness`, `identity`, `lineage`,
`oracle`, `qualification`, `receipt`, `registry`, `scope`, `security`, and
`validation`, plus common errors. Their consumers were the legacy
`scripts/repository_intelligence_pilot.py` reexports, Poker-specific
integration/compatibility tests, and historical benchmark contracts. The
function locator does not import them. They are no longer in the working tree
or the standalone package.

Their accepted history remains in Poker Git. If a real future consumer needs
one of these interfaces, it must establish that need and qualify a restored
interface separately; do not silently reintroduce the whole pilot.

## #391 audit findings and disposition

| Finding | Current disposition |
| --- | --- |
| `oracle.py` finding paths can expose mapping keys | Historical benchmark/oracle module; exclude from standalone core. Do not claim its scanner physically isolates data. Fix before any renewed supported use. |
| `scope.py` accepts a rename without a concrete destination | Historical edit-grant module; exclude. Do not use it to authorize a rename. Fix or reject rename before renewed supported use. |
| `attempts.py` cannot finish a never-started setup attempt | Historical attempt ledger; exclude. Keep the discrepancy with the old fixture visible; fix only if that ledger is retained for execution. |
| `receipt.py` can equate integer schema version `1` with Boolean `True` | Historical generic receipt validator; exclude. Do not use an integer-version receipt as a current orientation-core proof. Fix if retained by a supported consumer. |
| `evidence.py` compares a binding dictionary to itself | Historical evidence validator; exclude. The check proves nothing independent and should be removed if the validator is retained. |

The removed modules' defects are not repaired; the modules are unsupported.
The installed-wheel test asserts that only the locator ships, but that check
still requires the pinned offline build wheels and must pass before a separate
package is released. #390 applies
only if a checkout-backed observer is retained or a new one claims exact Git
worktree identity; the active locator's raw byte digest makes no such claim.
