---
name: capsule-queue
description: Queue one terminal result for an external agent job, capsule qualification, or CI run that otherwise needs repeated polling. Keep controller, implementor, and reviewer authority separate; use native completion when it already wakes the controller.
---

# Capsule queue

Routine role coordination, failure-evidence inspection, factual explanation
requests and permitted completion-delivery recovery are included in the authorized
task; they do not require a new human approval just because a gate failed. Keep
existing scope, disclosure rules, attempt limits and stops intact. Follow
[standing controller authority](references/project-procedure.md#waiting-and-recovery)
when deciding whether a genuinely new approval is needed.

Use this skill when an external agent or other process needs a watcher to detect its terminal state and wake its controller. Native subagents and Codex threads with reliable completion channels use those channels. Ordinary commands return directly. Do not create a second notification when the runner already provides a reliable terminal callback. Establish the completion route at dispatch; do not spend repeated controller turns checking unchanged status.

## Verify wake-up before relying on queue

Before dispatch, select the terminal delivery route for the exact controller.
Receiving a result in an active blocking wait and waking an idle controller are
separate capabilities. Do not end the turn assuming native subagent completion
will start a new one. Use native completion while the supported blocking wait
remains active; end the turn only when idle wake-up is verified.

Use the queue watcher when native idle wake-up is unavailable and a supported
watcher can observe that job, but first verify that queue delivery actually wakes
the intended controller on this host. A small harmless delivery probe must reach
the exact idle controller and be consumed without a human nudge; CLI acceptance
alone is insufficient. Reuse that observation for the same host/controller route
until the route changes or delivery fails. Do not add duplicate notifications to
a verified native route. If neither route has verified idle wake-up, keep the
supported bounded blocking wait and state the limitation. Do not restart a job
to attach a watcher or claim an untested native-subagent watcher is supported.

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

After dispatch, wait for the terminal handoff. Reading the active workspace,
source diff, logs or interim test results to track progress is monitoring too;
it is not an alternative to status polling. Do not repeatedly restate the
contract or produce interim acceptance judgments while a role is working.
Controller candidate/scope/evidence verification begins after terminal delivery.
Unsolicited progress may be received without starting a monitoring loop.

Early intervention is limited to an actionable blocker/clarification delivered
by the role, a concrete safety concern, failed completion delivery or a direct
owner status request. Use only the reads necessary for that intervention, then
return to waiting. Independent preparation must be a specific already-authorized
activity that does not inspect or depend on the active role's unfinished work;
do it once, not as a recurring excuse to stay active. Supported wait resumptions
at host time limits are allowed; they do not authorize extra progress checks.

For a native subagent terminal return, the controller retains and authenticates
the handoff, records its disposition, then closes the completed agent, where available, through
the host's supported operation before dispatching the next fresh role. Completed
but open threads can consume capacity even with only one working subagent.
Do not close a running agent or discard its evidence. If no close operation is
available and fresh creation is blocked, record the limitation and use the
workflow's authorized last-resort idle-agent reuse with a complete reauthenticated
handoff. Keep review independent; never restart the completed job or reset its
allowance to regain capacity. See
[agent capacity recovery](references/project-procedure.md#waiting-and-recovery).

Distinguish nonterminal opening progress from the accepted terminal outcome.
Never use `stop_replan` as an acknowledgement while authentication is merely
pending. The role must establish the relevant trigger through bounded authorized
checks before emitting this last-resort outcome, with immediate stops retained
for confirmed violations or explicit owner instructions. An actual stopping event
still halts dependent work; do not reinterpret it as progress to resume a job.
See [stop-trigger checks](references/project-procedure.md#waiting-and-recovery).

When a blocker is found, hold execution and consolidate related findings through
one bounded authorized read-only capsule sweep before terminal closure where
supported. Keep diagnostic progress nonterminal; never misuse a stopping status
as an interim hold. If the host already finalized the stop, recover diagnosis
through a separate diagnostic-only follow-up before replacement planning, not
by resuming the job. See [diagnostic sweep](references/project-procedure.md#waiting-and-recovery).

A stopping terminal result requires diagnosis before replan: preserve its reason,
raw output, exact attempt identity and cleanup state. A bare `stop_replan` is not
proof the capsule needs rewriting. Record `reason unknown` if the evidence lacks
an explanation; obtain bounded authorized diagnostics before selecting recovery.
Do not restart or resume the stopped job to obtain that explanation. See
[stop diagnosis](references/project-procedure.md#waiting-and-recovery).

A bounded diagnostic-only follow-up to the stopping implementor is included in
the authorized task and needs no additional human approval. It may explain its
own stop through the existing authorized channel; this does not resume the job.
Retain the answer separately and wait through the supported completion route.
See [standing diagnostic authority](references/project-procedure.md#waiting-and-recovery).

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
