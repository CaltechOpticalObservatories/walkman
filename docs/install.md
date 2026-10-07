# How To Install

walkman is installed from source into a Python virtual environment. Installing it also installs the `walkman` command
and all of its dependencies, including the `eregion` detector characterization framework.

## Requirements

- **Python 3.12 or 3.13.** Check with `python3 --version`.
- **git**, and network access to GitHub. `eregion` is installed directly from its GitHub repository
  ([CaltechOpticalObservatories/eregion](https://github.com/CaltechOpticalObservatories/eregion), branch `kpf-config`).
- **A web browser** on the machine where you will look at the dashboard.

## Install

1. Get the source code:

   ```bash
   git clone git@github.com:CaltechOpticalObservatories/walkman.git
   cd walkman
   ```

   If you have no SSH key set up on GitHub, clone over HTTPS instead:
   `git clone https://github.com/CaltechOpticalObservatories/walkman.git`.

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   In a new terminal, either activate it again (`source .venv/bin/activate`) before using walkman, or set up the
   `walkman` command once so it works without activating, see
   [Use walkman without activating the environment](#use-walkman-without-activating-the-environment).

3. Install walkman:

   ```bash
   pip install -e .
   ```

4. Check that it worked:

   ```bash
   walkman --help
   ```

   This lists the `start` and `stop` commands. You can now [start a dashboard](usage.md).

## Use walkman without activating the environment

The `walkman` command installed in `.venv/bin` always runs with the environment's own Python, and so does the
dashboard it starts, whether or not the environment is active. Activating only puts `.venv/bin` on your `PATH` so the
shell can find the command. To run `walkman` from any terminal and any folder without activating, link the command
into a folder that is on your `PATH`. From the `walkman` folder:

```bash
mkdir -p ~/.local/bin
ln -s "$PWD/.venv/bin/walkman" ~/.local/bin/walkman
```

If `~/.local/bin` is not on your `PATH` yet (`walkman: command not found` in a new terminal), add this line to your
shell's startup file (`~/.zshrc` for zsh, `~/.bashrc` for bash) and open a new terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The link points to the installed command, so it keeps working after `git pull` and after updating eregion. To
undo it, delete the link with `rm ~/.local/bin/walkman`.

## Optional extras

Extra dependencies are grouped so you only install what you need:

| Extra  | Install with                 | For                                         |
|--------|------------------------------|---------------------------------------------|
| `test` | `pip install -e '.[test]'`   | Running the test suite (`pytest`)           |
| `dev`  | `pip install -e '.[dev]'`    | Development tools (`black`, `flake8`, `tox`) |
| `docs` | `pip install -e '.[docs]'`   | Building this documentation                 |

Extras can be combined, for example `pip install -e '.[dev,test,docs]'`.

To build the documentation, run `tox -e docs` (needs the `dev` extra) or `make -C docs html` (needs the `docs` extra).
The pages are written to `docs/_build/html`.

## Updating

To update walkman itself, pull the latest code. Because it is installed with `-e`, no reinstall is needed:

```bash
git pull
```

If the new code needs new dependencies, also run `pip install -e .` again.

`eregion` is a separate package and is **not** updated by `git pull` or by `pip install -e .`. pip sees that
`eregion` is already installed and skips it, because the version number usually stays the same between commits.
To get the latest `eregion`, force a reinstall:

```bash
pip install --force-reinstall --no-deps \
    "eregion @ git+https://github.com/CaltechOpticalObservatories/eregion.git@kpf-config"
```

## Troubleshooting

**`ERROR: Package 'walkman' requires a different Python`**
: Your Python is older than 3.12 or newer than 3.13. Create the virtual environment with a supported version, for
  example `python3.12 -m venv .venv`.

**`walkman: command not found`**
: The virtual environment is not active in this terminal. Run `source .venv/bin/activate` from the `walkman` folder,
  or set up the command once as described in
  [Use walkman without activating the environment](#use-walkman-without-activating-the-environment).

**A change in eregion is not picked up**
: See [Updating](#updating). eregion has to be force-reinstalled.

**The browser does not open, or walkman runs on a remote machine**
: `walkman start` prints the dashboard's address in the terminal, a line like
  `http://localhost:8888/voila/render/basic.ipynb?token=...`. Open that address in a browser yourself. If walkman
  runs on a remote machine, forward the port over SSH from your own computer (use the port number from that
  address), then open the address locally:

  ```bash
  ssh -L 8888:localhost:8888 user@remote-machine
  ```
