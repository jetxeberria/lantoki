"""Tests for the `cli` module."""

from typer.testing import CliRunner
from lantoki.cli import app

runner = CliRunner()


def test_info():
    """Test the CLI"""
    result = runner.invoke(app, [])
    expected = "This is the lantoki CLI"

    assert result.exit_code == 0
    assert expected in result.stdout
