# Maintenance and verification

The source and current contract are the implementation authority. Package version `0.1.0` alone does not identify the semantics of the successive navigation/inventory revisions. Record the RI commit, Python/platform, installed dependency versions, test command, and skips when reporting verification.

## Baseline tests

Install RI's pinned dependencies from `pyproject.toml` before running discovery:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests
```

Native tests depend on the required Rust tools being present; installed-wheel verification depends on its local wheel inputs. Report each outcome separately.

## Offline package verification

The offline package check creates fresh build and consumer environments, builds the RI wheel, verifies shipped modules and pinned grammars, and exercises an unrelated mixed-language consumer:

```sh
RI_SETUPTOOLS_WHEEL=/path/to/setuptools-79.0.1-py3-none-any.whl \
RI_WHEEL_WHEEL=/path/to/wheel-0.47.0-py3-none-any.whl \
RI_TREE_SITTER_WHEELHOUSE=/path/to/pinned-tree-sitter-wheels \
RI_REQUIRE_STANDALONE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3.13 -m unittest discover -s tests -p test_installed_package.py
```

The wheelhouse must contain wheels compatible with the selected interpreter/platform. The nine grammar distributions plus Tree-sitter runtime are required dependencies. The `RI_REQUIRE_STANDALONE` flag makes missing package-test prerequisites fail rather than silently skip that check; it does not force unavailable native Rust tests to execute. See the [verification scope](#verification-scope) below for exercised hosts.

## Automated verification

[The Verify workflow](../.github/workflows/verify.yml) runs on pull requests,
main pushes, and manual dispatch with macOS 15 and Python 3.12/3.13. It reads
build/runtime pins from `pyproject.toml`, downloads compatible wheels, then
requires the offline installed-consumer test during full discovery. Missing
package-test prerequisites fail CI. Native Rust tests retain their explicit
tool-presence conditions; the verbose log records skips. A configured workflow
is not evidence of a hosted pass or new platform qualification.

Dependency caching follows the upstream [setup-python guidance](https://github.com/actions/setup-python#caching-packages-dependencies).
The token has read-only contents access and checkout credentials are not retained.
No workflow publishes packages, merges changes, or alters repository settings.

## Design regressions around invariants

For extraction changes, specify expected qualified owners, declaration kinds, and complete raw source slices independently of production helpers. Recomputing a hash from a reported range is necessary consistency checking, but cannot prove the range itself is correct. Counter agreement likewise cannot prove that traversal reached all promised nodes.

Use paired planning/candidate fixtures. A body edit should modify a stable named declaration. A harmless comment or local parameter rename must not accidentally create a different identity where the identity contract excludes that detail. Changing attached declaration syntax must affect its observation. Anonymous offset changes and genuinely ambiguous duplicate names should continue following the documented conservative policy.

Combine grammar forms rather than testing only isolated features: deleted declarations with lambda defaults; reference declarators with named parameters; comments between parameters and generic type parameters; annotations containing keyword text; overloads containing local classes. Verify nested descendants are still visited when an enclosing declaration is bodyless or unhandled.

Failure tests should preserve usable partial evidence, reject contradictory comparison inputs, and exercise read/parse boundaries separately. Use sparse oversized files and fake stalled providers instead of allocating excessive fixtures or requiring native tools for transport-only tests. Do not accept a broad exception handler as a substitute for understanding which optional operation can fail.

## Change contracts deliberately

The [navigation reference](navigation.md#current-result-contracts) owns the current version table. Changes to identity, source envelopes, classification, or accounting need an explicit compatibility decision and corresponding version updates before old/new observations are compared. Update the current reference, callable contract, README, fixtures, and any exact-version packaging assertions together. Maintain the compatibility summary and exact historical recovery link in
[navigation](navigation.md#compatibility-history); do not create another versioned
copy of the full reference or reinterpret old packets under new semantics.

A grammar-pin change requires reviewing upstream `node-types.json` and relevant grammar rules at the exact tags, not only incrementing a dependency string. The existing `scripts/check_grammar_nodes.py` covers its documented Python/Rust checks; it is not a complete all-language upgrade verifier. Run affected language fixtures, common navigation/inventory tests, and installed-wheel verification after an upgrade. Do not assume every declarator child has a field name or every named child is a parameter.

## Acceptance and cleanup

Reproduce correctness findings with parser-integrated regressions before marking
them fixed. Deliberate [limitations](limitations.md) are not promises of planned features. Add an exact mixed-language P-to-C expectation and inspect the complete diff. Record documentation consolidation separately from later runtime corrections in the audit record. Public release and licensing remain separate decisions; do not invent a license or broaden platform-support claims as part of a correctness patch.

## Verification scope

Recorded local full-suite and offline installed-wheel runs used macOS ARM64
with Python 3.12.13 and 3.13.15. The [audit record](archive/audit-2026-09-25.md)
contains revision-specific test counts, skips, and the later native-handoff
check. Those measurements are not a standing quality guarantee. Native Rust fixtures used the locally
available `rust-analyzer`; ordinary structural queries did not need it.

The package requires Python >=3.12. Other Python/host combinations, including
Windows and Linux, have not been qualified by these records. The configured
hosted workflow is not evidence of a hosted pass until it actually executes.
Record native tool versions and skips separately from structural/package results.

## Documentation ownership

The [documentation index](README.md) assigns each topic to one current guide.
Keep filenames stable as schemas change; update compatibility notes inside the
reference. Keep commands in usage/maintenance guides and measurements in the
archive. Avoid duplicating live issue status or historical test counts in the
README. For a docs-only change, check local links/anchors, CLI examples, and
`git diff --check`; a runtime suite rerun is warranted when behavior or examples
exercise a changed execution path.

## Distribution

RI has no project license file yet; public redistribution needs an explicit
licensing decision. The previously inspected pinned wheels carried license
files in distribution metadata (grammar metadata identified MIT; the runtime
had a license file without a `License` field). This is a historical packaging
observation, not legal clearance. Review the actual notices when distributing
new artifacts; do not invent a license as part of maintenance.
