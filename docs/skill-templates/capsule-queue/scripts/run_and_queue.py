#!/usr/bin/env python3
"""Detach one bounded command, save its result, and attempt one terminal notification."""

import argparse
import json
import math
import os
from pathlib import Path
import re
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


def terminate_group(process):
    """Leader exit does not imply that its process group has exited."""
    group = process.pid
    try:
        os.killpg(group, 15)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + TERM_GRACE_SECONDS
    while group_exists(group) and time.monotonic() < deadline:
        process.poll()  # reap the leader without using its exit as group proof
        time.sleep(0.05)
    try:
        os.killpg(group, 9)
    except ProcessLookupError:
        pass
    code = process.wait(timeout=CLEANUP_WAIT_SECONDS)
    deadline = time.monotonic() + CLEANUP_WAIT_SECONDS
    while group_exists(group) and time.monotonic() < deadline:
        time.sleep(0.05)
    return code, not group_exists(group)


def save_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    os.replace(temporary, path)


def notify(config, *, recovery=False):
    job_dir = Path(config['job_dir'])
    status_path = job_dir / 'status.json'
    status = json.loads(status_path.read_text())
    delivery_path = job_dir / 'delivery.json'
    queue_path = job_dir / 'queue.log'
    existing = json.loads(delivery_path.read_text()) if delivery_path.exists() else None
    if recovery and existing and existing['state'] == 'accepted_by_cli':
        raise ValueError('Notification was accepted by codex queue; do not resend')
    attempts = 1 + (existing['attempts'] if existing else 0)
    delivery = {'state': 'attempting', 'attempts': attempts,
                'status_path': str(status_path), 'thread': config['thread']}
    save_json(delivery_path, delivery)
    message = (f"{config['label']}: {status['outcome']}. Status: {status_path}. "
               f"{config['follow_up']}")
    try:
        queued = subprocess.run(['codex', 'queue', '--thread', config['thread'],
                                 '--message', message], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                timeout=QUEUE_TIMEOUT_SECONDS)
        delivery['state'] = 'accepted_by_cli' if queued.returncode == 0 else 'rejected_by_cli'
        delivery['exit_code'] = queued.returncode
        queue_path.write_text(f"exit_code={queued.returncode}\n{queued.stdout}")
    except (OSError, subprocess.SubprocessError) as error:
        delivery['state'] = 'uncertain'
        delivery['error'] = f'{type(error).__name__}: {error}'
        queue_path.write_text(f"delivery uncertain: {delivery['error']}\n")
    save_json(delivery_path, delivery)
    return delivery


def watch(config):
    job_dir = Path(config['job_dir'])
    status_path = job_dir / 'status.json'
    output_path = job_dir / 'output.log'
    started = time.time()
    outcome = 'watcher_error'
    exit_code = None
    detail = ''
    cleanup_confirmed = None
    try:
        with output_path.open('wb') as output:
            process = subprocess.Popen(config['command'], cwd=config['cwd'],
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                exit_code = process.wait(timeout=config['timeout_seconds'])
                outcome = ('success' if exit_code == 0 else
                           'signal_terminated' if exit_code < 0 else 'failure')
                if exit_code < 0:
                    detail = f'terminated by signal {-exit_code}; intent unknown'
            except subprocess.TimeoutExpired:
                outcome = 'timeout'
                cleanup_confirmed = False
                exit_code, cleanup_confirmed = terminate_group(process)
                detail = ('deadline exceeded; process group absent after cleanup' if cleanup_confirmed
                          else 'deadline exceeded; cleanup unresolved; do not retry overlapping work')
    except Exception as error:
        detail = f'watcher error: {type(error).__name__}: {error}'
        if outcome != 'timeout':
            outcome = ('lost_connectivity' if isinstance(error, (ConnectionError, BrokenPipeError))
                       else 'watcher_error')

    status = {'outcome': outcome, 'exit_code': exit_code, 'detail': detail,
              'cleanup_confirmed': cleanup_confirmed,
              'started_at_epoch': started, 'finished_at_epoch': time.time(),
              'command': config['command'], 'cwd': config['cwd'],
              'thread': config['thread'], 'label': config['label']}
    save_json(status_path, status)
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
                                     text=True, timeout=10)
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
