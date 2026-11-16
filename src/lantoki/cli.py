"""lantoki command line (CLI-1)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lantoki.app import Outcome, Selection, Workspace, run_scope
from lantoki.config import load_settings
from lantoki.exceptions import LantokiError
from lantoki.installer import Action
from lantoki.sources import Kind, Scope, Source


app = typer.Typer(help="Compile lantoki customizations into every AI harness.", no_args_is_help=True)
plan_app = typer.Typer(help="Show what sync would change, without changing anything (INS-8).", no_args_is_help=True)
sync_app = typer.Typer(help="Install customizations for every enabled provider.", no_args_is_help=True)
app.add_typer(plan_app, name="plan")
app.add_typer(sync_app, name="sync")

console = Console()

ProvidersOption = Annotated[
    list[str] | None,
    typer.Option("--provider", "-p", help="Only these provider ids (repeatable). Default: all enabled."),
]
RepoArgument = Annotated[Path, typer.Argument(exists=True, file_okay=False, resolve_path=True, help="Repository path")]
AllOption = Annotated[bool, typer.Option("--all", help="Apply every project source to the repository.")]
SelectOption = Annotated[bool, typer.Option("--select", help="Ask again for every project source.")]
AdoptOption = Annotated[
    bool,
    typer.Option("--adopt-commands", help="Replace existing CLI registrations with the same name (INS-6)."),
]

_STYLES = {
    Action.CREATE: "green",
    Action.UPDATE: "yellow",
    Action.ADOPT: "cyan",
    Action.UNCHANGED: "dim",
    Action.PRUNE: "magenta",
    Action.CONFLICT: "bold red",
    Action.SKIP: "red",
}


def _workspace(providers: list[str] | None) -> Workspace:
    try:
        return Workspace.load(load_settings(), tuple(providers or ()))
    except LantokiError as error:
        console.print(f"[bold red]{error.message}[/]")
        raise typer.Exit(code=2) from error


def _selection(*, select_all: bool, select: bool) -> Selection:
    if select_all and select:
        console.print("[bold red]--all and --select are mutually exclusive[/]")
        raise typer.Exit(code=2)
    if select_all:
        return Selection.ALL
    return Selection.ASK if select else Selection.REMEMBERED


def _ask(source: Source) -> bool:
    return typer.confirm(f"Apply {source.kind} '{source.name}' to this repository?", default=False)


def _print(outcome: Outcome, *, verbose: bool) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("action")
    table.add_column("target", overflow="fold")
    table.add_column("detail", overflow="fold")
    for step in outcome.plan.steps:
        if step.action is Action.UNCHANGED and not verbose:
            continue
        table.add_row(
            f"[{_STYLES[step.action]}]{step.action}[/]", step.target.replace(str(Path.home()), "~"), step.detail
        )
    if table.row_count:
        console.print(table)
    summary = ", ".join(f"{outcome.plan.count(action)} {action}" for action in Action if outcome.plan.count(action))
    console.print(summary or "nothing to do")
    for warning in outcome.warnings:
        console.print(f"[yellow]warning:[/] {warning}")
    if outcome.skipped_new_sources:
        console.print(f"[yellow]new project sources not applied (no terminal to ask):[/] {outcome.skipped_new_sources}")
    if outcome.report is not None:
        for step, error in outcome.report.failed:
            console.print(f"[bold red]failed[/] {step.target}: {error}")


def _finish(outcome: Outcome, *, verbose: bool) -> None:
    _print(outcome, verbose=verbose)
    if not outcome.ok:
        raise typer.Exit(code=1)


Verbose = Annotated[bool, typer.Option("--verbose", "-v", help="Also list unchanged targets.")]


@app.command()
def validate(providers: ProvidersOption = None) -> None:
    """Validate every source and provider profile and compile both scopes (CMP-3)."""
    workspace = _workspace(providers)
    try:
        user = workspace.compile(Scope.USER)
        project = workspace.compile(Scope.PROJECT, Path("/validate/repo"))
    except LantokiError as error:
        console.print(f"[bold red]{error.message}[/]")
        raise typer.Exit(code=2) from error
    for warning in user.warnings + project.warnings:
        console.print(f"[yellow]warning:[/] {warning}")
    console.print(
        f"[green]valid:[/] {len(workspace.sources)} sources, {len(workspace.profiles)} providers, "
        f"{len(user.artifacts)} user and {len(project.artifacts)} project artifacts",
    )


@app.command()
def providers(providers: ProvidersOption = None) -> None:
    """List enabled providers and which kinds each supports per scope."""
    workspace = _workspace(providers)
    table = Table("provider", "verified", *[f"{scope}" for scope in Scope])
    for profile in workspace.profiles:
        per_scope = [
            ", ".join(sorted({str(output.kind) for output in profile.outputs_for(scope)})) or "-" for scope in Scope
        ]
        table.add_row(
            f"{profile.provider.name} ({profile.id})",
            f"{profile.provider.verified_with} on {profile.provider.verified_on}",
            *per_scope,
        )
    console.print(table)
    console.print(f"kinds: {', '.join(str(kind) for kind in Kind)}")


@plan_app.command("user")
def plan_user(providers: ProvidersOption = None, verbose: Verbose = False) -> None:  # noqa: FBT002
    """Show what `sync user` would change."""
    _finish(run_scope(_workspace(providers), Scope.USER), verbose=verbose)


@plan_app.command("repo")
def plan_repo(
    repo: RepoArgument,
    providers: ProvidersOption = None,
    select_all: AllOption = False,  # noqa: FBT002
    verbose: Verbose = False,  # noqa: FBT002
) -> None:
    """Show what `sync repo` would change."""
    selection = Selection.ALL if select_all else Selection.REMEMBERED
    _finish(run_scope(_workspace(providers), Scope.PROJECT, repo, selection=selection), verbose=verbose)


@sync_app.command("user")
def sync_user(
    providers: ProvidersOption = None,
    adopt_commands: AdoptOption = False,  # noqa: FBT002
    verbose: Verbose = False,  # noqa: FBT002
) -> None:
    """Install user-level customizations for every enabled provider."""
    outcome = run_scope(_workspace(providers), Scope.USER, apply=True, adopt_commands=adopt_commands)
    _finish(outcome, verbose=verbose)


@sync_app.command("repo")
def sync_repo(  # noqa: PLR0917 - typer maps each parameter to a CLI option
    repo: RepoArgument,
    providers: ProvidersOption = None,
    select_all: AllOption = False,  # noqa: FBT002
    select: SelectOption = False,  # noqa: FBT002
    adopt_commands: AdoptOption = False,  # noqa: FBT002
    verbose: Verbose = False,  # noqa: FBT002
) -> None:
    """Install project-level customizations into a repository."""
    outcome = run_scope(
        _workspace(providers),
        Scope.PROJECT,
        repo,
        selection=_selection(select_all=select_all, select=select),
        ask=_ask if sys.stdin.isatty() else None,
        apply=True,
        adopt_commands=adopt_commands,
    )
    _finish(outcome, verbose=verbose)


if __name__ == "__main__":
    app()
