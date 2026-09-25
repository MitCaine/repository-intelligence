"""One opt-in rust-analyzer question: resolve a Rust reference definition."""

from __future__ import annotations

import hashlib
import json
import os
import select
import subprocess
import time
from pathlib import Path
from urllib.parse import unquote, urlparse


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot(root: Path) -> dict:
    """Checksum local Rust/Cargo inputs, without claiming an atomic workspace view."""
    files = []
    for current, directories, names in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories
                          if name not in {"target", ".git", "node_modules"}
                          and not (Path(current) / name).is_symlink()]
        for name in names:
            path = Path(current) / name
            if (name.endswith(".rs") or name in {"Cargo.toml", "Cargo.lock",
                                                   "rust-toolchain", "rust-toolchain.toml"}
                    or path.parent.name == ".cargo" and name in {"config", "config.toml"}):
                if path.is_file() and not path.is_symlink():
                    files.append(path)
    records = [(path.relative_to(root).as_posix(), _sha(path.read_bytes()))
               for path in sorted(set(files))]
    digest = _sha(json.dumps(records, separators=(",", ":")).encode())
    return {"digest_sha256": digest, "file_count": len(records),
            "materialization": "non_atomic_working_tree"}


class _RustAnalyzer:
    def __init__(self, executable: str, root: Path, configuration: dict, timeout: float):
        self.proc = subprocess.Popen([executable], cwd=root, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.buffer = b""
        self.configuration = configuration
        self.deadline = time.monotonic() + timeout
        self.last_status = None

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        if self.proc.stdin is not None:
            self.proc.stdin.close()
        if self.proc.stdout is not None:
            self.proc.stdout.close()

    def send(self, message: dict) -> None:
        data = json.dumps(message, separators=(",", ":")).encode()
        assert self.proc.stdin is not None
        self.proc.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode() + data)
        self.proc.stdin.flush()

    def receive(self) -> dict:
        assert self.proc.stdout is not None
        while b"\r\n\r\n" not in self.buffer:
            self._read()
        header, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        lengths = [int(line.split(b":", 1)[1].strip()) for line in header.split(b"\r\n")
                   if line.lower().startswith(b"content-length:")]
        if len(lengths) != 1 or not 0 < lengths[0] <= 8_000_000:
            raise ValueError("Invalid rust-analyzer message length")
        while len(self.buffer) < lengths[0]:
            self._read()
        body, self.buffer = self.buffer[:lengths[0]], self.buffer[lengths[0]:]
        return json.loads(body)

    def _read(self) -> None:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or not select.select([self.proc.stdout], [], [], remaining)[0]:
            raise TimeoutError("rust-analyzer did not answer in time")
        assert self.proc.stdout is not None
        chunk = os.read(self.proc.stdout.fileno(), 65536)
        if not chunk:
            raise RuntimeError("rust-analyzer closed its output")
        self.buffer += chunk

    def request(self, request_id: int, method: str, params: dict) -> object:
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            message = self.receive()
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise RuntimeError(f"rust-analyzer {method}: {message['error']}")
                return message.get("result")
            self._handle(message)

    def _handle(self, message: dict) -> None:
        if message.get("method") == "experimental/serverStatus":
            self.last_status = message.get("params")
        if "id" in message and "method" in message:
            response = ([self.configuration] * len(message.get("params", {}).get("items", []))
                        if message["method"] == "workspace/configuration" else None)
            self.send({"jsonrpc": "2.0", "id": message["id"], "result": response})

    def wait_ready(self) -> None:
        while not (isinstance(self.last_status, dict) and
                   self.last_status.get("quiescent")):
            self._handle(self.receive())


def resolve_definition(project_root: Path, source_path: Path, line: int, column: int, *,
                       features: tuple[str, ...], no_default_features: bool,
                       target: str, analyzer: str = "rust-analyzer", timeout: float = 45) -> dict:
    """Resolve one 1-based source position under caller-specified Cargo settings.

    Native analysis is optional and never used by ordinary structural scans.
    """
    root = project_root.resolve()
    source_path = source_path.resolve()
    if not (root / "Cargo.toml").is_file() or source_path.suffix != ".rs" \
            or not source_path.is_file() or not source_path.is_relative_to(root):
        raise ValueError("Provide a Rust file inside a Cargo project")
    if (not isinstance(features, tuple) or not all(isinstance(f, str) for f in features)
            or type(no_default_features) is not bool or not isinstance(target, str)
            or not target or line < 1 or column < 1):
        raise ValueError("Explicit Cargo features, default-feature choice, target, and position are required")
    source = source_path.read_bytes()
    decoded = source.decode("utf-8")
    lines = decoded.splitlines()
    if line > len(lines) or column > len(lines[line - 1]) + 1:
        raise ValueError("Reference position is outside source")
    lsp_character = len(lines[line - 1][:column - 1].encode("utf-16-le")) // 2
    before = _snapshot(root)
    version = subprocess.run([analyzer, "--version"], text=True, capture_output=True,
                             timeout=10, check=True).stdout.strip()
    configuration = {"cargo": {"features": list(features),
                               "noDefaultFeatures": no_default_features,
                               "target": target, "allTargets": False, "noDeps": True,
                               "buildScripts": {"enable": False}},
                     "procMacro": {"enable": False}, "checkOnSave": False}
    packet = {"result_kind": "rust_semantic_definition_v1",
              "question": "definition_of_reference",
              "reference": {"path": source_path.relative_to(root).as_posix(),
                            "line": line, "column": column, "raw_sha256": _sha(source)},
              "provider": {"name": "rust-analyzer", "version": version},
              "configuration": configuration,
              "source_snapshot": before,
              "limitations": ["Workspace reads are non-atomic; pre/post local checksums are not attestation",
                              "External dependencies and sysroot are not included in the local digest",
                              "Build scripts and procedural macros are disabled",
                              "A resolved target does not imply global semantic completeness"],
              "targets": []}
    client = _RustAnalyzer(analyzer, root, configuration, timeout)
    try:
        client.request(1, "initialize", {"processId": os.getpid(), "rootUri": root.as_uri(),
                                          "workspaceFolders": [{"uri": root.as_uri(),
                                                                "name": root.name}],
                                          "capabilities": {"workspace": {"configuration": True},
                                                           "textDocument": {"definition": {}},
                                                           "experimental": {"serverStatusNotification": True}},
                                          "initializationOptions": configuration})
        client.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        client.send({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                     "params": {"textDocument": {"uri": source_path.as_uri(),
                                                 "languageId": "rust", "version": 1,
                                                 "text": decoded}}})
        client.wait_ready()
        packet["provider_status"] = client.last_status
        if client.last_status and client.last_status.get("health") != "ok":
            packet["limitations"].append("Analyzer reported a non-OK workspace status")
        answer = client.request(2, "textDocument/definition",
                                {"textDocument": {"uri": source_path.as_uri()},
                                 "position": {"line": line - 1, "character": lsp_character}})
    finally:
        client.close()
    after = _snapshot(root)
    if before != after or _sha(source_path.read_bytes()) != _sha(source):
        return {**packet, "status": "incomplete_changed_source",
                "source_snapshot_after": after}
    locations = answer if isinstance(answer, list) else [answer] if answer else []
    for location in locations:
        uri = location.get("uri") or location.get("targetUri")
        span = location.get("range") or location.get("targetSelectionRange")
        if not uri or not span:
            continue
        parsed = urlparse(uri)
        target_path = Path(unquote(parsed.path)) if parsed.scheme == "file" else None
        identity = None
        if target_path is not None and target_path.is_file():
            target_bytes = target_path.read_bytes()
            identity = {"raw_sha256": _sha(target_bytes),
                        "byte_count": len(target_bytes),
                        "within_project": target_path.is_relative_to(root)}
        packet["targets"].append({"uri": uri, "range": span, "source_identity": identity})
    packet["status"] = "resolved" if packet["targets"] else "unresolved"
    return packet
