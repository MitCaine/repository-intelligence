"""Read-only controller observation of exact Git source materialization."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
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
