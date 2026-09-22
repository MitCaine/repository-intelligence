"""Oracle-leak detection with redacted monotonic attempt dispositions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import re
import threading
from typing import Any, Optional

from .errors import ValidationError
from .validation import _canonical_json, _deep_freeze, _json_value, _require_sequence, _require_text, _typed_equal


@dataclass(frozen=True)
class LeakageFinding:
    """Redacted reason for one oracle-leak scan hit; protected content is omitted."""

    path: str
    representation: str


@dataclass(frozen=True)
class LeakageDisposition:
    """Monotonic attempt-level oracle disposition and retained scan evidence."""

    attempt_id: str
    status: str
    invalidated: bool
    scan_count: int
    finding_count: int
    findings: tuple[LeakageFinding, ...]


def _is_scalar(value: Any) -> bool:
    """Return whether a supported value is a scalar rather than a container."""

    return value is None or type(value) in {bool, int, float, str}


def _composite_contains(container: Any, protected: Any) -> bool:
    """Detect protected composite material embedded in a larger supported structure."""

    if isinstance(protected, Mapping) and isinstance(container, Mapping):
        if not protected:
            return not container
        for key, value in protected.items():
            if key not in container:
                return False
            if _typed_equal(container[key], value):
                continue
            if not _is_scalar(value) and _composite_contains(container[key], value):
                continue
            return False
        return True
    if isinstance(protected, (list, tuple)) and isinstance(container, (list, tuple)):
        if not protected:
            return len(container) == 0
        if len(protected) == len(container):
            return _typed_equal(container, protected)
        return any(
            _typed_equal(tuple(container[index : index + len(protected)]), tuple(protected))
            for index in range(len(container) - len(protected) + 1)
        )
    return False


def _python_form(value: Any) -> str:
    """Render JSON-shaped values in the ordinary Python representation."""

    if isinstance(value, Mapping):
        return repr(dict(value))
    if isinstance(value, tuple):
        return repr(list(value))
    return repr(value)


def _text_contains_protected(text: str, protected: Any) -> Optional[str]:
    """Find supported scalar/composite encodings embedded in ordinary text."""

    if type(protected) is str:
        if protected == "":
            if '""' in text or "''" in text:
                return "text_empty_string"
        elif protected in text:
            return "text_scalar"
        return None
    if type(protected) is bool:
        words = ("true", "True") if protected else ("false", "False")
        for word in words:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", text):
                return "text_boolean"
        return None
    if type(protected) is int:
        token = str(protected)
        if re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(token) + r"(?![A-Za-z0-9_.-])", text):
            return "text_integer"
        return None
    if type(protected) is float:
        forms = {repr(protected), format(protected, ".15g")}
        for form in forms:
            if re.search(
                r"(?<![A-Za-z0-9_.-])" + re.escape(form) + r"(?![A-Za-z0-9_.-])",
                text,
            ):
                return "text_float"
        return None
    if protected is None:
        if re.search(r"(?<![A-Za-z0-9_])(null|None)(?![A-Za-z0-9_])", text):
            return "text_null"
        return None
    if isinstance(protected, (Mapping, list, tuple)):
        forms = {
            _canonical_json(protected),
            json.dumps(_json_value(protected), ensure_ascii=False, sort_keys=True, indent=2),
            _python_form(protected),
        }
        for form in forms:
            if form in text:
                return "text_composite"
    return None


class OracleLeakDetector:
    """Recursively scan supported traces for protected oracle material.

    Scans are monotonic per attempt.  Once a finding exists, later clean input
    can add a scan count but cannot restore ``clean`` or clear the invalidating
    disposition.  Protected values are type-aware, so ``False``, ``0``, and
    ``0.0`` remain distinct while empty strings, containers, null, scalar
    encodings, and composite serializations are still protected.
    """

    def __init__(self, protected_values: Sequence[Any]) -> None:
        if isinstance(protected_values, Mapping) or _is_scalar(protected_values):
            values = (protected_values,)
        else:
            values = _require_sequence(protected_values, "protected_values")
        if len(values) == 0:
            raise ValidationError("at least one protected oracle value is required")
        normalized = [_json_value(value, "protected_value") for value in values]
        self._protected = tuple(_deep_freeze(value) for value in normalized)
        self._lock = threading.RLock()
        self._dispositions: dict[str, LeakageDisposition] = {}

    @property
    def protected_count(self) -> int:
        """Return the number of protected records without revealing their content."""

        return len(self._protected)

    def _scan_value(self, value: Any, path: str) -> list[LeakageFinding]:
        findings: list[LeakageFinding] = []
        for protected in self._protected:
            if _typed_equal(value, protected):
                findings.append(LeakageFinding(path, "structured"))
            elif not _is_scalar(protected) and _composite_contains(value, protected):
                findings.append(LeakageFinding(path, "embedded_composite"))
        if isinstance(value, str):
            for protected in self._protected:
                representation = _text_contains_protected(value, protected)
                if representation is not None:
                    findings.append(LeakageFinding(path, representation))
        if isinstance(value, Mapping):
            for key in sorted(value):
                findings.extend(self._scan_value(key, f"{path}.<key>"))
                findings.extend(self._scan_value(value[key], f"{path}.{key}"))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                findings.extend(self._scan_value(item, f"{path}[{index}]"))
        return findings

    def scan(self, attempt_id: str, payload: Any) -> LeakageDisposition:
        """Scan a trace and retain a monotonic clean/leaked disposition."""

        _require_text(attempt_id, "attempt_id", identifier=True)
        _json_value(payload, "oracle_scan.payload")
        findings = self._scan_value(payload, "$")
        with self._lock:
            prior = self._dispositions.get(attempt_id)
            prior_findings = prior.findings if prior is not None else ()
            all_findings = prior_findings + tuple(findings)
            leaked = prior is not None and prior.status == "leaked"
            if findings:
                leaked = True
            disposition = LeakageDisposition(
                attempt_id=attempt_id,
                status="leaked" if leaked else "clean",
                invalidated=leaked,
                scan_count=(prior.scan_count if prior is not None else 0) + 1,
                finding_count=len(all_findings),
                findings=all_findings,
            )
            self._dispositions[attempt_id] = disposition
            return disposition

    def disposition(self, attempt_id: str) -> LeakageDisposition:
        """Return a retained disposition or fail rather than inventing clean state."""

        _require_text(attempt_id, "attempt_id", identifier=True)
        with self._lock:
            if attempt_id not in self._dispositions:
                raise ValidationError("oracle disposition has not been observed")
            return self._dispositions[attempt_id]


OracleIsolation = OracleLeakDetector
