"""Tests for lantoki's exception hierarchy."""

import pytest
from structlog.testing import capture_logs

from lantoki.exceptions import (
    CompileError,
    ConfigError,
    InstallError,
    LantokiError,
    ProfileError,
    SourceError,
)


@pytest.mark.parametrize(
    ("error_class", "event"),
    [
        (LantokiError, "lantoki_error"),
        (ConfigError, "config_error"),
        (SourceError, "source_error"),
        (ProfileError, "profile_error"),
        (CompileError, "compile_error"),
        (InstallError, "install_error"),
    ],
)
def test_given_error_class_when_instantiated_then_it_is_a_lantoki_error_that_logs_itself(
    error_class: type[LantokiError],
    event: str,
) -> None:
    with capture_logs() as logs:
        error = error_class("something broke", path="/x")

    assert isinstance(error, LantokiError)
    assert str(error) == "something broke"
    assert error.context == {"path": "/x"}
    assert logs == [{"event": event, "message": "something broke", "path": "/x", "log_level": "error"}]
