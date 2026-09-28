# Maintenance and verification

The source and current contract are the implementation authority. Package version `0.1.0` alone does not identify the semantics of the successive navigation/inventory revisions. Record the RI commit, Python/platform, installed dependency versions, test command, and skips when reporting verification.

## One local and CI path

`pyproject.toml` is the only package-version list. The standard-library
`scripts/maintain.py` reads its runtime and build pins; it works from any working
directory and does not need RI installed to report the environment. From the RI
checkout:

```sh
python3 scripts/update.py
# Use the interpreter path printed by the updater:
/path/to/selected/python scripts/maintain.py status
```

The updater reuses the selected environment for ordinary start-of-work runs.
On first setup, it creates `.venv` with the newest installed CI-supported Python
(3.12, 3.13, or 3.14). `--migrate-python` prepares a separate permanent candidate
environment under `.ri-cache/venvs`, verifies it, then selects it for future runs
and VS Code. Package candidates also qualify in separate environments before
their pin and interpreter selection are promoted. An interruption leaves the
last selected environment intact; a recovery record restores manifest/selection
bytes at the next launch. A second updater run exits while another holds the
single-run lock. A package candidate failure leaves the former environment and
selection in place. Later native-tool failure can leave already qualified
package changes selected, but no overall readiness result is written.
The updater asks PyPI for the latest stable release of each exact pin in
`pyproject.toml`, ignores lower versions, then tries changes one at a time with
`prepare` and `verify`.
An available wheel on PyPI does not guarantee one for this host; preparation
checks that. A failed candidate is restored and the full verification is rerun
before the updater continues. Releases that prepare successfully but fail
verification are recorded in ignored `.ri-cache/rejected-updates.json` with the
RI HEAD and tracked code diff, manifest, Python version, and platform context. The same
version is retried when that context changes. Download or preparation failures
restore the prior pin and remain retryable. Deliberate known-bad exclusions
remain in the updater source. Delete the cache only after investigating it.
The Tree-sitter 0.26.0 runtime caused a Python crash in the deep-call fixture on
the tested macOS/Python 3.13 host and is excluded from update proposals.
Tree-sitter 0.25.1 supplies a Python 3.14 macOS ARM64 wheel and passed RI's
offline installed-package and native verification on local Python 3.12, 3.13,
and 3.14. Comparisons across different installed parser versions remain
incompatible; regenerate both observations with the same pinned environment.

The updater also refreshes SHA-pinned GitHub Actions from their latest releases
and writes ignored local `.vscode/settings.json` with the project interpreter when that file
is JSON. JSONC settings are left untouched with a warning so an editor preference
cannot invalidate package verification. Codex uses the interpreter printed by
the updater. It does not install a new Python or CI runner image. Review grammar changes and hosted CI
before adopting updates. Use `--offline` to reuse existing wheels without
release checks, `--skip-actions` to defer Actions checks, and `--native` to
update rustup stable plus analyzer/source components and verify that same stable
toolchain. `--offline --native` is rejected because the native update can use
the network.
Native updates are opt-in and cannot be rolled back by this script.

On success, inspect `.ri-cache/update-result.json`: `selected_python` and
`local_verify_passed` identify the usable local environment;
`outstanding_qualification` names work still required. Updated grammar packages
still need the upstream node review described below. Changed Actions still need
a successful hosted Verify run. The updater does not claim either check passed
merely because local tests completed. A failed or interrupted run removes its
previous readiness result. The recovery journal and candidate environments
remain ignored local files; do not run dependency updates inside an active
consumer capsule attempt.

For manual fixed-pin setup, create the environment and run `prepare` then
`verify` as separate commands. The start-of-work updater currently targets macOS.
On Windows use `.venv\Scripts\python.exe` for the shared maintenance commands.
`status` prints installed versus pinned versions, Python/platform, and functional
native-tool versions.
It does not check the internet for newer releases. `prepare` downloads the
pinned build/runtime wheels and installs them into the invoking virtual
environment. It refuses a global interpreter. `verify` checks installed pins,
then runs all tests with mandatory offline package verification. It does not
update the invoking environment; the package test creates temporary build and
consumer environments and installs only from the wheelhouse.

Wheels default to ignored `.ri-cache/wheels`. Both commands accept
`--wheelhouse /path/to/wheels`; old and new versions may coexist because pip
resolves the exact manifest pins and compatible platform tags. Online preparation
uses the configured package index. For a prepared offline wheelhouse:

```sh
.venv/bin/python scripts/maintain.py prepare --offline --wheelhouse /path/to/wheels
.venv/bin/python scripts/maintain.py verify --wheelhouse /path/to/wheels --require-native
```

Offline installation disables inherited pip configuration, remote links, and
extra requirements. `--require-native` fails early unless `rustc`, `cargo`, and
`rust-analyzer` respond successfully. Without it, native tests keep their existing
availability conditions; inspect skips. A rustup proxy on PATH is not evidence
that its analyzer component is installed. RI does not update native tools as a
side effect of these commands.

## Offline package verification

For an already prepared environment, direct discovery remains available:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
```

Direct discovery may skip package verification unless wheel inputs are supplied.
The preferred strict package-only invocation is:

```sh
RI_WHEELHOUSE=/path/to/wheels RI_REQUIRE_STANDALONE=1 \
  PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_installed_package.py
```

The older `RI_SETUPTOOLS_WHEEL`, `RI_WHEEL_WHEEL`, and
`RI_TREE_SITTER_WHEELHOUSE` inputs remain supported. Prefer `RI_WHEELHOUSE` for
new automation: adding another build dependency then needs no extra environment
variable. The test independently reads the manifest, verifies actual build-tool
versions, builds RI, checks wheel dependency metadata, and exercises an unrelated
mixed-language consumer without native tools on its PATH. Avoid running two
package-building suites concurrently in the same checkout.

## Updates and ownership

Run `python3 scripts/update.py` at the start of work when internet access is
available. Package and Action checks live in separate modules under
`scripts/update_modules/`; `scripts/maintain.py` remains the shared environment
preparation and verification path. Dependency PR scheduling was removed because
updates now start locally when the maintainer runs this command. The updater
does not commit or push any changes.

## Retained wheel bundles

After preparing a clean committed checkout, retain a wheel bundle for one
Python/platform combination:

```sh
.venv/bin/python scripts/maintain.py prepare
.venv/bin/python scripts/maintain.py bundle --require-native \
  --output .ri-cache/bundles/ri-macos-arm64-py314
```

After `--migrate-python`, substitute the selected interpreter path printed by
the updater for `.venv/bin/python` in this recipe.

`bundle` requires a clean checkout, runs full verification, copies compatible pinned
dependency wheels, builds the RI wheel from `git archive HEAD`, and installs that
exact retained wheel into a temporary
offline consumer environment for an import and `pip check`. The output includes
`receipt.json` with the Git commit, clean-checkout flag, Python/platform,
package pins, and SHA-256 of every wheel. The output directory must be empty.
Only clean bundles qualify for consumer adoption. `--allow-dirty` permits a
diagnostic build from HEAD while the checkout has local changes; its receipt
records `clean_checkout: false`. Build a separate bundle for each required
Python/platform. CI exercises bundle creation but does not publish or upload it.

| Technology | Change location | Verification before adoption |
| --- | --- | --- |
| Tree-sitter runtime and grammar packages | Exact pins in `pyproject.toml`, refreshed by `scripts/update.py` | Grammar review below, language fixtures, full `verify` |
| Python packaging/build dependencies | `build-system.requires`; runtime additions go in `project.dependencies` | `prepare`, then fresh offline build/consumer verification |
| Python interpreter support | `requires-python` and Verify's Python matrix | Compatible wheels and complete tests for every added interpreter |
| Native Rust analyzer/toolchain | Host's existing Rust installation; CI provisions required components | `status`, then `verify --require-native`; retain the reported versions |
| GitHub Actions | `.github/workflows`; SHA-pinned actions refreshed by `scripts/update.py` | Review release notes and complete the hosted matrix |
| CI runner images | `.github/workflows/verify.yml`; change the `runs-on` value deliberately | Complete the hosted matrix |
| RI instructions and capsule skill templates | Repository instructions in `AGENTS.md`; optional templates under `docs/skill-templates/` | Keep RI maintenance on shared commands; validate templates and their links after changes |

RI now carries optional **source templates** for capsule handoffs, including a
queue watcher helper. These do not install automatically, alter the RI package,
or grant authority in a consumer project. An installed personal skill or plugin
still has its own lifecycle; compare it with the template before updating it.
A skill that maintains RI should call these shared commands instead of embedding
package pins or its own install/test procedure. Consumer capsules remain owned
by their consumer project; see the [controller workflow](capsule-controller-workflow.md).

For a routine package update, run the updater or edit the exact `NAME==VERSION`
pin, inspect `status`, and run `verify`. Keep independent
behavior assertions: a parser upgrade that fixes a formerly unsupported construct
needs a reviewed expectation change, not a blanket relaxation of failure tests.
The current maintenance commands deliberately support exact, unmarked pins.
If extras, URL requirements, or environment markers become necessary, extend
that parsing and its tests explicitly. Adding an ordinary exact dependency or
build requirement needs no change to the scripts or CI setup.

Native Rust is optional for ordinary RI use. CI installs the analyzer and source
components in its selected runner toolchain and records actual tool versions.
To update a rustup-managed local stable toolchain deliberately:

```sh
rustup update stable
rustup component add --toolchain stable rust-analyzer rust-src
RUSTUP_TOOLCHAIN=stable .venv/bin/python scripts/maintain.py verify --require-native
```

Use the corresponding owner for other installations. Native tool/runner versions
are reported rather than pinned by RI's Python manifest; a hosted run verifies
that run's environment, not every future native release.

## Automated and reusable verification

[Verify](../.github/workflows/verify.yml) runs on pull requests, main pushes,
manual dispatch, and reusable-workflow calls, on macOS 15 with Python 3.12/3.13/3.14.
It provisions functional native tools, runs `prepare`, then runs
`bundle --require-native`, which includes full `verify` and an offline install
of the retained wheel. Missing package/native
prerequisites fail the job. Its Python environment and wheel cache are ignored
workspace files. Action revisions remain SHA-pinned with version comments so
the local updater can refresh them. Hosted CI is still required to verify an
Action change.

For future orchestration **inside this repository**, reuse the existing job:

```yaml
name: Manual verification and bundle smoke test
on: workflow_dispatch
jobs:
  verify:
    uses: ./.github/workflows/verify.yml
```

Add specialized checks as separate jobs when they establish something different;
use the shared commands in jobs that need the same environment. A new language
runtime/ecosystem also needs its own manifest and verification path.
New SHA-pinned Actions references in `.yml` or `.yaml` files under
`.github/workflows` are discovered by the updater when they use a
`uses: owner/repo@SHA # vX` line, including named steps.
Cross-repository workflow reuse is not promised: checkout and script paths here
assume RI's own source tree. No workflow publishes packages or merges changes.
A workflow edit is verified only after its hosted run completes successfully.

## Design regressions around invariants

For extraction changes, specify expected qualified owners, declaration kinds, and complete raw source slices independently of production helpers. Recomputing a hash from a reported range is necessary consistency checking, but cannot prove the range itself is correct. Counter agreement likewise cannot prove that traversal reached all promised nodes.

Use paired planning/candidate fixtures. A body edit should modify a stable named declaration. A harmless comment or local parameter rename must not accidentally create a different identity where the identity contract excludes that detail. Changing attached declaration syntax must affect its observation. Anonymous offset changes and genuinely ambiguous duplicate names should continue following the documented conservative policy.

Combine grammar forms rather than testing only isolated features: deleted declarations with lambda defaults; reference declarators with named parameters; comments between parameters and generic type parameters; annotations containing keyword text; overloads containing local classes. Verify nested descendants are still visited when an enclosing declaration is bodyless or unhandled.

Failure tests should preserve usable partial evidence, reject contradictory comparison inputs, and exercise read/parse boundaries separately. Use sparse oversized files and fake stalled providers instead of allocating excessive fixtures or requiring native tools for transport-only tests. Do not accept a broad exception handler as a substitute for understanding which optional operation can fail.

## Change contracts deliberately

The [navigation reference](navigation.md#current-result-contracts) owns the current version table. Changes to identity, source envelopes, classification, or accounting need an explicit compatibility decision and corresponding version updates before old/new observations are compared. Update the current reference, callable contract, README, fixtures, and any exact-version packaging assertions together. Maintain the compatibility summary and exact historical recovery link in
[navigation](navigation.md#compatibility-history); do not create another versioned
copy of the full reference or reinterpret old packets under new semantics.

A grammar-pin change requires reviewing upstream `node-types.json` and relevant
grammar rules at the exact tags. The maintainer checker covers selected
node/field-presence and requiredness assumptions for all ten parser variants,
including separate TypeScript and TSX shapes. Print URLs derived from the
current pins, download the relevant files, and check them locally:

```sh
python scripts/check_grammar_nodes.py --sources
python scripts/check_grammar_nodes.py python=/tmp/python-node-types.json
```

Pass all `LANGUAGE=PATH` pairs with `--require-all` for a complete set (`python`,
`rust`, `javascript`, `typescript`, `tsx`, `java`, `go`, `c-sharp`, `c`, `cpp`).
The historical two-positional-file Python/Rust invocation still works. The
checker never downloads or changes dependencies. Review its upstream repository
paths if a project changes its tag or packaging convention.

This checks selected assumptions, not new syntax, field types, or exhaustive
classifier coverage. Keep the all-variant checker/test mapping current when
adding a language. Run affected language fixtures, common navigation/inventory
tests, and installed-wheel verification; do not assume every declarator child
has a field name or every named child is a parameter.

## Acceptance and cleanup

Reproduce correctness findings with parser-integrated regressions before marking
them fixed. Deliberate [limitations](limitations.md) are not promises of planned features. Add an exact mixed-language P-to-C expectation and inspect the complete diff. Record documentation consolidation separately from later runtime corrections in the audit record. Public release and licensing remain separate decisions; do not invent a license or broaden platform-support claims as part of a correctness patch.

## Verification scope

Recorded local full-suite and offline installed-wheel runs used macOS ARM64
with Python 3.12.13 and 3.13.15. The [audit record](archive/audit-2026-09-25.md)
contains revision-specific test counts, skips, and the later native-handoff
check. Those measurements are not a standing quality guarantee. Native Rust fixtures used the locally
available `rust-analyzer`; ordinary structural queries did not need it.

The package requires Python >=3.12. Local macOS ARM64 verification of the
Tree-sitter 0.25.1 pin passed the full suite, including offline
installed-wheel verification and required native tools, on Python 3.12, 3.13,
and 3.14. Other Python/host combinations, including Windows and Linux, have not
been qualified by these records. The configured hosted workflow is not evidence
of a hosted pass until it actually executes.
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
