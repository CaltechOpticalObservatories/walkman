"""
walkman CLI entry point.

Lets dashboards be started from the terminal.
"""
import typer

from walkman.cli.commands.base import start, stop

app = typer.Typer(
    name="walkman",
    help="Start and stop walkman dashboard notebooks from the terminal.",
    no_args_is_help=True,
    add_completion=False,
)

app.command("start")(start)
app.command("stop")(stop)


def main():
    app()


if __name__ == "__main__":
    main()
