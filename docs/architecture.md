# Architecture and ownership

RI is an on-demand reader of source, not a maintained symbol database. The normal pipeline is source selection, byte acquisition and identity, one Tree-sitter parse, language extraction, then either navigation ranking or query-independent inventory comparison. Native Rust definition lookup is separate.

## Shared source and parsing

[`scan.py`](../src/repository_intelligence/scan.py) owns language selection, directory traversal, exclusions, regular-file/read limits, and per-file orchestration. It invokes the adapter selected by [`adapters.py`](../src/repository_intelligence/adapters.py). Its read limit is 32,000,000 bytes; its parser limit is 4,000,000 bytes. Failures and unsupported/excluded states are data when the implemented branch can return a packet, not fabricated empty successful indexes.

[`source.py`](../src/repository_intelligence/source.py) owns raw-byte identity, repository-relative paths, algorithm-tagged computed Git blob IDs, and common display-coordinate helpers. Identity describes the bytes supplied to it; Git membership and source stability remain caller responsibilities.

[`structural.py`](../src/repository_intelligence/structural.py) owns installed runtime/grammar metadata, Tree-sitter setup, Python declared-encoding input conversion, and independent ERROR/MISSING diagnostics. `ScanSetup` reuses parser and version setup within one invocation. It is not a persistent source cache or a global shared parser pool. Python raw positions come from actual incremental decoder boundaries; unsupported boundaries fail instead of receiving approximate offsets.

## Language adapters

Each `*_tree_index.py` module owns its language's callable classification, body/bodyless policy, names, ownership, syntactic identity components, attached source envelope, and lexical call hints. The [callable contract](tree-sitter-baseline.md) is the intended reviewed boundary. [Known limitations](known-limitations.md) records current counterexamples.

[`declarations.py`](../src/repository_intelligence/declarations.py) provides small shared primitives: token-preserving syntax keys, exact source-range hashes, named ID assignment, and coverage accounting. It must not decide language semantics. In particular, omitting one declaration from the callable map must not automatically suppress traversal of nested declarations.

The structural declaration summary is a bounded projection of adapter output. It is not an independent second classifier. Independent expected names, slices, and counts in tests are therefore essential. Nested callable ranges may overlap their enclosing callable, while duplicate exact ranges are rejected.

## Navigation and comparison

[`locator.py`](../src/repository_intelligence/locator.py) is the public file/directory query interface and CLI. [`search.py`](../src/repository_intelligence/search.py) owns lexical tokenization, ranking, and display truncation. Ranking must see full extracted evidence before any display limit is applied.

[`inventory.py`](../src/repository_intelligence/inventory.py) collects all selected supported files, including zero-callable files, and compares compatible caller-stable inventories. The digest covers normalized scan policy and file identities, not a signature over trusted authority. File and declaration changes are separate outputs. A compact projection removes repeated presentation data only after comparison; it does not reduce accounting.

The main handoff is source facts, not permission: RI does not decide whether a change is within task scope or whether tests are sufficient. A consumer still reviews the full Git diff and applies its own acceptance rules.

## Optional and legacy paths

[`rust_semantic.py`](../src/repository_intelligence/rust_semantic.py) asks a bounded native definition question using explicit Cargo settings. Provider I/O has deadlines; local pre/post checksums and target-byte observations have stated coverage limits. These do not constitute an atomic snapshot. Its source reads do not route through the shared scanner's 32 MB guard.

`python_index.py` is the standard-library AST reference/fallback. `rust_index.py` retains the older native Rust parsing/query interface. Their result shapes and traversal/resource behavior are not interchangeable with navigation v5. New consumers should use the shared interface unless they explicitly need one of these separate capabilities.

## Keep the design small

Prefer explicit grammar-specific functions and small common utilities. Do not add a universal LSP framework, plugin discovery, a daemon, a database, compiler type resolution, signed receipts, or workflow authority merely to correct syntax mapping. Grammar-aware traversal and well-defined result boundaries are the required mechanisms.
