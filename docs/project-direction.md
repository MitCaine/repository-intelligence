# Repository Intelligence: project direction

RI is a small, reusable source-orientation tool for unrelated software
projects. It finds relevant code, maps a declared set of source constructs,
binds observations to the exact bytes read, and returns compact evidence.
It does not decide task scope, edit permission, test sufficiency, or whether a
candidate should be accepted.

This document records the intended end state. The [result contract](navigation-result-v3.md)
describes what the current implementation actually returns; the two must not
be confused. In particular, today's `navigation_only` result is **not** a
complete inventory or a candidate-change qualification.

## Development workflow

```text
GitHub issue (durable task authority)
    ↓
Controller selects scope and asks RI for source evidence
    ↓
Controller inspects source and prepares a directed work packet
    ↓
Codex implements and tests on a non-main branch
    ↓
Controller reviews the exact candidate and qualification evidence
    ├── FAIL → controller requests a bounded correction → Codex retries
    └── PASS → controller may merge and reconcile the issue
```

The controller and reviewer may be the same person or agent. RI assists both
with source facts but does not become a capsule runner or workflow engine.
Project-specific authority documents remain with their project/controller.

## Source-evidence pipeline

```text
exact source bytes
    ↓ raw SHA-256 + optional algorithm-tagged computed Git blob ID
Tree-sitter syntax
    ↓ language-specific extraction rules
normalized structural inventory + explicit coverage state
    ├── query/rank → bounded navigation packet for the controller
    └── compare planning P with candidate C → structural delta for review

When structure cannot answer a requested semantic question:
    optional language-native analyzer → separately labeled resolved evidence
```

Tree-sitter is the routine structural baseline. Language-specific adapters are
necessary; language-neutral output does not mean translating all languages to
one representation. `rust-analyzer` remains available as an optional backup
or escalation for richer Rust metadata. It is not being retired, and no
native analyzer is required merely to perform ordinary structural lookup once
that language's Tree-sitter adapter is ready.

## Trustworthy coverage

The central invariant is:

> For each supported language, every declaration promised by its explicit
> mapping contract in each successfully parsed, in-scope source file appears
> exactly once in the structural inventory, or RI reports the scan incomplete.

This is completeness over a *declared source-level contract*, not all
compiler-generated behavior, all build variants, or all semantic relationships.
Parser success alone cannot prove adapter coverage: Tree-sitter `ERROR` and
`MISSING` nodes, unhandled promised syntax, failed or oversized files, and
scan exclusions must be visible. Partial results remain useful for navigation;
an incomplete supported-source inventory cannot qualify a candidate delta.
Avoiding unknowingly incomplete mapping is an engineering goal, not a proven
guarantee from counters alone. The declared contract and adapter fixtures need
review: a wrong owner or kind can preserve perfect counts. A controller must
also review the full source/file diff beside RI's declaration delta, since
imports, initializers, configuration, and unsupported source can change with
no declaration changes.

Mappings are generated from source, never manually maintained. The controller
or reviewer can compare `RI(P)` and `RI(C)` to see added, removed, modified,
and unchanged files and declarations. RI reports the delta; the controller
decides whether each change belongs to the task. Query terms must not affect
the underlying inventory or delta, and display limits apply only *after*
matching/ranking has seen full extracted evidence.

Each observation should retain repository-relative path, exact raw-source
hash, optional algorithm-tagged Git blob ID, parser/grammar/adapter versions,
declaration identity, exact byte range and declaration hash, plus display
line/column. Line numbers are locations, not identities. A computed hash does
not attest to a checkout or prove commit membership. Structural or lexical
references must never be labeled resolved calls.

## Progressive precision and scope

Ordinary navigation starts with structural evidence and narrow source
inspection. Escalate to a native analyzer when a task needs resolved targets,
callers, implementations, overrides, overload/type-dependent dispatch, or
when imports, aliases, or ambiguous names defeat structural identification.
Resolved evidence must name its provider, version, source snapshot, relevant
project/build configuration, and unresolved limits. Neither Tree-sitter nor a
native analyzer should manufacture certainty about reflection, generated
source, conditional compilation, or dynamic dispatch.

The Python, Rust, JavaScript/TypeScript, Java, C/C++, Go, and C# structural
adapters now ship. Kotlin may follow when useful. Each adapter needs a
language-specific callable/declaration contract and fixtures, including an
explicit policy for anonymous functions, executable accessors/operators, and
bodyless declarations where the language has them. C/C++ must state its
header/preprocessor/build-configuration limits rather than claim compiled
program completeness from raw syntax.

## Issue ownership and non-goals

- [#4](https://github.com/MitCaine/repository-intelligence/issues/4) owns the
  shared result/navigation contract; [#8](https://github.com/MitCaine/repository-intelligence/issues/8)
  owns the Tree-sitter baseline and adapter parity; [#9](https://github.com/MitCaine/repository-intelligence/issues/9)
  owns complete inventories and planning-to-candidate deltas.
- [#10–#14](https://github.com/MitCaine/repository-intelligence/issues) own
  additional language adapters. [#15](https://github.com/MitCaine/repository-intelligence/issues/15)
  owns optional native semantic resolution. [#3](https://github.com/MitCaine/repository-intelligence/issues/3)
  owns standalone packaging; [#6](https://github.com/MitCaine/repository-intelligence/issues/6)
  owns practical cross-project adoption and product documentation.

RI should not contain a database, persistent generated dictionaries,
embeddings, a daemon/service, hosted indexing, a generic code graph or LSP
framework, a custom C++ parser, source translation, project-domain knowledge,
security/governance machinery, task permissions, capsule semantics, or
research-grade benchmarks. The goal is minimum machinery with maximum
trustworthy source orientation.
