"""Tests for the lantoki command line (CLI-1)."""

lazy from pathlib import Path

import pytest
from typer.testing import CliRunner

from lantoki.cli import app


runner = CliRunner()


def test_given_valid_sources_when_validating_then_summary_and_warnings_are_printed(acme_env: Path) -> None:
    del acme_env

    result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0, result.output
    assert "valid: 12 sources, 1 providers" in result.output
    assert "does not support prompt at project scope" in result.output


def test_given_invalid_source_when_validating_then_exit_code_is_two(acme_env: Path, sources_root: Path) -> None:
    del acme_env
    (sources_root / "user" / "agents" / "broken.md").write_text("---\ntools: [x]\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["validate"])

    assert result.exit_code == 2
    assert "broken.md" in result.output


def test_given_profiles_when_listing_providers_then_each_is_shown_with_its_kinds(acme_env: Path) -> None:
    del acme_env

    result = runner.invoke(app, ["providers"])

    assert result.exit_code == 0, result.output
    assert "Acme Assistant" in result.output
    assert "0.0.0" in result.output


def test_given_empty_home_when_planning_user_then_creations_are_listed_without_writing(acme_env: Path) -> None:
    result = runner.invoke(app, ["plan", "user"])

    assert result.exit_code == 0, result.output
    assert "create" in result.output
    assert not (acme_env / ".acme").exists()


def test_given_empty_home_when_syncing_user_twice_then_second_run_reports_unchanged(acme_env: Path) -> None:
    runner.invoke(app, ["sync", "user"])

    result = runner.invoke(app, ["sync", "user", "--verbose"])

    assert result.exit_code == 0, result.output
    assert "unchanged" in result.output
    assert (acme_env / ".acme" / "rules" / "general.md").is_symlink()


def test_given_conflicting_file_when_syncing_user_then_exit_code_is_one(acme_env: Path) -> None:
    rule = acme_env / ".acme" / "rules" / "general.md"
    rule.parent.mkdir(parents=True)
    rule.write_text("mine", encoding="utf-8")

    result = runner.invoke(app, ["sync", "user"])

    assert result.exit_code == 1
    assert "conflict" in result.output


@pytest.mark.parametrize(
    ("args", "expected_exit", "expected_text"),
    [
        (["--all"], 0, "create"),
        ([], 0, "new project sources not applied"),
        (["--all", "--select"], 2, "mutually exclusive"),
    ],
)
def test_given_repo_when_syncing_with_selection_options_then_outcome_matches(
    acme_env: Path,
    repo: Path,
    args: list[str],
    expected_exit: int,
    expected_text: str,
) -> None:
    del acme_env

    result = runner.invoke(app, ["sync", "repo", str(repo), *args])

    assert result.exit_code == expected_exit, result.output
    assert expected_text in result.output


def test_given_repo_when_planning_with_all_then_nothing_is_written(acme_env: Path, repo: Path) -> None:
    del acme_env

    result = runner.invoke(app, ["plan", "repo", str(repo), "--all"])

    assert result.exit_code == 0, result.output
    assert not (repo / ".acme").exists()


def test_given_unknown_provider_when_running_then_exit_code_is_two(acme_env: Path) -> None:
    del acme_env

    result = runner.invoke(app, ["plan", "user", "--provider", "nope"])

    assert result.exit_code == 2
    assert "Enabled providers without a profile" in result.output
