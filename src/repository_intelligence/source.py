"""Identify exact source bytes without requiring a language parser."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


SCHEMA_VERSION = 2


def git_object_format(root: Path) -> str | None:
    """Return this checkout's storage format, if root is in a Git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-object-format=storage"],
            capture_output=True, text=True, check=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    format_name = result.stdout.strip()
    return format_name if format_name in {"sha1", "sha256"} else None


def identify_bytes(path: Path, source: bytes, *, root: Path,
                   object_format: str | None = None) -> dict:
    """Bind a canonical in-root path and optional computed Git ID to bytes."""
    resolved_root = root.resolve()
    relative = path.resolve().relative_to(resolved_root).as_posix()
    blob = None
    if object_format is not None:
        if object_format not in {"sha1", "sha256"}:
            raise ValueError("Unsupported Git object format")
        content = f"blob {len(source)}\0".encode() + source
        blob = {"algorithm": object_format,
                "object_id": hashlib.new(object_format, content).hexdigest(),
                "meaning": "computed from bytes; not checkout attestation"}
    return {"relative_path": relative, "byte_count": len(source),
            "raw_sha256": hashlib.sha256(source).hexdigest(), "git_blob": blob}
