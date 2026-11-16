"""lantoki's exception hierarchy.

Every error lantoki raises derives from :class:`LantokiError`, which logs itself with
structured context when created, so failures are traceable even when callers only
report the message.
"""

from __future__ import annotations

import structlog


LOGGER = structlog.get_logger(__name__)


class LantokiError(Exception):
    """Base class for lantoki errors; logs a structured event when instantiated."""

    event = "lantoki_error"

    def __init__(self, message: str, **context: object) -> None:
        """Store the message and context and log them as a structured error event."""
        super().__init__(message)
        self.message = message
        self.context = context
        LOGGER.error(self.event, message=message, **context)


class ConfigError(LantokiError):
    """Application settings are missing or invalid."""

    event = "config_error"


class SourceError(LantokiError):
    """A customization source does not follow the neutral format (SRC-*)."""

    event = "source_error"


class ProfileError(LantokiError):
    """A provider profile is missing, unreadable or does not match the profile schema (PRF-*)."""

    event = "profile_error"


class CompileError(LantokiError):
    """Sources and profiles cannot be compiled into consistent artifacts (CMP-*)."""

    event = "compile_error"


class InstallError(LantokiError):
    """Installing or pruning artifacts failed (INS-*)."""

    event = "install_error"
