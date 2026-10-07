# Design

This page describes how walkman is put together and why, for developers working on it. For using walkman, see
[How To Use](../usage.md).

## Goals

walkman is first of all a **live monitoring tool**: while a detector is taking data, it should show the noise of
every output within seconds of each new image, and keep doing so through a session without supervision. Analyzing
existing data sets uses the same path, with watch mode off.

This leads to the main requirements:

- Low latency per image: results appear one image at a time, not after a whole batch.
- Robust over long runs: no growing per-image cost, nothing lost if the dashboard is stopped or crashes.
- One code path for any detector: instrument differences live in configuration, not in the analysis code.
- A browser UI that needs no web development to change.

## Architecture

```text
walkman start <INSTRUMENT>     [cli/commands/base.py]
  │ checks instrument and config,
  │ copies the notebook to a session folder,
  │ sets WALKMAN_* env vars
  ▼
Jupyter server + Voilà
  │ browser opens /voila/render/<notebook>
  ▼
Dashboard notebook, UI only    [notebooks/, plots.py]
  │ widgets, background thread,
  │ plots updated in place
  ▼
NoiseAnalysis                  [backend.py]
  │ owns ImageCreator + NoisePSD,
  │ saves and accumulates results
  ▼
eregion
  │ ImageCreator.lazy_run → DetImages
  │ NoisePSD (noise.py)   → NoiseResult
  ▼
<output>/<run>/<image>/noise_results.fits
```

| Component | Responsibility                                                                                                                             |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `cli/` | `walkman start` and `walkman stop`. Validates input in the terminal, manages Jupyter servers and session folders. Holds no analysis logic. |
| `instruments/` | One subpackage per instrument: detector YAML configs and instrument-specific hooks. Discovered by name with `importlib`.                   |
| `backend.py` | The only place eregion pipelines are executed. `NoiseAnalysis` turns settings into a stream of per-image results.                          |
| `noise.py` | The `NoisePSD` eregion task and its `NoiseResult`, including saving and loading, these will also be move to eregion in next update.        |
| `plots.py` | ipympl figures for the dashboard, updated in place.                                                                                        |
| `notebooks/` | Dashboard templates. UI only: they call the backend and render what it yields.                                                             |

## Design decisions

### The dashboard is a notebook rendered by Voilà

Dashboards are Jupyter notebooks built from `ipywidgets` and `ipympl`, rendered with Voilà, which runs every cell on
load and hides the code. Scientists can change a dashboard without any web development, and a new dashboard is just
another notebook (`walkman start -n`).

Voilà runs as an extension of a normal Jupyter server rather than as its own server. As a result,
`walkman stop` can find walkman's servers with `jupyter_server`'s `list_running_servers`, and the notebook editor
stays available at `/tree` for debugging.

`walkman start` copies the template into a fresh temporary session folder and starts the server there. The packaged
template is never modified, and `walkman stop` identifies walkman servers by their root folder (`walkman_<instrument>_*`
in the system temp folder), so other Jupyter servers are left alone.

Settings reach the notebook's kernel through environment variables (`WALKMAN_INSTRUMENT`, `WALKMAN_CONFIG`,
`WALKMAN_OUTPUT`) set on the server process, which kernels inherit. A notebook therefore cannot run standalone; it
raises an error that points to `walkman start`.

### UI and backend are separate

The notebook contains no eregion logic. It builds a `NoiseAnalysis` once and iterates over `analysis.run(...)`,
which yields one `NoiseResult` per image. Keeping execution in `backend.py` means the same analysis runs from a script
or a test without a browser, and dashboards stay small.

The run happens in a background thread so the kernel stays responsive for the Stop button and plot interaction.
Exceptions in that thread are shown in the dashboard's status line, since they would otherwise be lost.

### One image at a time, saved immediately

The `ImageCreator` is built with `max_batch_size=1`, so each `lazy_run` iteration holds the images from one file.
This bounds memory and gives the lowest latency per image, which matters more for live monitoring than batch
throughput.

Each image's `NoiseResult` is saved to its own folder as soon as it is computed, and `run_config.json` records the
settings of the run. Rewriting one growing file per run would make every save slower over a long night (each image
holds a few MB of histogram and PSD data). Per-image files keep the cost constant and lose nothing on a crash.
`NoiseResult.load_run` puts a run back together.

### Watch mode lives in eregion

Polling, stopping and file tracking use eregion's `ImageCreator` rather than a walkman loop:

- `watch_mode` and `poll_interval` control polling. `stop()` (from `LazyTask`) can be called from another thread and
  also wakes a waiting poll.
- `settle_time` skips files modified too recently, so files still being written are not read half-finished.
- Files are marked seen only after their images are built, so a stopped or failed run does not lose files.
- Seen files are remembered for the lifetime of the `ImageCreator`, by design. A dashboard keeps one creator, so
  restarting watch mode only picks up new files. `NoiseAnalysis.reset()` rebuilds the creator to forget them.

### Results are stored in FITS

A `NoiseResult` is a pandas DataFrame with one row per image, detector, output and region. It is saved as FITS to
match the rest of the detector data. Scalar columns go to the first table HDU through eregion's
`save_dataframe_to_fits`. The `psd` and `histogram` columns hold `(x, y)` array pairs whose lengths differ between
rows (histogram binning adapts to the data), so they are split into four variable-length array columns in a second
HDU named `ARRAYS`. `NoiseResult.load` rebuilds the pairs, so the in-memory format is the same before and after
saving.

### Timestamps are configured per instrument

Instruments record exposure time under different header keywords and formats, so each instrument package declares
`TIMESTAMP_HDRKEY` and `TIMESTAMP_FORMAT` (an `astropy.time.Time` format), and `NoisePSD` converts the value to MJD.
If an image lacks the keyword, the file's time on disk is used instead. For live monitoring that is within seconds of
the exposure, but for copied data it is the copy time.

### Plots are updated in place

Each plot class in `plots.py` owns one figure and updates its existing artists (`set_data`) instead of redrawing.
The widget identity stays the same across updates from the background thread, and redraws stay cheap as results
accumulate. Each series, keyed by `(det_id, output, region)`, gets a color from a fixed palette in order of first
appearance, so colors are stable through a run.

## Extending walkman

### Add an instrument

1. Create a subpackage `src/walkman/instruments/<NAME>/` with an `__init__.py`. The name is what users type in
   `walkman start <NAME>` and is case-sensitive.
2. Add one or more eregion detector YAML configs next to it. YAML files in instrument folders are shipped with the
   package through the `instruments/*/*.yaml` entry in `pyproject.toml`.
3. Define in `__init__.py`:

   | Name | Required | Meaning |
   |------|----------|---------|
   | `DEFAULT_CONFIG` | yes, unless users always pass `-c` | File name of the default detector config. |
   | `TIMESTAMP_HDRKEY` | yes | Header keyword holding the exposure time. |
   | `TIMESTAMP_FORMAT` | yes | `astropy.time.Time` format of that value, e.g. `mjd` or `isot`. |
   | `load_image` | no | Custom file loader for eregion's `ImageCreator`, if the default FITS loader does not fit. |
   | `identify_image` | no | Custom image type identifier for `ImageCreator`. |

   Custom loaders and identifiers usually live in `eregion.tasks.custom` and are imported here. See
   `instruments/KPF/__init__.py` and `instruments/DEIMOS/__init__.py`.

### Add a dashboard

Add a notebook to `src/walkman/notebooks/` (shipped through the `notebooks/*.ipynb` package data entry) and open it
with `walkman start <INSTRUMENT> -n <notebook>.ipynb`. Like `basic.ipynb`, it should read the `WALKMAN_*` environment
variables, create a `NoiseAnalysis`, run it in a background thread, and use the classes in `plots.py`, keeping eregion
logic out of the notebook.

### Add an analysis

New analyses follow the pattern of `noise.py`: an eregion `Task` whose `TaskResult` implements `save` and `load`. The
current `NoiseAnalysis` is specific to `NoisePSD`, so a new analysis gets its own backend class in `backend.py` that
reuses `build_image_creator` and yields one result per image, so dashboards consume it the same way.

## Testing

`tests/test_noise.py` checks the `NoiseResult` save and load round trip with synthetic data, including rows with
histograms of different lengths and loading a whole run with `load_run`. Run the tests with `pytest`.
