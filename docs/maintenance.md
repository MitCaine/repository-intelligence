# Maintenance and verification

The source and current contract are the implementation authority. Package version `0.1.0` alone does not identify the semantics of the successive navigation/inventory revisions. Record the RI commit, Python/platform, installed dependency versions, test command, and skips when reporting verification.

## Baseline tests

Install RI's pinned dependencies from `pyproject.toml` before running discovery:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests
```

PR #61 records 139 passing tests on its pinned environment, including installed-wheel and live Rust verification. A later pass with optional tests skipped is not equivalent evidence. Native tests depend on the required Rust tools being present; installed-wheel verification depends on its local wheel inputs. Report each outcome separately.

The offline package check creates fresh build and consumer environments, builds the RI wheel, verifies shipped modules and pinned grammars, and exercises an unrelated mixed-language consumer:

```sh
RI_SETUPTOOLS_WHEEL=/path/to/setuptools-79.0.1-py3-none-any.whl \
RI_WHEEL_WHEEL=/path/to/wheel-0.47.0-py3-none-any.whl \
RI_TREE_SITTER_WHEELHOUSE=/path/to/pinned-tree-sitter-wheels \
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests -p test_installed_package.py
```

The wheelhouse must contain wheels compatible with the selected interpreter/platform. The nine grammar distributions plus Tree-sitter runtime are required dependencies. The `RI_REQUIRE_STANDALONE` flag makes missing package-test prerequisites fail rather than silently skip that check; it does not force unavailable native Rust tests to execute. Preserve the recorded host limitations in [install and verify](install-and-verify.md).

## Design regressions around invariants

For extraction changes, specify expected qualified owners, declaration kinds, and complete raw source slices independently of production helpers. Recomputing a hash from a reported range is necessary consistency checking, but cannot prove the range itself is correct. Counter agreement likewise cannot prove that traversal reached all promised nodes.

Use paired planning/candidate fixtures. A body edit should modify a stable named declaration. A harmless comment or local parameter rename must not accidentally create a different identity where the identity contract excludes that detail. Changing attached declaration syntax must affect its observation. Anonymous offset changes and genuinely ambiguous duplicate names should continue following the documented conservative policy.

Combine grammar forms rather than testing only isolated features: deleted declarations with lambda defaults; reference declarators with named parameters; comments between parameters and generic type parameters; annotations containing keyword text; overloads containing local classes. Verify nested descendants are still visited when an enclosing declaration is bodyless or unhandled.

Failure tests should preserve usable partial evidence, reject contradictory comparison inputs, and exercise read/parse boundaries separately. Use sparse oversized files and fake stalled providers instead of allocating excessive fixtures or requiring native tools for transport-only tests. Do not accept a broad exception handler as a substitute for understanding which optional operation can fail.

## Change contracts deliberately

The current implementation emits navigation schema 5, inventory schema 11, mapping contract v8, and adapter version 8. Changes to identity, source envelopes, classification, or accounting need an explicit compatibility decision and corresponding version updates before old/new observations are compared. Update the current reference, callable contract, README, fixtures, and any exact-version packaging assertions together. Retain historical navigation pages for existing consumers rather than silently rewriting their old meanings.

A grammar-pin change requires reviewing upstream `node-types.json` and relevant grammar rules at the exact tags, not only incrementing a dependency string. The existing `scripts/check_grammar_nodes.py` covers its documented Python/Rust checks; it is not a complete all-language upgrade verifier. Run affected language fixtures, common navigation/inventory tests, and installed-wheel verification after an upgrade. Do not assume every declarator child has a field name or every named child is a parameter.

## Acceptance and cleanup

Confirm each outstanding item in [known limitations](known-limitations.md) with a parser-integrated regression before marking it fixed. Add an exact mixed-language P-to-C expectation and inspect the complete diff. Keep the documentation-only refresh separate from runtime corrections. Public release and licensing remain separate decisions; do not invent a license or broaden platform-support claims as part of a correctness patch.
