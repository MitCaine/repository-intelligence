#!/usr/bin/env python3
"""Detach one bounded command, save its result, and attempt one terminal notification."""

import argparse
import fcntl
import hashlib
import tempfile
import json
import math
import os
from pathlib import Path
import re
import signal
import threading
import subprocess
import sys
import time


UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DEFAULT_TIMEOUT_SECONDS = 3600
QUEUE_TIMEOUT_SECONDS = 30
TERM_GRACE_SECONDS = 5
CLEANUP_WAIT_SECONDS = 2


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError as error:
        raise PermissionError(error.errno, f'Cannot inspect owned process group {group}') from error


def wait_group_absence(process, seconds):
    deadline = time.monotonic() + seconds
    last_error = None
    while True:
        process.poll()  # Reap the leader before probing a possibly zombie-only group.
        try:
            if not group_exists(process.pid):
                return True, None
            last_error = None
        except PermissionError as error:
            # An unavailable observation is never absence. Retry within the cleanup budget.
            last_error = error
        if time.monotonic() >= deadline:
            return False, last_error
        time.sleep(min(.05, max(0, deadline - time.monotonic())))


def terminate_group(process):
    """Leader exit does not imply group exit; require a confirmed absent group."""
    signal_error = None
    for signum, grace in ((signal.SIGTERM, TERM_GRACE_SECONDS),
                          (signal.SIGKILL, CLEANUP_WAIT_SECONDS)):
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            signal_error = PermissionError(error.errno,
                f'Cannot send signal {signum} to owned process group {process.pid}')
        absent, inspection_error = wait_group_absence(process, grace)
        if absent:
            return process.wait(timeout=CLEANUP_WAIT_SECONDS), True
    code = process.wait(timeout=CLEANUP_WAIT_SECONDS)
    if inspection_error or signal_error:
        raise inspection_error or signal_error
    return code, False


def save_json(path, data):
    fd, raw = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(json.dumps(data, indent=2, sort_keys=True) + '\n')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_exclusive(path, text):
    """Attempt evidence is append-only; never replace a prior record."""
    with path.open('x') as output:
        output.write(text)



def notify(config, *, recovery=False):
    # Serialize notification attempts; an accepted attempt cannot be resent by recovery.
    with (Path(config['job_dir']) / 'delivery.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return notify_locked(config, recovery=recovery)


def notify_locked(config, *, recovery=False):
    job_dir = Path(config['job_dir'])
    status_path = job_dir / 'status.json'
    status = json.loads(status_path.read_text())
    delivery_path = job_dir / 'delivery.json'
    queue_path = job_dir / 'queue.log'
    existing = json.loads(delivery_path.read_text()) if delivery_path.exists() else None
    if recovery and existing and existing['state'] == 'accepted_by_cli':
        raise ValueError('Notification was accepted by codex queue; do not resend')
    history = job_dir / 'delivery-attempts'
    history.mkdir(exist_ok=True)
    if recovery:
        # A durable result may precede an interrupted current-summary update.
        # Acceptance in retained evidence is authoritative: never send again.
        for prior in sorted(history.iterdir(), reverse=True):
            if not prior.name.isdecimal():
                continue
            result_path = prior / 'result.json'
            if result_path.exists():
                retained = json.loads(result_path.read_text())
                if retained['state'] == 'accepted_by_cli':
                    save_json(delivery_path, retained)
                    raise ValueError('Notification was accepted by codex queue; do not resend')
    # Preserve summaries produced by older helpers before replacing them.
    if existing:
        prior = history / f"{existing['attempts']:06d}"
        if not prior.exists():
            prior.mkdir()
            save_exclusive(prior / 'legacy.json', delivery_path.read_text())
            if queue_path.exists():
                save_exclusive(prior / 'queue.log', queue_path.read_text())
    attempts = 1 + max([existing['attempts'] if existing else 0] +
                       [int(path.name) for path in history.iterdir() if path.name.isdecimal()])
    attempt = history / f'{attempts:06d}'
    attempt.mkdir()  # Reserved while holding the notification lock.
    delivery = {'state': 'attempting', 'attempts': attempts,
                'status_path': str(status_path), 'thread': config['thread'],
                'attempt_path': str(attempt), 'started_at_epoch': time.time(),
                'status_sha256': hashlib.sha256(status_path.read_bytes()).hexdigest()}
    save_exclusive(attempt / 'attempting.json', json.dumps(delivery, indent=2) + '\n')
    save_json(delivery_path, delivery)
    message = (f"{config['label']}: {status['outcome']}. Status: {status_path}. "
               f"{config['follow_up']}" + (' Cleanup unresolved; block overlapping follow-up.'
               if status.get('cleanup_confirmed') is False else ''))
    try:
        queued = subprocess.run(['codex', 'queue', '--thread', config['thread'],
                                 '--message', message], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="backslashreplace",
                                timeout=QUEUE_TIMEOUT_SECONDS)
        delivery['state'] = 'accepted_by_cli' if queued.returncode == 0 else 'rejected_by_cli'
        delivery['exit_code'] = queued.returncode
        diagnostic = f"exit_code={queued.returncode}\n{queued.stdout}"
    except (OSError, subprocess.SubprocessError) as error:
        delivery['state'] = 'uncertain'
        delivery['error'] = f'{type(error).__name__}: {error}'
        diagnostic = f"delivery uncertain: {delivery['error']}\n"
    delivery['finished_at_epoch'] = time.time()
    save_exclusive(attempt / 'queue.log', diagnostic)
    save_exclusive(attempt / 'result.json', json.dumps(delivery, indent=2) + '\n')
    queue_path.write_text(diagnostic)
    save_json(delivery_path, delivery)
    return delivery


class WatchCancelled(Exception):
    pass


def watch(config):
    job_dir = Path(config['job_dir'])
    status_path = job_dir / 'status.json'
    if status_path.exists():
        raise ValueError('Terminal result already retained; recover delivery without rerunning the command')
    output_path = job_dir / 'output.log'
    started = time.time()
    outcome, exit_code, detail = 'watcher_error', None, ''
    cleanup_confirmed, cleanup_error = None, None
    process = None
    cancelled = False
    cleaning = False
    launching = False
    handlers = {}

    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
        if not cleaning and not launching:
            raise WatchCancelled(f'watcher cancellation signal {signum}')

    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            handlers[signum] = signal.signal(signum, cancel)
    try:
        try:
            with output_path.open('wb') as output:
                launching = True
                try:
                    process = subprocess.Popen(config['command'], cwd=config['cwd'],
                                               stdout=output, stderr=subprocess.STDOUT,
                                               start_new_session=True)
                finally:
                    launching = False
                if cancelled:
                    raise WatchCancelled('watcher cancelled during launch')
                try:
                    exit_code = process.wait(timeout=config['timeout_seconds'])
                except subprocess.TimeoutExpired:
                    outcome, detail = 'timeout', 'deadline exceeded'
                else:
                    outcome = ('success' if exit_code == 0 else
                               'signal_terminated' if exit_code < 0 else 'failure')
                    detail = f'command outcome {outcome}; exit {exit_code}'
        except (WatchCancelled, KeyboardInterrupt) as error:
            cancelled = True
            if outcome not in ('success', 'failure', 'signal_terminated', 'timeout'):
                outcome = 'interrupted'
            detail += f'; {type(error).__name__}: {error}'
        except Exception as error:
            detail = f'watcher error: {type(error).__name__}: {error}'
            if outcome not in ('success', 'failure', 'signal_terminated', 'timeout'):
                outcome = ('lost_connectivity' if isinstance(error, (ConnectionError, BrokenPipeError))
                           else 'watcher_error')
        finally:
            cleaning = True
            if process is not None:
                cleanup_confirmed = False
                try:
                    try:
                        absent = outcome == 'success' and not group_exists(process.pid)
                    except PermissionError:
                        # First observation uncertainty must enter bounded cleanup too.
                        absent = False
                    if absent:
                        cleanup_confirmed = True
                    else:
                        cleanup_code, cleanup_confirmed = terminate_group(process)
                        if exit_code is None:
                            exit_code = cleanup_code
                except Exception as error:
                    cleanup_error = f'{type(error).__name__}: {error}'
                detail += ('; process group absent after cleanup' if cleanup_confirmed else
                           '; cleanup unresolved; do not retry overlapping work')
        status = {'outcome': outcome, 'exit_code': exit_code, 'detail': detail,
                  'cleanup_confirmed': cleanup_confirmed, 'cleanup_error': cleanup_error,
                  'cancel_requested': cancelled,
                  'started_at_epoch': started, 'finished_at_epoch': time.time(),
                  'command': config['command'], 'cwd': config['cwd'],
                  'thread': config['thread'], 'label': config['label']}
        save_json(status_path, status)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    notify(config)


def launch(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--thread', required=True)
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--job-dir', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--follow-up', required=True)
    parser.add_argument('--timeout-seconds', type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not UUID.fullmatch(args.thread):
        parser.error('--thread must be a verified UUID')
    if not command:
        parser.error('command required after --')
    if not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
        parser.error('--timeout-seconds must be finite and positive')
    cwd = Path(args.cwd).resolve(strict=True)
    if not cwd.is_dir():
        parser.error('--cwd must be a directory')
    job_dir = Path(args.job_dir).resolve()
    try:
        help_result = subprocess.run(['codex', 'queue', '--help'], capture_output=True,
                                     text=True, errors="backslashreplace", timeout=10)
        if help_result.returncode or '--thread' not in help_result.stdout or '--message' not in help_result.stdout:
            parser.error('codex queue --help does not confirm --thread and --message')
    except (OSError, subprocess.SubprocessError) as error:
        parser.error(f'codex queue capability check failed: {error}')
    job_dir.mkdir(parents=True, exist_ok=False)
    config = {'thread': args.thread, 'cwd': str(cwd), 'job_dir': str(job_dir),
              'label': args.label, 'follow_up': args.follow_up,
              'timeout_seconds': args.timeout_seconds, 'command': command}
    config_path = job_dir / 'config.json'
    save_json(config_path, config)
    with (job_dir / 'watcher.log').open('wb') as watcher_log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                    '--worker', str(config_path)], cwd=str(cwd),
                                   stdin=subprocess.DEVNULL, stdout=watcher_log,
                                   stderr=subprocess.STDOUT, start_new_session=True,
                                   close_fds=True)
    print(f'watcher_pid={process.pid} job_dir={job_dir}')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        watch(json.loads(Path(sys.argv[2]).read_text()))
    elif len(sys.argv) == 3 and sys.argv[1] == '--redeliver':
        config_path = Path(sys.argv[2])
        config = json.loads(config_path.read_text())
        delivery = notify(config, recovery=True)
        print(json.dumps(delivery, indent=2))
    else:
        launch()


if __name__ == '__main__':
    main()
