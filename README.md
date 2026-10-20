# Repository Intelligence

Repository Intelligence (RI) is a local Python tool for finding relevant source
and reviewing structural changes. It reads current files, locates callables and
Markdown document units, and compares caller-supplied planning and candidate
trees. It keeps source hashes, locations, parser metadata, and coverage gaps
with its results.

Tree-sitter is the default parser for **Python, Rust, JavaScript/JSX,
TypeScript/TSX, Java, Go, C#, C, C++, and Markdown**. Native analyzers are optional.
RI needs no service, database, or maintained symbol index. Task scope, execution and acceptance stay with the consumer project.

[Bounded workflow helpers](docs/workflow-tools.md) support explicit section reading
and declared-resource adoption, plus optional
[prepared execution and inventory-driven request generation](docs/workflow-tools.md#prepared-worker-execution-linkage). Consumer check execution stays in the project's
selected runner; these helpers do not add acceptance gates.

## Start work

The selected workflow uses **one Work author for engineering and coding**, followed
by a **fresh independent Work reviewer**. Both default to **Sol 6.1 Light
(`gpt-6.1-sol / low`)** under the project's selected settings and permitted overrides.
One author chat is enough to start; no creator, dispatcher, Luna worker or planning
review is required. Using RI navigation alone does not require adopting this workflow.

**New project?** Complete [project setup](docs/new-project-setup.md) first. Existing
projects use their adopted map and instructions, not automatically latest RI main.
With the installed kickoff skill, send:

```text
@ri-work-kickoff
@GitHub
Repository: <owner/repository>
Issue(s): #<issue>
Author selection: Work; gpt-6.1-sol / low, owner-confirmed
Authority: I select the reusable task grant for this issue.
```

Include the selection/grant only when true and intended. `@GitHub` is optional when
another permitted route exists; connector access is not authority. An applicable
recorded grant may be reused. See [authority](docs/new-project-setup.md#access-and-task-authority).
If Work skill registration is unverified, use the same prompt with the map's selected
[issue procedure](docs/start-an-issue.md) directly. Copied templates do not prove
installation or runtime mode.

The author inspects relevant source, keeps concise design and test expectations in
the existing task record, implements and checks coherent changes, then requests
exact-candidate independent review. Findings receive correction and affected
re-review. Existing authorized qualification, integration, installed verification,
durable evidence and safe cleanup remain required. Bounded maintenance uses this
same sequence with proportionate engineering/checks; no extra planning artifact.
Active attempts keep their pins. Consumers must explicitly reconcile their local
rules before adopting this change; editing RI does not migrate Poker or Nutrition.

## Choose a route

| Your task | Start here | What you get |
| --- | --- | --- |
| Use RI in an ordinary project | [Consumer guide](docs/consumer-guide.md), then the `locator` command below | Source navigation and coverage evidence; no capsule is required. |
| Set up RI workflow in a new project | [New-project setup](docs/new-project-setup.md), [adoption and tool ownership](docs/capsule-controller-workflow.md), and [skill templates](docs/skill-templates/README.md) | One author engineers and implements; a fresh independent reviewer assesses the exact candidate. |
| Maintain the RI package | [Architecture](docs/architecture.md), [maintenance](docs/maintenance.md), and [documentation index](docs/README.md) | Module boundaries, updater/bundle commands, and verification requirements. |

RI does not supply project permissions or approval rules. A project can use source
evidence without adopting the optional author/reviewer workflow.

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
For a Markdown capsule, query the exact `.md` file for a heading or checklist
term; RI reports source-bound sections and task items, while the consumer's
capsule validator still decides whether the document is valid.
[The consumer guide](docs/consumer-guide.md) covers installation, offline use,
upgrading an existing consumer, selection, and troubleshooting. Keep the RI
revision fixed during a comparison.

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
The [issue procedure](docs/start-an-issue.md) owns engineering, implementation,
independent review and closeout. Publication/integration remain subject to project
authority; useful tools do not grant it. [Adoption and tool ownership](docs/capsule-controller-workflow.md)
explain the compatibility boundary for older integrations.

## Develop and verify

From the RI checkout on macOS, run the start-of-work updater. It checks Python
package and SHA-pinned GitHub Action releases, prepares the selected environment,
runs the full offline package verification, and sets the local VS Code interpreter.
Use the interpreter path printed by the updater in Codex:

```sh
python3 scripts/update.py
```

Add `--codex` to keep a separate managed Codex CLI current for future attempts.
Use its printed path and selection receipt during setup; active attempts retain
their bound runtime. See [managed CLI updates](docs/maintenance.md#managed-codex-cli-updates-for-future-attempts).

The updater retains the previously selected environment while it qualifies a
package candidate in a separate environment. Its
`.ri-cache/update-result.json` distinguishes local verification from outstanding
grammar review or hosted GitHub Actions verification. Do not treat a locally
ready interpreter as a completed cross-project adoption decision.

To prepare and verify the current pins without checking for newer releases:

```sh
python3.14 -m venv .venv
.venv/bin/python scripts/maintain.py prepare
.venv/bin/python scripts/maintain.py verify
```

`prepare` above downloads wheels. Once the wheelhouse is populated, use
`python3 scripts/update.py --offline` for an offline start-of-work run.
An existing environment stays selected; use `--migrate-python` to qualify a
newer interpreter separately before selecting it. After verification, use
`maintain.py bundle` to retain an RI wheel and compatible dependency wheels for
consumers. [Maintenance](docs/maintenance.md#retained-wheel-bundles) has the recipe.
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
RI has no project license file yet; distribution notes are in maintenance.

For large structural handoffs, the optional [deduplicated review bundle](docs/review-evidence.md) retains complete evidence with a concise index and selective reads. Consumer adoption remains explicit.

For updater integrations, `scripts/update.py --result-schema 2` reports the
qualified interpreter and current runtime compatibility versions in
`.ri-cache/update-result.json`. Compare them with the consumer's supported
contract before activation. See [the updater contract](docs/maintenance.md)
and [current result versions](docs/navigation.md#current-result-contracts).
Existing schema-1 consumers remain supported by the default command.
