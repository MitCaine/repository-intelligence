#!/usr/bin/env python3
"""Detach one command, save its terminal result, and queue one notification."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def save_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def watch(config):
    job_dir = Path(config["job_dir"])
    status_path = job_dir / "status.json"
    output_path = job_dir / "output.log"
    queue_path = job_dir / "queue.log"
    started = time.time()
    outcome = "failure"
    exit_code = None
    detail = ""
    try:
        with output_path.open("wb") as output:
            process = subprocess.Popen(config["command"], cwd=config["cwd"], stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                exit_code = process.wait(timeout=config["timeout_seconds"])
                outcome = "success" if exit_code == 0 else "failure"
            except subprocess.TimeoutExpired:
                outcome = "timeout"
                detail = "deadline exceeded; process group terminated"
                os.killpg(process.pid, 15)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, 9)
                    process.wait()
    except Exception as error:
        detail = f"watcher error: {type(error).__name__}: {error}"
        outcome = "lost_connectivity" if isinstance(error, (ConnectionError, BrokenPipeError)) else "failure"

    status = {"outcome": outcome, "exit_code": exit_code, "detail": detail,
              "started_at_epoch": started, "finished_at_epoch": time.time(),
              "command": config["command"], "cwd": config["cwd"],
              "thread": config["thread"], "label": config["label"]}
    save_json(status_path, status)
    message = f'{config["label"]}: {outcome}. Status: {status_path}. {config["follow_up"]}'
    try:
        queued = subprocess.run(["codex", "queue", "--thread", config["thread"], "--message", message],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        queue_path.write_text(f"exit_code={queued.returncode}\n{queued.stdout}")
    except Exception as error:
        queue_path.write_text(f"delivery uncertain; no retry: {type(error).__name__}: {error}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--follow-up", required=True)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not UUID.fullmatch(args.thread):
        parser.error("--thread must be a verified UUID")
    if not command:
        parser.error("command required after --")
    if args.timeout_seconds is not None and args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    cwd = Path(args.cwd).resolve(strict=True)
    if not cwd.is_dir():
        parser.error("--cwd must be a directory")
    job_dir = Path(args.job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=False)
    help_result = subprocess.run(["codex", "queue", "--help"], capture_output=True, text=True)
    if help_result.returncode or "--thread" not in help_result.stdout or "--message" not in help_result.stdout:
        job_dir.rmdir()
        parser.error("codex queue --help does not confirm --thread and --message")
    config = {"thread": args.thread, "cwd": str(cwd), "job_dir": str(job_dir),
              "label": args.label, "follow_up": args.follow_up,
              "timeout_seconds": args.timeout_seconds, "command": command}
    config_path = job_dir / "config.json"
    save_json(config_path, config)
    with (job_dir / "watcher.log").open("wb") as watcher_log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(config_path)],
                                   cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=watcher_log,
                                   stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    print(f"watcher_pid={process.pid} job_dir={job_dir}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        watch(json.loads(Path(sys.argv[2]).read_text()))
    else:
        main()
