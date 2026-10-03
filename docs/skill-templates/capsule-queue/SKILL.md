---
name: capsule-queue
description: Queue one terminal result for an external agent job, capsule qualification, or CI run that otherwise needs repeated polling. Keep controller, implementor, and reviewer authority separate; use native completion when it already wakes the controller.
---

# Capsule queue

Use this skill when an external agent or other process needs a watcher to detect its terminal state and wake its controller. Native subagents and Codex threads with reliable completion channels use those channels. Ordinary commands return directly. Do not create a second notification when the runner already provides a reliable terminal callback. Establish the completion route at dispatch; do not spend repeated controller turns checking unchanged status.

## Authority and routing

- Read the active capsule and current controller assignment before dispatch. The capsule alone defines owned paths, exact branch/base/overlay, checks, and stop conditions. A watcher may observe and report; it cannot broaden scope, choose replacement checks, retry a failed gate, publish, accept, or merge.
- RI findings are navigation and source evidence. Bind any RI location to the exact consumer blob before use. Neither RI output nor watcher output establishes qualification or reviewer approval.
- Queue to the exact task UUID that owns the next decision, normally the controller. Obtain it from `CODEX_THREAD_ID` or verified runtime metadata. Never infer it from recency, a role label, or a convenient open task. Check `codex queue --help` for `--thread` and `--message` on the host that will notify.
- `codex queue` targets a Codex session, not an arbitrary ChatGPT Work chat. For a Work controller, verify its native agent completion route or a tested bridge to the exact controller task before relying on this helper. If no route exists, use the environment's supported bounded wait and report the limit.
- An implementor may return its result to its controller through native agent or thread messaging. Queue an external gate result to the controller only when that controller has authorized the gate and the originating task UUID is verified. A fresh independent reviewer receives an exact candidate and evidence packet through the controller's normal review dispatch; do not treat a queued gate result as a reviewer verdict.

## Watcher contract

Before launch, record the mechanism, verified destination, job/candidate identity,
deadline and retained evidence paths. A bounded wait means an event wait or
blocking runner operation; putting a deadline around repeated model-driven
status requests is still polling. If Work lacks a verified completion bridge,
state that limitation once and use its supported blocking wait.

The controller may prepare authorized review or installation material while
waiting, provided it neither depends on a pending PASS nor changes the candidate.
Once useful preparation is complete, wait for the terminal result. Do not query
individual CI jobs or reread unchanged status files to generate periodic
"still running" commentary. Intermediate green profiles do not require a wake-up
when the same aggregate result remains pending. Report actionable failures,
timeouts, delivery problems or requested status. Necessary tool-level resumptions
of a blocking wait must not turn into repeated CI inspection.

For a native subagent terminal return, the controller retains and authenticates
the handoff, records its disposition, then closes the completed agent, where available, through
the host's supported operation before dispatching the next fresh role. Completed
but open threads can consume capacity even with only one working subagent.
Do not close a running agent or discard its evidence. If no close operation is
available and fresh creation is blocked, record the limitation and use the
workflow's authorized last-resort idle-agent reuse with a complete reauthenticated
handoff. Keep review independent; never restart the completed job or reset its
allowance to regain capacity. See
[agent capacity recovery](../../capsule-controller-workflow.md#release-completed-agent-capacity).

For a new external command, launch it once through the helper below. For an existing job, watch its blocking completion event or wrap a blocking watch command; never restart it to attach a watcher. If the service exposes only status checks, put bounded polling with backoff and a deadline inside a dedicated watcher script.

Distinguish success, failure, timeout, signal termination, and lost connectivity using authoritative terminal evidence. The helper can classify its own watcher errors; a wrapped command that exits nonzero after losing connectivity is a failure unless its watcher records a more specific outcome. A signal alone does not prove an intentional cancellation. A missing PID or closed connection is not success. Save raw, potentially untrusted logs under an unused directory under the consumer-authorized external evidence root. Queue exactly one concise terminal message containing outcome, status path, and the controller's next action. The helper records command outcome in `status.json` and notification state in `delivery.json`; `accepted_by_cli` is not proof the controller consumed it.

After launch, end the waiting turn only if the host has a verified terminal delivery route. Do not poll from later model turns or post periodic updates. On receipt, read `status.json`, `delivery.json`, and relevant `output.log`, verify the exact capsule/candidate/check identity, then continue the controller workflow. Failure or missing evidence blocks the affected qualification gate; it does not turn into a PASS. Preserve the failed candidate and evidence for independent review or replan.

## Monitored command

Use [scripts/run_and_queue.py](scripts/run_and_queue.py) with an unused job directory:

```sh
origin_thread="${CODEX_THREAD_ID:?verified task UUID required}"
evidence_root="${EVIDENCE_ROOT:?authorized external evidence root required}"
python3 path/to/capsule-queue/scripts/run_and_queue.py \
  --thread "$origin_thread" --cwd "$PWD" \
  --job-dir "$evidence_root/qualification-watch-001" \
  --label 'Capsule qualification' --timeout-seconds 3600 \
  --follow-up 'Controller: inspect the saved gate result and continue the capsule workflow.' \
  -- ./scripts/capsule-check.sh
```

Pass a blocking watcher command after `--` for an existing job. Compound logic belongs in a script; arguments are executed without shell evaluation. The default deadline is one hour; select a finite positive `--timeout-seconds` appropriate to the job. The helper records `status.json`, `delivery.json`, `output.log`, and `queue.log`, then makes one queue attempt for every terminal outcome. It survives the launching shell, but not host shutdown. A host shutdown or missing status requires fresh evidence before any gate disposition.

If `delivery.json` reports `rejected_by_cli` or `uncertain`, the completed command must **not** be restarted to regain notification. Inspect the saved status and delivery evidence through a separate controller-visible route. The controller may use `python3 path/to/run_and_queue.py --redeliver /path/to/job/config.json` after checking the exact destination and accepting possible duplicate notification. This command sends only the saved terminal result; it never reruns the job. A host with no delivery acknowledgement cannot guarantee autonomous wake-up. For that host, retain a bounded external monitor or supported blocking wait and report the limitation.

For a job managed by another runner, save its terminal evidence first and call `codex queue --thread "$origin_thread" --message "$completion_message"` once. Remote watchers need verified Codex access; otherwise run the watcher locally. If no reliable callback or detached watcher is available, use the environment's supported blocking wait and state that limit.

## Process containment and retry safety

Timeout cleanup sends TERM, waits a bounded grace, then sends KILL to remaining
members of the original POSIX process group even if its leader already exited.
`cleanup_confirmed` reports whether that group is absent after cleanup. False or
unknown cleanup is not permission to retry overlapping writes: establish that
previous work is stopped or isolated first. Descendants that create another
session/group and remote jobs are outside this local boundary; their accepted
runner must cancel or isolate them separately. A success exit describes the
wrapped command, not arbitrary detached descendants. Notification/redelivery
remains separate from command outcome and never reruns the command.

Keep watcher artifacts outside the clean candidate checkout. An in-repository
location is permitted only if consumer-authorized, ignored and outside candidate
scope, verified before launch. Signal/nonzero leader exits also trigger group
cleanup; false or unknown cleanup blocks overlapping retries.

Command outcome and cleanup outcome are separate. Cleanup errors preserve a known
success/failure/signal/timeout, record `cleanup_error`, and leave
`cleanup_confirmed: false`. Even exit zero checks for remaining group members
and cleans them up. Success with false/unknown cleanup is not terminal readiness
for overlapping follow-up; verify termination or isolate remaining work first.

Notification recovery is serialized per job using a local POSIX file lock.
Accepted notification attempts cannot be resent by concurrent recovery callers.
Diagnostic output uses escaped replacement for invalid encoded bytes; it does
not modify retained command logs or source evidence. CLI acceptance still does
not prove controller consumption. Recovery only retries delivery, never the
completed command. A terminated delivery attempt can remain uncertain; inspect
its saved state before authorizing another attempt.

The watcher owns cancellation of its original local command process group.
SIGTERM or SIGINT/KeyboardInterrupt retains an interrupted record and performs
bounded TERM/KILL cleanup; repeated cancellation during cleanup does not restart
or interrupt that cleanup. Known completed outcomes remain separate from
cleanup/cancellation flags. SIGKILL, host loss, escaped sessions and remote jobs
cannot be contained by this handler. Use the accepted remote cancellation route
when applicable. End-of-turn consumption still requires an actual host probe;
see [completion and waiting](../../workflow-effectiveness.md#completion-and-waiting).

The cleanup wait reaps the leader before checking group absence. Temporary
permission failures in group inspection are retried only within the existing
cleanup deadline; they never count as absence. Unresolved permission or signal
failures retain `cleanup_confirmed: false` with diagnostics. The helper is POSIX;
qualify the actual host's signalling policy rather than assume a nested sandbox
permits cleanup. A terminal status file prevents worker rerun; use delivery
recovery for that existing completed job.

A permission failure on the first post-success group inspection also enters the
bounded cleanup routine. It cannot skip retries; persistent uncertainty still
records unconfirmed cleanup and never permits overlapping follow-up.
