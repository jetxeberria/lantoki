"""Module that contains the command line application."""

import typer
from rich import print as rich_print


app = typer.Typer()


@app.command()
def info() -> None:
    """Show that the CLI is working."""
    rich_print("This is the lantoki CLI")
    rich_print()


if __name__ == "__main__":
    app()
