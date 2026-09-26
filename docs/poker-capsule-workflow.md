# Poker capsule workflow: first-consumer recipe

Poker is the first consumer, not a policy module inside RI. The current
[task capsule contract](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/TASK_CAPSULE.md)
and [context-retention policy](https://github.com/MitCaine/poker-app/blob/main/engineering/workflow/CONTEXT_RETENTION.md)
remain the owners of edit/read scope and context-page rules. This recipe was
checked against Poker `a11ce9a42bd40b22c3e1505de4f3f159c3224054`; consult current
Poker guidance when authoring a new capsule.

## Minimal controller sequence

1. Start from task intent and Poker's authored authority map. Use it to select
   the owning file or directory and the specific unanswered question.
2. Query that source with the installed shared locator, then inspect the exact
   declaration bytes and relevant callers/types/tests. Names and lexical call
   hints are navigation; they cannot supply an omitted behavioral requirement.
3. If syntax or semantics is insufficient, use the explicit [native handoff](native-analysis.md)
   for the named question and keep both observations. Avoid repeated whole-repo
   scans, automatic all-language analyzer startup, and persistent symbol caches.
4. Author context pages through Poker's existing `capsule_verify.py page` helper
   against the exact intended planning base. RI locations suggest an excerpt;
   the helper obtains the actual Git blob and validates the page declaration.
5. During execution, use supplied pages and declared expansions in page mode;
   use the authorized repository-read surface in the normal tool lane. RI does
   not add a new read permission or permit missing context to be invented.
6. Review the candidate with the full changed-file list, tests, and—when useful—
   RI's structural delta from stable planning/candidate trees with equal policy.
   Configuration, imports, type definitions, unsupported files, and enclosing
   state can change behavior even when all callable hashes are unchanged.

For ordinary source lookup, use the interpreter with RI installed:

```sh
python3.13 -m repository_intelligence.locator poker-tournament/src/clock.rs \
  --root . --query 'pause resume clock' --limit 5 --json
```

Authority-map reading is a separate controller step. The historical
`rust_index ... --authority-dir engineering/authority` command is unsupported
by current RI. Ordinary Rust lookup no longer requires `rust-analyzer`; only an
explicit native question does. See [installation](consumer-guide.md).

## Prevent information loss at the page handoff

Retain one full result outside bounded model context when it is useful, then
send the selected source excerpt plus task-relevant facts. Preserve the source
path/hash, parser/provider identity, coverage status, omissions/failures, and
unresolved question. Keep behavioral authority beside source evidence rather
than embedding Poker's authority maps into RI's language modules.

Use the declaration's `byte_range` to include attached attributes/decorators/docs.
Display `line` may point at the function name and omit those preceding bytes.
Convert from the exact source blob using the **consumer's** line convention.
Poker's current helper uses Python `str.splitlines(keepends=True)`, which also
splits Unicode separators inside comments/strings. Counting only LF bytes can
therefore produce a mechanically valid page that silently omits the function's
last lines. The following conversion matches the checked helper:

```python
from bisect import bisect_right

# source is the exact UTF-8 blob; start/end are its half-open declaration range.
assert 0 <= start < end <= len(source)
lines = source.decode("utf-8").splitlines(keepends=True)
byte_boundaries = [0]
for line in lines:
    byte_boundaries.append(byte_boundaries[-1] + len(line.encode("utf-8")))
first_line = bisect_right(byte_boundaries, start)
last_line = bisect_right(byte_boundaries, end - 1)
excerpt = "".join(lines[first_line - 1:last_line]).encode("utf-8")
assert source[start:end] in excerpt
```

Pass `first_line`/`last_line` to the helper's inclusive `--start`/`--end` options.
Inspect the selected excerpt; a function alone may omit a necessary contract or
caller. Respect the existing page limits rather than truncating source silently.
A computed Git blob ID from RI does not replace Poker's immutable-Git page helper.
Recheck the line convention if that consumer implementation changes.

The controller decides the necessary evidence. `stable=True`, a successful RI
command, a native answer, or a comparable delta never approves a capsule.
Edited source needs refreshed working locations; that ordinary refresh does
not itself reopen the immutable planning snapshot or end the attempt.

The [recorded Poker smoke test](archive/audit-2026-09-25.md#follow-up-native-and-poker-handoff)
includes one successful page-helper handoff and the observed native/Tree-sitter
coverage difference. It is evidence from a specific revision, not a reusable
planning base or a complete capsule qualification.
