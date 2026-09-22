"""Shared exceptions for repository-intelligence validation boundaries."""


class PilotError(ValueError):
    """Base error for rejected or internally inconsistent authority records."""


class ValidationError(PilotError):
    """A trust-bearing input failed closed validation."""


class DuplicateAttemptError(PilotError):
    """An allocation would duplicate an existing non-rerun attempt."""


class ReceiptVerificationError(PilotError):
    """A conformance receipt is malformed, inconsistent, or tampered with."""
