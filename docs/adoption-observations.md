# Cross-project navigation observations

These are read-only, non-atomic working-tree observations from 2026-09-25,
using RI's local Tree-sitter locator. They are practical orientation examples,
not benchmarks, checkout attestations, or proof of a complete behavior path.
Paths and line numbers can move; rerun RI and inspect the returned source when
preparing an actual task.

## Task Manager: one feature across Java and TypeScript

In the unrelated `task-manager-fullstack` checkout, the query `create task`
scanned a 30-file Java source directory and a 164-file frontend source
directory separately. Both scans returned `navigation_only`, with no parser
failure in those scoped directories. The source-bound results gave the
controller a short initial route:

```text
taskmanager-frontend/src/hooks/useCreateTaskWorkflow.ts:36  useCreateTaskWorkflow
taskmanager-frontend/src/api/tasks.ts:48                 createTask
src/main/java/com/mitchell/taskmanager/TaskController.java:56  createTask
```

Those locations were checked against the current source: the frontend API
wrapper posts the task, and the Java controller validates and saves it. The
query also ranked tests and other `create*` methods, so the controller still
has to choose task-relevant paths. RI did not resolve a call graph, infer edit
permission, or decide whether the task crosses the frontend/backend boundary.

## Nutrition App: separate TypeScript and Python orientation

In the unrelated `Nutrition App` checkout, `backup restore` over its two-file
TypeScript backup directory surfaced
`activatePendingLocalRestore` in `localBackup.ts:408` and nearby staging and
inspection functions. The source at that location confirms it activates a
previously validated restore. A separate `source digest` query over the
engineering directory's one Python file surfaced `source_digest` in
`generate_dri_reference.py:686`, whose source hashes the loaded source bytes.
Both scoped queries returned `navigation_only`; a broader `dri reference`
query did **not** find a useful match, which is a reminder that ranking depends
on task wording and never proves absence.

The useful controller pattern is to put a few current RI locations, hashes,
and the relevant source excerpt into the work packet, then let the implementor
inspect further if needed. Project-owned authority maps and domain rules stay
in each consumer repository. RI only supplies source evidence.
