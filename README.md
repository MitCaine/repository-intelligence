# Repository Intelligence

Repository Intelligence (RI) is a local Python tool for finding relevant source
and reviewing structural changes. It reads current files, locates callables,
and compares caller-supplied planning and candidate trees. It keeps source hashes,
locations, parser metadata, and coverage gaps with its results.

Tree-sitter is the default parser for **Python, Rust, JavaScript/JSX,
TypeScript/TSX, Java, Go, C#, C, and C++**. Native analyzers are optional.
RI needs no service, database, or maintained symbol index. Task scope, capsule
execution, and acceptance stay with the consumer project.

## First query

Python 3.12+ is required. From the project you want to inspect, install a selected
RI checkout into a virtual environment:

```sh
python3.14 -m venv .venv-ri
.venv-ri/bin/python -m pip install "/path/to/Repository Intelligence"
.venv-ri/bin/python -m repository_intelligence.locator . \
  --query 'calculate total' --limit 8
```

Use a file path to narrow the question and `--json` to inspect full packet metadata.
A direct ambiguous C/C++ header needs `--language c` or `--language cpp`;
directory scans use repeatable `--header-language include/api.h=cpp`.
[The consumer guide](docs/consumer-guide.md) covers installation, offline use,
selection, and troubleshooting. Reinstall after intentionally updating a
non-editable RI checkout; keep its revision fixed during a comparison.

## Compare source trees

When the caller has prepared stable planning and candidate trees:

```sh
.venv-ri/bin/python -m repository_intelligence.inventory compare \
  /snapshots/planning /snapshots/candidate \
  --assert-stable-materialization --compact-json
```

The stability flag is the caller's assertion. Without it, RI reports incomplete
non-atomic scans and emits no comparable delta. Inspect file changes as well as
declaration changes, then reconcile with the full Git diff. See the
[inventory reference](docs/inventory.md) for compatibility and exit codes.

## Use the right evidence

Navigation is lexical: zero matches does not prove absence. Callable hashes
also cannot show every effect of changed imports, types, configuration, or
macros. Read [coverage limits](docs/limitations.md) when deciding what else to inspect.

For a parser gap or a Rust reference question, [native analysis](docs/native-analysis.md)
provides explicit Python AST, native Rust syntax, and Rust definition interfaces.
Keep the original structural evidence; the providers have different coverage.
[Poker's capsule recipe](docs/poker-capsule-workflow.md) demonstrates the controller
handoff through its existing context-page helper.

## Develop and verify

From the RI checkout on macOS, run the start-of-work updater. It checks Python
package and SHA-pinned GitHub Action releases, prepares `.venv`, runs the full
offline package verification, and sets the VS Code interpreter. Use the same
`.venv/bin/python` in Codex:

```sh
python3 scripts/update.py
```

To prepare and verify the current pins without checking for newer releases:

```sh
python3.14 -m venv .venv
.venv/bin/python scripts/maintain.py prepare
.venv/bin/python scripts/maintain.py verify
```

`prepare` above downloads wheels. Once the wheelhouse is populated, use
`python3 scripts/update.py --offline` for an offline start-of-work run.
Use `status` to inspect installed versions and `verify --require-native` when
qualifying native Rust tools. Native toolchain updates are opt-in with
`python3 scripts/update.py --native`.
[Maintenance](docs/maintenance.md) covers update options, all-grammar
upgrade checks, external tool/skill ownership, and reusable CI workflows.
[Architecture](docs/architecture.md) describes module ownership and the small-design goals.

The [documentation index](docs/README.md) links all current guides.
[Result contracts and compatibility](docs/navigation.md#current-result-contracts)
identify behavior more precisely than package version `0.1.0`; pin the RI revision.
RI originated in [Poker App](https://github.com/MitCaine/poker-app).
[Historical measurements](docs/archive/README.md) retain their original scope.
RI has no project license file yet; distribution notes are in maintenance.
