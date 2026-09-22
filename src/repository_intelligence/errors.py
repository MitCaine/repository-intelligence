"""Shared exceptions for repository-intelligence validation boundaries."""


class PilotError(ValueError):
    """Base error for rejected or internally inconsistent authority records."""


class ValidationError(PilotError):
    """A trust-bearing input failed closed validation."""
