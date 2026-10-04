---
name: capsule-queue
description: Queue one terminal result for an external agent job, capsule qualification, or CI run that otherwise needs repeated polling. Keep controller, implementor, and reviewer authority separate; use native completion when it already wakes the controller.
---

# Capsule queue

Use a watcher for an external job lacking reliable native completion. Native
subagents default to event-based blocking waits; ordinary commands return directly.
Do not duplicate a verified callback. Follow the selected
[project procedure](references/project-procedure.md#waiting-and-recovery) for
waiting discipline, agent capacity, terminal stops and bounded diagnosis. Routine
coordination/diagnosis needs no repeated approval; preserve scope, disclosure,
stops and attempt limits. A watcher only observes/reports, never grants retries,
qualification, review approval or integration authority.

## Delivery and routing

- Establish the route before dispatch. Active-parent delivery does not prove idle
  wake-up. End the turn only after the exact controller/host route has consumed
  a harmless terminal notification without a human nudge. CLI acceptance is not
  consumption. Reuse that observation until relevant inputs change or delivery
  fails; otherwise use the supported bounded blocking wait.
- Verify the destination task UUID from `CODEX_THREAD_ID` or runtime metadata,
  never recency or role name. Check host `codex queue --help` for supported options.
  Queue targets a Codex session; a ChatGPT Work controller needs a tested bridge.
  Do not claim an untested native-subagent watcher is supported.
- Bind the active assignment, job/candidate/check identity, destination, mechanism,
  deadline and evidence paths. RI locations remain exact-source navigation, not
  qualification or reviewer verdicts.
- Launch a new command once. For an existing job, wrap its blocking completion
  event/watch command, never restart it to attach a watcher. If only status checks
  exist, use bounded polling/backoff inside a dedicated watcher, not model turns.
- Retain raw untrusted logs outside the candidate under an authorized evidence
  root. Send one concise terminal message with outcome, status path and next action.
  On receipt authenticate `status.json`, `delivery.json` and relevant `output.log`
  against the assignment before continuing.

## Terminal interpretation

Keep command completion, cleanup, notification acceptance and controller consumption
separate. Distinguish success, failure, timeout, signal and lost connectivity from
actual evidence; missing PID/connection is not success and a signal alone is not
intentional cancellation. Wrapped nonzero connectivity loss is failure unless its
watcher records a more specific outcome. Preserve failures and unknown reasons;
diagnose before selecting recovery, without resuming a stopped attempt. Missing
proof cannot pass. Follow the selected procedure's bounded diagnostic-only route
rather than guess a replan or reset an allowance.

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
see [completion and waiting](references/project-procedure.md#waiting-and-recovery).

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
