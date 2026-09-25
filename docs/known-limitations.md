# Known limitations

The four follow-up logic findings after PR #61 were corrected in adapter version 5 and mapping contract v5; later variants were corrected in version 6. The deliberate boundaries below still apply.

Navigation is lexical and bounded; no matches is not proof of absence. Inventories cover the documented source constructs in selected supported files, not the whole compiled program. C/C++ macros, conditionals, includes, and build settings remain unexpanded. Imports, initializers, configuration, enclosing containers, and unsupported files can change behavior without a callable delta. Full changed-file review remains required.

Working-tree reads are non-atomic. `stable=True` is the caller's assertion. Computed hashes are byte identities, not attestation. Anonymous offsets may change after preceding edits; ambiguous named declarations are compared conservatively. Default exclusions are explicit but do not implement `.gitignore` or Git-tracked-file selection.

The 32,000,000-byte acquisition limit and 4,000,000-byte parser limit belong to the shared scanner. Optional native and legacy entry points have separate behavior. Recorded platform verification is limited to the hosts described in [install and verify](install-and-verify.md).

## Open audit follow-ups

The stateful-encoding AST fallback and contradictory comparison packets found in the September 2026 audit are corrected with exact-byte and changed-candidate regressions. Additional C++/JavaScript identity variants are tracked in [issue #68](https://github.com/MitCaine/repository-intelligence/issues/68), and optional-versus-required Rust I/O behavior is tracked in [issue #69](https://github.com/MitCaine/repository-intelligence/issues/69). Until those pass parser-integrated or controlled-I/O regressions, treat affected declaration deltas and native observations as potentially incomplete; inspect source and the full changed-file list.

## Corrected follow-up findings

Parser-integrated regressions now cover a lambda nested inside a deleted C++ member, C++ reference-return and reference-parameter identity, comments between parameters in C++ and Java, comments between C# generic type parameters, and attribute text containing `static` on C# constructors. The fixes preserve the enclosing bodyless classification, ignore comment extras when constructing signatures and arity, and use actual C# modifier syntax. These fixtures verify the specified forms, not every possible declarator or grammar variant.
