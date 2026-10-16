# Documentation

Start with the [repository README](../README.md) for a first query, then choose
the guide for your next action. Each topic has one current owner; result
versions are tracked inside the references rather than in parallel filenames.

| Need | Read |
| --- | --- |
| Controller: execute an issue in an established project | [Start an issue](start-an-issue.md), `docs/local_project_map.md` and live issue |
| Assigned builder, implementor or reviewer | [Worker instructions](worker-instructions.md#role-index) and supplied task inputs |
| Install, navigate, compare, troubleshoot | [Consumer guide](consumer-guide.md) |
| Interpret file/directory JSON, statuses, identity, limits, or older versions | [Navigation reference](navigation.md) |
| Compare planning and candidate source; interpret compact deltas and exits | [Inventory reference](inventory.md) |
| Keep complete review evidence without repeating records | [Review evidence transport](review-evidence.md) |
| Read selected instructions, maintain resource copies, or use selected dispatch/worker-execution bindings | [Bounded workflow tools](workflow-tools.md) |
| Know exactly which callables each language maps | [Language support](language-support.md) |
| Hand off to Python AST, native Rust syntax, or Rust definition lookup | [Native analysis](native-analysis.md) |
| Orient a controller, draft checkable capsule requirements, and run a low-interruption handoff | [Capsule controller workflow](capsule-controller-workflow.md) and [optional skill templates](skill-templates/README.md) |
| Set up RI and the capsule skills in a new consumer project | [New-project setup](new-project-setup.md) |
| Decide whether more evidence is needed | [Limitations](limitations.md) |
| Change a module or add a language | [Architecture and ownership](architecture.md) |
| Run the start-of-work updater, verify, upgrade grammars, maintain docs, or package RI | [Maintenance](maintenance.md) |


Established-project controllers read the bounded start-an-issue procedure, project-root
`docs/local_project_map.md` and live issue. Setup and package reference docs are conditional resources.
Do not use archived workflow instructions or previous plans for new execution.

## Workflow audit scope

- **Daily execution procedure:** start-an-issue; controller workflow explains
  project adoption and broader context, and new-project setup is used at adoption.
- **Current role instructions:** the [worker instructions](worker-instructions.md#role-index); optional
  skill templates route to the selected role and targeted helpers.
- **Runtime contracts:** navigation/inventory references and executable package code.
- **Optional extended helpers:** preflight evidence checker, queue watcher and review
  bundles are separate executable surfaces. Making them optional does not fix or
  erase defects; audit their code when evaluating or selecting those helpers.

Published commit identity matters: local documentation replacement is not yet a
published consumer adoption or a successful real-host trial.
