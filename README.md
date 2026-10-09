# Repository Intelligence

Repository Intelligence (RI) is a local Python tool for finding relevant source
and reviewing structural changes. It reads current files, locates callables and
Markdown document units, and compares caller-supplied planning and candidate
trees. It keeps source hashes, locations, parser metadata, and coverage gaps
with its results.

Tree-sitter is the default parser for **Python, Rust, JavaScript/JSX,
TypeScript/TSX, Java, Go, C#, C, C++, and Markdown**. Native analyzers are optional.
RI needs no service, database, or maintained symbol index. Task scope, capsule
execution, and acceptance stay with the consumer project.

## Start work with the kickoff skills

For an established project, use **ri-work-kickoff** in the owner-selected Work
controller chat and **ri-codex-dispatcher-kickoff** in a Codex dispatcher chat for
the same repository. First [install and verify skill availability](docs/skill-templates/README.md#kickoff-availability-and-adoption)
through each host's supported mechanism; repository templates alone are not
installed skills. These thin entrypoints locate the project's adopted workflow,
not automatically the newest RI main. They add no planning or review stage.

### 1. Work controller: send this prompt

Open Work, select the controller model/effort you actually intend, and replace the
example repository, issue and chat identifiers. Include the selection statement
only when true. Use the host's skill selector to invoke the installed skill.

```text
@ri-work-kickoff
Repository: MitCaine/poker-app
Issue(s): #447
Controller selection: I created this chat in Work and selected Sol 6.1 Light
(gpt-6.1-sol / low). Record this as owner-confirmed selection, not independently
observed runtime telemetry. Do not infer conflicting mode from tools or metadata,
or ask me to reconfirm unchanged accepted selections.
Capsule builder: gpt-6.1-sol / low
Independent reviewer: gpt-6.1-sol / low
Implementor: gpt-6-luna / max
Codex dispatcher: <exact designated dispatcher chat ID, or pending handoff>
Authority/constraints: Follow the project's existing task permissions. Ask only
for genuinely uncovered authority; no repository settings changes are granted.
Stopping conditions: Verified issue closeout, or a genuine unresolved blocker.
```

The example names the initial selections explicitly; omit those worker fields when
the project already selects them. Omitted worker settings use the project's selected defaults; optional explicit
Capsule builder, Independent reviewer and Implementor fields select authorized
run-specific overrides. The controller configures workers separately. For a queue,
replace Issue(s) with a list or inclusive range, such as `#447–#458`; the existing
[queue rules](docs/new-project-setup.md#issue-queues) require eligible-order processing
and a fresh controller for each issue. A range does not authorize context reuse.

### 2. Codex dispatcher: send this prompt

Open Codex for the same project. The dispatcher waits for the controller's bounded
handoff; kickoff does not authorize implementation or spawning a worker.

```text
$ri-codex-dispatcher-kickoff
Repository: MitCaine/poker-app
Work controller: <exact designated Work controller chat ID, or pending>
I designate this Codex chat as this project's implementation dispatcher.
```

Use the installed host selector (`@` in Work, `$` in Codex) rather than assuming
plain pasted text proves skill discovery. If the controller is not designated,
the dispatcher completes bounded orientation and waits. To connect designated
chats, the owner separately authorizes messaging in both directions for the
bounded task; naming a chat is not disclosure permission. The implementor's
model/effort comes from the controller's resolved handoff, not a second dispatcher
configuration. See the [input and selected-configuration contract](docs/new-project-setup.md#kickoff-inputs-and-selected-configuration)
for initial defaults, overrides and confirmation requirements.

Without installed skills, supply the same fields and actual selection directly,
then use [Start an issue](docs/start-an-issue.md) through the project's
`docs/local_project_map.md`. The dispatcher instead reads its selected
[worker section](docs/worker-instructions.md#codex-dispatcher). Direct document-based
launch remains supported; package introduction and setup/reference material
below are not required daily controller reading.

## Choose a route

| Your task | Start here | What you get |
| --- | --- | --- |
| Use RI in an ordinary project | [Consumer guide](docs/consumer-guide.md), then the `locator` command below | Source navigation and coverage evidence; no capsule is required. |
| Set up RI workflow in a new project | [New-project setup](docs/new-project-setup.md), [controller workflow](docs/capsule-controller-workflow.md), and [skill templates](docs/skill-templates/README.md) | The controller delegates planning, implementation and independent review through the selected project route. |
| Maintain the RI package | [Architecture](docs/architecture.md), [maintenance](docs/maintenance.md), and [documentation index](docs/README.md) | Module boundaries, updater/bundle commands, and verification requirements. |

RI does not supply a consumer capsule runner, project permissions, or approval
rules. A project can use RI source evidence without
adopting the optional capsule workflow.

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
The [capsule controller workflow](docs/capsule-controller-workflow.md) explains
the purpose, capsule requirements and checkable acceptance criteria, full
handoff, native subagent completion, recovery decisions, and optional project
skill templates. The controller verifies the accepted planning capsule and exact
published candidate before assigning independent review. Publication and
integration remain subject to project authority. The consumer's capsule remains
the execution authority.

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

The default [controller workflow](docs/capsule-controller-workflow.md) uses a
bounded task, serial planner/implementor/reviewer roles, relevant tests and full
diff review. Independent scope challenge and evidence helpers are optional unless
needed by a separately adopted project requirement.

For large structural handoffs, the optional [deduplicated review bundle](docs/review-evidence.md) retains complete evidence with a concise index and selective reads. Consumer adoption remains explicit.

For updater integrations, `scripts/update.py --result-schema 2` reports the
qualified interpreter and current runtime compatibility versions in
`.ri-cache/update-result.json`. Compare them with the consumer's supported
contract before activation. See [the updater contract](docs/maintenance.md)
and [current result versions](docs/navigation.md#current-result-contracts).
Existing schema-1 consumers remain supported by the default command.
