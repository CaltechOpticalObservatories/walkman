"""
Base walkman commands.

- `walkman start`: Start the walkman dashboard for a given isntrument package.
- `walkman stop`: Shut down Jupyter servers started by `walkman start` and remove their session directories.
"""

from importlib.resources import files
from pathlib import Path
from typing import Optional
import os
import shutil
import subprocess
import sys
import tempfile

from jupyter_server.serverapp import list_running_servers, shutdown_server
import typer

from walkman.instruments import CONFIG_ENV_VAR, INSTRUMENT_ENV_VAR, load_instrument, resolve_config

# Session directories are created in the system temp dir as f"{SESSION_PREFIX}{instrument}_<random>"
SESSION_PREFIX = "walkman_"


def _session_prefix(instrument: Optional[str]) -> str:
    return f"{SESSION_PREFIX}{instrument}_" if instrument else SESSION_PREFIX


def _is_session_dir(path: Path, prefix: str) -> bool:
    return path.parent == Path(tempfile.gettempdir()).resolve() and path.name.startswith(prefix)


def start(
    instrument: str = typer.Argument(
        ..., help="Name of the instrument package (case sensitive) to start the walkman dashboard for.",
    ),
    notebook: str = typer.Option(
        "basic.ipynb", "--notebook", "-n", help="Name of the dashboard notebook, should be present in walkman/notebooks.",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c",
        help="Name of the detector YAML config, should be present in the instrument package.",
    ),
):
    """
    Start the walkman dashboard for a given instrument package.
    """
    # Validate the instrument and config here, so errors show in the terminal rather than the notebook
    try:
        instrument_module = load_instrument(instrument)
    except ImportError as e:
        typer.secho(f"Error importing instrument package: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    try:
        config_path = resolve_config(instrument_module, config)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    template = files("walkman.notebooks").joinpath(notebook)
    if not template.is_file():
        typer.secho(f"Dashboard notebook '{notebook}' not found in walkman/notebooks.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Copy the template notebook into a fresh session directory, so the packaged template is never modified
    session_dir = Path(tempfile.mkdtemp(prefix=_session_prefix(instrument)))
    with template.open("rb") as src, open(session_dir / notebook, "wb") as dst:
        shutil.copyfileobj(src, dst)
    typer.secho(f"Session directory: {session_dir}", fg=typer.colors.GREEN)

    # Launch Jupyter from the session directory, the kernel inherits the env vars from the server
    env = {**os.environ, INSTRUMENT_ENV_VAR: instrument, CONFIG_ENV_VAR: str(config_path)}
    result = subprocess.run([sys.executable, "-m", "notebook", notebook], cwd=session_dir, env=env)
    raise typer.Exit(result.returncode)


def stop(
    instrument: Optional[str] = typer.Argument(
        None, help="Only stop sessions of this instrument package (case sensitive). Stops all sessions if omitted.",
    ),
    keep_sessions: bool = typer.Option(
        False, "--keep-sessions", "-k", help="Keep session directories (notebook copies) after shutting down.",
    ),
):
    """
    Shut down walkman notebook servers and clean up their session directories.
    """
    prefix = _session_prefix(instrument)

    # Only touch servers whose root dir is a walkman session dir, other Jupyter servers are left alone
    busy_dirs = set()
    stopped = 0
    for server_info in list_running_servers():
        root_dir = Path(server_info["root_dir"]).resolve()
        if not _is_session_dir(root_dir, prefix):
            continue
        typer.echo(f"Stopping Jupyter server {server_info['url']} (pid {server_info['pid']}) for {root_dir.name}")
        if shutdown_server(server_info):
            stopped += 1
        else:
            typer.secho(f"Failed to stop server with pid {server_info['pid']}.", fg=typer.colors.RED, err=True)
            busy_dirs.add(root_dir)
    typer.secho(f"Stopped {stopped} walkman server(s).", fg=typer.colors.GREEN)

    if keep_sessions:
        return

    # Remove session dirs, including stale ones left behind by servers that were closed another way
    removed = 0
    for session_dir in Path(tempfile.gettempdir()).resolve().glob(f"{prefix}*"):
        if session_dir.is_dir() and session_dir not in busy_dirs:
            shutil.rmtree(session_dir)
            removed += 1
    typer.secho(f"Removed {removed} session director{'y' if removed == 1 else 'ies'}.", fg=typer.colors.GREEN)
