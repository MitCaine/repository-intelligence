# Documentation

Start with the [repository README](../README.md) for a first query, then choose
the guide for your next action. Each topic has one current owner; result
versions are tracked inside the references rather than in parallel filenames.

| Need | Read |
| --- | --- |
| Install, navigate, compare, troubleshoot | [Consumer guide](consumer-guide.md) |
| Interpret file/directory JSON, statuses, identity, limits, or older versions | [Navigation reference](navigation.md) |
| Compare planning and candidate source; interpret compact deltas and exits | [Inventory reference](inventory.md) |
| Keep complete review evidence without repeating records | [Review evidence transport](review-evidence.md) |
| Know exactly which callables each language maps | [Language support](language-support.md) |
| Hand off to Python AST, native Rust syntax, or Rust definition lookup | [Native analysis](native-analysis.md) |
| Prepare Poker capsule context without changing its workflow | [Poker capsule integration](poker-capsule-workflow.md) |
| Orient a controller, draft checkable capsule requirements, and run a low-interruption handoff | [Capsule controller workflow](capsule-controller-workflow.md) and [optional skill templates](skill-templates/README.md) |
| Set up RI and the capsule skills in a new consumer project | [New-project setup](new-project-setup.md) |
| Exercise adoption in a new project before claiming reliable autonomy | [Workflow adoption cases](adoption-cases.md) |
| Decide whether more evidence is needed | [Limitations](limitations.md) |
| Change a module or add a language | [Architecture and ownership](architecture.md) |
| Run the start-of-work updater, verify, upgrade grammars, maintain docs, or package RI | [Maintenance](maintenance.md) |

[Historical records](archive/README.md) retain extraction decisions, pilot/adoption
observations, and measured audit results. They are not current setup instructions,
provider promises, or capsule authority.

The [workflow effectiveness corrections](workflow-effectiveness.md) explain
reusable adoption checks, claim-specific evidence, lifecycle stages and bounded
reuse without adding universal workflow machinery.

- [Backlog implementation status](archive/backlog-implementation-status-2026-09-30.md): local fixes and outstanding consumer qualification boundaries.

## Workflow audit scope

- **Default procedure:** controller workflow and compact new-project setup.
- **Current role instructions:** the optional skill templates; choose only useful roles.
- **Runtime contracts:** navigation/inventory references and executable package code.
- **Optional extended helpers:** preflight evidence checker, queue watcher and review
  bundles are separate executable surfaces. Making them optional does not fix or
  erase defects; audit their code when evaluating or selecting those helpers.
- **Historical extended instructions:** the archive retains the former mandatory
  procedure for comparison. It is not the expected route for new tasks.

Published commit identity matters: local documentation replacement is not yet a
published consumer adoption or a successful real-host trial.
