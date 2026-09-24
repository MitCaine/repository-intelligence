# Standalone orientation core: retention decision

This records the #391 scope decision before #392 changes distribution. It does
not move files, rename imports, or declare the current extracted package safe
to publish independently.

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

The standalone package should keep this module and its direct tests as its
initial executable core. Add authored meaning only where a real task or the
Poker sweep shows it is needed; authored Poker authority remains in Poker's
source/comments and consumer configuration, not in generic Python code.

## Keep historical modules in Poker, not the new core

The current extracted package also contains `acquisition`, `attempts`,
`authority`, `conformance`, `evidence`, `harness`, `identity`, `lineage`,
`oracle`, `qualification`, `receipt`, `registry`, `scope`, `security`, and
`validation`, plus common errors. Their present consumers are the legacy
`scripts/repository_intelligence_pilot.py` reexports, Poker-specific
integration/compatibility tests, and historical benchmark contracts. The
function locator does not import them. Do not copy them into the standalone
orientation package merely because they were previously extracted.

Preserve these files and their accepted history in Poker until #392 supplies a
compatibility-preserving packaging split. Do not maintain two independently
edited copies. If a real future consumer needs one of these interfaces, it
must establish that need and qualify the retained interface separately.

## #391 audit findings and disposition

| Finding | Current disposition |
| --- | --- |
| `oracle.py` finding paths can expose mapping keys | Historical benchmark/oracle module; exclude from standalone core. Do not claim its scanner physically isolates data. Fix before any renewed supported use. |
| `scope.py` accepts a rename without a concrete destination | Historical edit-grant module; exclude. Do not use it to authorize a rename. Fix or reject rename before renewed supported use. |
| `attempts.py` cannot finish a never-started setup attempt | Historical attempt ledger; exclude. Keep the discrepancy with the old fixture visible; fix only if that ledger is retained for execution. |
| `receipt.py` can equate integer schema version `1` with Boolean `True` | Historical generic receipt validator; exclude. Do not use an integer-version receipt as a current orientation-core proof. Fix if retained by a supported consumer. |
| `evidence.py` compares a binding dictionary to itself | Historical evidence validator; exclude. The check proves nothing independent and should be removed if the validator is retained. |

This is a retention decision, not a claim that the existing published package
has already stopped exposing these modules or that their defects are repaired.
#392 must enforce the split and verify actual imports before the standalone
package is released. Until then, the old modules remain Poker-owned historical
compatibility surfaces, not prerequisites for the map or sweep. #390 applies
only if a checkout-backed observer is retained or a new one claims exact Git
worktree identity; the active locator's raw byte digest makes no such claim.
