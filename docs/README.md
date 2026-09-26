# RI documentation

These guides describe the current implementation. The contracts are navigation v5, inventory schema 11, mapping contract v8, and adapter version 8. Follow the [known limitations](known-limitations.md) alongside the intended callable contract; a passing counter is not proof that an adapter has no logic defect.

## Using RI

[Install and verify](install-and-verify.md) covers environment setup, offline packaging, and recorded hosts. The [consumer guide](consumer-guide.md) covers navigation, stable source comparison, result handling, and troubleshooting. The [navigation v5 reference](navigation-result-v5.md) describes the current file/directory packets without requiring readers to reconstruct several historical versions. [Inventory and delta](inventory-delta-v1.md) specifies comparison and compact output. [Optional Rust definition lookup](rust-semantic-definition.md) describes the separate native API.

## Maintaining RI

[Architecture](architecture.md) assigns implementation responsibilities. [Maintenance](maintenance.md) describes regression design, pinned grammar upgrades, packaging checks, and version changes. [Tree-sitter callable contracts](tree-sitter-baseline.md) enumerate promised language forms. [Known limitations](known-limitations.md) separates deliberate boundaries from outstanding correctness findings.

## Direction and historical material

[Project direction](project-direction.md) describes the intended controller workflow and non-goals. [Extraction decision](standalone-core-seam.md), [pilot report](rust-function-locator-pilot.md), and [adoption observations](adoption-observations.md) record prior evidence with its original scope. Navigation v1-v4 documents remain historical references; do not use them as the current packet specification.
