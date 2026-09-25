# Optional Rust definition resolution

Routine RI navigation and inventories use Tree-sitter and do not launch a
language server. When a task actually needs the definition of one Rust
reference, `resolve_definition` asks a locally installed `rust-analyzer` the
LSP `textDocument/definition` question. This is a narrow proof, not a generic
language-server framework or a replacement for the legacy Rust parser route.

```python
from pathlib import Path
from repository_intelligence.rust_semantic import resolve_definition

result = resolve_definition(
    Path("/path/to/cargo-project"),
    Path("/path/to/cargo-project/src/lib.rs"),
    line=42, column=17,                 # 1-based Unicode-character position
    features=(), no_default_features=False,
    target="aarch64-apple-darwin",     # choose the project's actual target
)
```

The project root must contain `Cargo.toml`; the source must be a Rust file
inside it. Pass the Cargo feature names, default-feature choice, and target
explicitly. A working local `rust-analyzer` executable is required only for
this call. The result names its analyzer version, configuration, reference
byte hash, local Rust/Cargo-input digest, analyzer workspace status, and each
returned target's URI, range, and byte identity when readable. It says
`resolved` when a target was returned, `unresolved` when none was returned,
and `incomplete_changed_source` if checked local inputs changed during the
question. An analyzer failure raises an exception; it is not an absence proof.
Target bytes are captured before the final local checksum. A local target's
`byte_binding` says `checked_against_final_local_snapshot` only after that
check passes **and** the target path and observed bytes match a file included
in the final snapshot. Project-local targets omitted by the snapshot (for
example under `target/` or through a symlink) remain
`post_analysis_observation`. External or unreadable targets also remain
`post_analysis_observation`: their bytes, if available, are not verified to
match what the analyzer used. None of these checks makes the working tree
atomic.

The snapshot is a non-atomic checksum of local `.rs` files, Cargo manifests
and lockfiles, Rust toolchain files, and `.cargo` configuration below the
project root. It excludes external dependencies and the sysroot. Build
scripts and procedural macros are disabled for this proof. A resolved target
answers only this reference under this configuration: it does not certify all
build variants, dynamic relationships, generated code, or semantic
completeness of the repository. RI reports evidence; the controller decides
what source to inspect and whether the evidence is enough for a task.
