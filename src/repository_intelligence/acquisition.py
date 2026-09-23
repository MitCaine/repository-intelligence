"""Read-only controller observations of exact source and local input material."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
from types import MappingProxyType
from typing import Any

from .errors import ValidationError
from .validation import _canonical_json, _require_exact_keys, _require_mapping, _require_text, _typed_equal


_SOURCE_FIELDS = (
    "source_id", "repository", "revision", "language",
    "source_state_mode", "configuration_id",
)
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_MUTABLE = frozenset({"all", "any", "current", "discover", "discovered", "head", "last", "latest", "next", "unknown"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOCAL_INPUT_FIELDS = ("input_id", "source_or_registry_id", "kind", "sha256")
_MAX_LOCAL_INPUT_BYTES = 64 * 1024 * 1024


def _concrete_local_identity(value: Any, name: str) -> str:
    text = _require_text(value, name)
    if (
        not _IDENTIFIER.fullmatch(text)
        or ".." in text
        or set(re.split(r"[^a-z0-9]+", text.lower())) & _MUTABLE
    ):
        raise ValidationError(f"{name} must be an authored concrete identity")
    return text


class LocalFileAcquisitionObservation:
    """One process-local, observer-issued record of controller-read bytes."""

    __slots__ = ("_owner", "_nonce", "_payload", "_signature", "_sealed")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError("local acquisition observations can only be minted by an observer")

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("local acquisition observation is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("local acquisition observation is immutable")

    def __copy__(self) -> "LocalFileAcquisitionObservation":
        raise ValidationError("local acquisition observations cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> "LocalFileAcquisitionObservation":
        raise ValidationError("local acquisition observations cannot be copied")

    def as_dict(self) -> dict[str, Any]:
        return dict(self._payload)


class LocalFileAcquisitionObserver:
    """Observe one controller-chosen regular file against an authored digest.

    This is not a materialization-closure or execution-readiness authority.
    """

    __slots__ = ("_identity", "_path", "_secret", "_issued", "_sealed")

    def __init__(self, authored_identity: Mapping[str, Any], local_path: Path | str) -> None:
        identity = _require_mapping(authored_identity, "authored local input")
        _require_exact_keys(identity, _LOCAL_INPUT_FIELDS, _LOCAL_INPUT_FIELDS, "authored local input")
        accepted = {
            key: _concrete_local_identity(identity[key], f"authored local input {key}")
            for key in _LOCAL_INPUT_FIELDS if key != "sha256"
        }
        digest = _require_text(identity["sha256"], "authored local input sha256")
        if not _SHA256.fullmatch(digest):
            raise ValidationError("authored local input sha256 must be exact lowercase hex")
        accepted["sha256"] = digest
        try:
            path = Path(os.path.abspath(os.fspath(local_path)))
        except (TypeError, ValueError, OSError) as exc:
            raise ValidationError("controller local input path is invalid") from exc
        object.__setattr__(self, "_identity", MappingProxyType(accepted))
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_secret", secrets.token_bytes(32))
        object.__setattr__(self, "_issued", {})
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("local acquisition observer authority is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("local acquisition observer authority is immutable")

    def _inspect(self) -> dict[str, Any]:
        path = self._path
        try:
            for component in (path, *path.parents):
                if stat.S_ISLNK(component.lstat().st_mode):
                    raise ValidationError("local input path traverses a symlink")
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode):
                raise ValidationError("local input must be a regular file")
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
            )
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    raise ValidationError("local input changed while opening")
                digest = hashlib.sha256()
                size = 0
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > _MAX_LOCAL_INPUT_BYTES:
                        raise ValidationError("local input exceeds bounded observation size")
                    digest.update(chunk)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            current = path.lstat()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValidationError("controller local input is unavailable or changed") from exc
        fingerprint = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if fingerprint(before) != fingerprint(opened) or fingerprint(opened) != fingerprint(after) or fingerprint(after) != fingerprint(current) or size != current.st_size:
            raise ValidationError("local input changed during observation")
        if digest.hexdigest() != self._identity["sha256"]:
            raise ValidationError("local input bytes differ from authored digest")
        return {
            **self._identity,
            "observation_kind": "controller_read_regular_file",
            "materialized_path": str(path),
            "byte_size": size,
            "device": current.st_dev,
            "inode": current.st_ino,
            "mtime_ns": current.st_mtime_ns,
            "ctime_ns": current.st_ctime_ns,
        }

    def _signature(self, payload: Mapping[str, Any], nonce: str) -> str:
        return hmac.new(
            self._secret,
            _canonical_json({"nonce": nonce, "payload": payload}).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def observe(self) -> LocalFileAcquisitionObservation:
        payload = MappingProxyType(self._inspect())
        nonce = secrets.token_hex(32)
        result = object.__new__(LocalFileAcquisitionObservation)
        object.__setattr__(result, "_owner", self)
        object.__setattr__(result, "_nonce", nonce)
        object.__setattr__(result, "_payload", payload)
        object.__setattr__(result, "_signature", self._signature(payload, nonce))
        object.__setattr__(result, "_sealed", True)
        self._issued[nonce] = result
        return result

    def require(self, value: LocalFileAcquisitionObservation) -> Mapping[str, Any]:
        if type(value) is not LocalFileAcquisitionObservation or getattr(value, "_owner", None) is not self:
            raise ValidationError("local acquisition observation is not issued by this observer")
        nonce = getattr(value, "_nonce", None)
        payload = getattr(value, "_payload", None)
        signature = getattr(value, "_signature", None)
        if (
            type(nonce) is not str
            or self._issued.get(nonce) is not value
            or not isinstance(payload, Mapping)
            or type(signature) is not str
        ):
            raise ValidationError("local acquisition observation is not issued by this observer")
        try:
            expected = self._signature(payload, nonce)
        except (TypeError, ValueError, ValidationError):
            raise ValidationError("local acquisition observation signature is invalid") from None
        if not hmac.compare_digest(signature, expected):
            raise ValidationError("local acquisition observation signature is invalid")
        if not _typed_equal(payload, self._inspect()):
            raise ValidationError("local input changed after observation")
        return payload


class GitSourceObservation:
    """One sealed observation minted by a GitSourceObserver."""

    __slots__ = ("_owner", "_nonce", "_payload", "_signature", "_sealed")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError("Git source observations can only be minted by an observer")

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("Git source observation is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Git source observation is immutable")

    def __copy__(self) -> "GitSourceObservation":
        raise ValidationError("Git source observations cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> "GitSourceObservation":
        raise ValidationError("Git source observations cannot be copied")

    def as_dict(self) -> dict[str, Any]:
        return dict(self._payload)


class GitSourceObserver:
    """Bind an authored pin to one controller chosen root and inspect real Git."""

    __slots__ = ("_pin", "_root", "_secret", "_issued", "_sealed")

    def __init__(self, authored_pin: Mapping[str, Any], repository_root: Path | str) -> None:
        pin = _require_mapping(authored_pin, "authored Git source pin")
        _require_exact_keys(pin, _SOURCE_FIELDS, _SOURCE_FIELDS, "authored Git source pin")
        accepted: dict[str, str] = {}
        for key in _SOURCE_FIELDS:
            value = _require_text(pin[key], f"authored Git source {key}")
            if (
                not _IDENTIFIER.fullmatch(value)
                or ".." in value
                or set(re.split(r"[^a-z0-9]+", value.lower())) & _MUTABLE
            ):
                raise ValidationError(f"authored Git source {key} is not concrete")
            accepted[key] = value
        if not _SHA1.fullmatch(accepted["revision"]):
            raise ValidationError("authored Git source revision must be a lowercase 40-character SHA")
        try:
            root = Path(repository_root).resolve(strict=True)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ValidationError("controller Git source root is unavailable") from exc
        if not root.is_dir():
            raise ValidationError("controller Git source root must be a directory")
        object.__setattr__(self, "_pin", MappingProxyType(accepted))
        object.__setattr__(self, "_root", root)
        object.__setattr__(self, "_secret", secrets.token_bytes(32))
        object.__setattr__(self, "_issued", {})
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("Git source observer authority is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Git source observer authority is immutable")

    def _git(self, *arguments: str) -> str:
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("GIT_")
        }
        environment.update({
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
        })
        try:
            result = subprocess.run(
                (
                    "git", "-c", "core.fsmonitor=false",
                    "-c", "core.hooksPath=/dev/null",
                    "-c", "submodule.recurse=false",
                    "-C", str(self._root), *arguments,
                ),
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
        except OSError as exc:
            raise ValidationError("Git source observation command unavailable") from exc
        if result.returncode != 0:
            raise ValidationError("Git source observation command failed")
        return result.stdout.strip()

    def _inspect(self) -> dict[str, Any]:
        top_level = self._git("rev-parse", "--show-toplevel")
        if Path(top_level).resolve() != self._root:
            raise ValidationError("Git source root does not match repository top level")
        revision = self._git("rev-parse", "--verify", "HEAD^{commit}")
        if revision != self._pin["revision"]:
            raise ValidationError("Git source HEAD differs from authored revision")
        if self._git("cat-file", "-t", revision) != "commit":
            raise ValidationError("Git source revision is not a commit object")
        tree_sha = self._git("rev-parse", "--verify", "HEAD^{tree}")
        if not _SHA1.fullmatch(tree_sha):
            raise ValidationError("Git source tree identity is malformed")
        if self._git("status", "--porcelain", "--untracked-files=all"):
            raise ValidationError("Git source checkout is not clean")
        if self._git("rev-parse", "--verify", "HEAD^{commit}") != revision:
            raise ValidationError("Git source HEAD changed during observation")
        return {
            **self._pin,
            "repository_root": str(self._root),
            "tree_sha": tree_sha,
            "observation_kind": "clean_exact_git_checkout",
        }

    def _signature(self, payload: Mapping[str, Any], nonce: str) -> str:
        return hmac.new(
            self._secret,
            _canonical_json({"nonce": nonce, "payload": payload}).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def observe(self) -> GitSourceObservation:
        payload = MappingProxyType(self._inspect())
        nonce = secrets.token_hex(32)
        result = object.__new__(GitSourceObservation)
        object.__setattr__(result, "_owner", self)
        object.__setattr__(result, "_nonce", nonce)
        object.__setattr__(result, "_payload", payload)
        object.__setattr__(result, "_signature", self._signature(payload, nonce))
        object.__setattr__(result, "_sealed", True)
        self._issued[nonce] = result
        return result

    def require(self, value: GitSourceObservation) -> Mapping[str, Any]:
        if type(value) is not GitSourceObservation or getattr(value, "_owner", None) is not self:
            raise ValidationError("Git source observation is not issued by this observer")
        nonce = getattr(value, "_nonce", None)
        payload = getattr(value, "_payload", None)
        signature = getattr(value, "_signature", None)
        if (
            type(nonce) is not str
            or self._issued.get(nonce) is not value
            or not isinstance(payload, Mapping)
            or type(signature) is not str
        ):
            raise ValidationError("Git source observation is not issued by this observer")
        try:
            expected = self._signature(payload, nonce)
        except (TypeError, ValueError, ValidationError):
            raise ValidationError("Git source observation signature is invalid") from None
        if not hmac.compare_digest(signature, expected):
            raise ValidationError("Git source observation signature is invalid")
        if not _typed_equal(payload, self._inspect()):
            raise ValidationError("Git source checkout changed after observation")
        return payload
