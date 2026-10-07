# How To Use

walkman measures the electronic noise in detector images and shows it in a dashboard in your web browser. For every
detector output it reports the noise level, a power spectral density (PSD) to reveal periodic noise, the noise over
time, and a histogram of pixel values. Every result is also saved to disk.

This page assumes walkman is [installed](install.md) and its virtual environment is active.

## Start the dashboard

Start walkman with the name of your instrument:

```bash
walkman start KPF
```

This opens the dashboard in your browser. Keep the terminal open while you work: the dashboard runs as long as the
`walkman start` command is running.

Instrument names are case-sensitive. The instruments available now are:

| Instrument | Detector configs | Default |
|------------|------------------|---------|
| `KPF`      | `kpf.yaml`: green and red CCDs with 2 outputs each, Ca H&K CCD with 1 output | `kpf.yaml` |
| `DEIMOS`   | 8 CCDs with 2 outputs each, one FITS file per CCD. `deimos_long_oscan.yaml`: 200-pixel serial overscan. `deimos_sci.yaml`: 20-pixel serial overscan. | `deimos_long_oscan.yaml` |

`walkman start` options:

| Option            | Meaning                                                                                       |
|-------------------|-----------------------------------------------------------------------------------------------|
| `-c`, `--config`  | Detector config to use instead of the instrument's default, e.g. `-c deimos_sci.yaml`.        |
| `-o`, `--output`  | Folder the dashboard's **Output folder** field starts with. Default `~/walkman_results/<instrument>`. |
| `-n`, `--notebook`| Dashboard to open. Default `basic.ipynb`, the dashboard described on this page.               |

For example, to analyze DEIMOS science-array data and keep the results on a data disk:

```bash
walkman start DEIMOS -c deimos_sci.yaml -o /data/noise_results
```

If the browser does not open by itself, copy the address that `walkman start` prints in the terminal into your
browser. See [How To Install](install.md#troubleshooting) for using walkman on a remote machine.

## Analyze images

When the dashboard opens, it shows the analysis settings. Click any screenshot on this page to see it at full size.

```{image} _static/screenshots/dashboard-inputs.png
:target: _static/screenshots/dashboard-inputs.png
:alt: The dashboard's input fields, with Run, Stop and Reset seen files buttons
```

1. In **Data folder(s)**, enter the folder that holds your FITS files.
2. Check the **Output folder** and the **Regions** to analyze.
3. Click **Run**.

walkman processes the images one at a time. The plots appear after the first image and update after every image
after that. The status line below the buttons shows how many images are done and where the results are saved.

### Settings

| Field                      | Meaning |
|----------------------------|---------|
| **Data folder(s)**         | Where to find the images. Enter an absolute path to a folder, a single FITS file, or a glob pattern such as `/data/2026-09-22/*bias*.fits`. Put several on separate lines. Folders are searched for `*.fits*` files, including in subfolders. Archives (for example `.tar.gz`) are unpacked next to the archive and searched too. |
| **Output folder**          | Absolute path of the folder the results are saved in. Every Run creates a new subfolder here, see [Saved results](#saved-results). |
| **Watch mode**             | Keep watching the data folders and analyze new files as they arrive, see [Watch for new images](#watch-for-new-images). |
| **Poll interval (s)**      | Watch mode only. Seconds between checks for new files. |
| **Settle time (s)**        | Watch mode only. A new file is only analyzed once it has not changed for this many seconds, so files that are still being written are not read half-finished. |
| **Regions**                | Which part of each output to analyze. **overscan** is the serial overscan (CCDs only), **image** is the light-sensitive area without the prescan and overscan, and **full** is everything the output read out. Select one or more. |
| **Trim start**, **Trim end** | Number of pixels to leave out at the start and at the end of each region, along both axes. Use this to skip edge columns and rows. |
| **Target shape (0 = auto)** | Size of the segments the PSD is computed on. `0` picks it automatically (512, or less for small images). Larger values give finer frequency resolution but a noisier PSD. |
| **Window function**        | Window applied to each PSD segment. Any name accepted by `scipy.signal.get_window`, for example `hamming`, `hann` or `boxcar`. |

### Buttons

- **Run** starts the analysis. It is greyed out while a run is in progress.
- **Stop** ends the current run after the image being processed. In watch mode it stops right away if walkman is
  waiting for new files.
- **Reset seen files** makes watch mode forget which files it has already analyzed, see
  [Watch for new images](#watch-for-new-images).

Each **Run** clears the plots and starts from scratch. Earlier runs stay saved on disk.

## Read the results

This is the dashboard after analyzing the overscan of one KPF image:

```{image} _static/screenshots/dashboard-results-overview.png
:target: _static/screenshots/dashboard-results-overview.png
:alt: The complete dashboard after a run, with the noise table, PSD, noise trend and histograms
```

Every combination of detector, output and region gets its own color. The color stays the same in all plots and for
the whole run.

### Noise and PSD

```{image} _static/screenshots/dashboard-noise-table-psd.png
:target: _static/screenshots/dashboard-noise-table-psd.png
:alt: Noise table with one row per detector output, next to the PSD plot
```

The **noise table** has one row per detector, output and region. **Noise** is the standard deviation of the pixel
values in that region, in the same units as the image (ADU for raw frames). It shows the value from the most recent
image.

The **PSD** plot shows how the noise power is spread over frequency, from 0 to 0.5 cycles/pixel, for the most recent
image. Purely random (white) noise gives a flat PSD. Peaks point to periodic noise, such as electrical pickup: a peak
at frequency *f* is a pattern that repeats every 1/*f* pixels.

Untick the checkbox in the **PSD** column to hide that row from the PSD and noise trend plots. This makes it easier
to compare a few outputs at a time.

### Noise over time

```{image} _static/screenshots/dashboard-noise-trend.png
:target: _static/screenshots/dashboard-noise-trend.png
:alt: Noise trend plot with one point per output for each image
```

The **noise trend** plots the noise of every image analyzed in this run against the time the image was taken, as a
Modified Julian Date (MJD). Use it to spot noise that drifts or jumps over a night. With a single image, as above,
each output has one point.

The time comes from the image header. Which header keyword is used depends on the instrument (`MJD-OBS` for KPF,
`TIMEUTC` for DEIMOS) and is shown in the axis label. If an image does not have that keyword, walkman uses the
file's time on disk instead. That is close to the exposure time only for files analyzed as they are written, not for
files that were copied later.

### Histograms

```{image} _static/screenshots/dashboard-histograms.png
:target: _static/screenshots/dashboard-histograms.png
:alt: Grid of pixel value histograms, one per detector output
```

The **histograms** show the distribution of pixel values for each detector, output and region of the most recent
image, with counts on a log scale. Clean read noise gives a single symmetric peak. Look for extra peaks, tails or
gaps.

### Working with the plots

Hover over a plot to show its toolbar, with tools to pan, zoom and save the plot as a PNG. Drag the triangle in the
bottom-right corner of a plot to resize it.

## Watch for new images

To monitor data while it is being taken, tick **Watch mode** and click **Run**. walkman first analyzes the files
already in the data folders, then checks for new files every **Poll interval** seconds and analyzes each one when it
arrives. The status line shows `Watching every 5.0 s...` while it waits. Click **Stop** to end watching.

walkman remembers which files watch mode has already analyzed for as long as the dashboard is open. If you stop and
start watching the same folder again, only files that arrived in between are analyzed. Click **Reset seen files** to
analyze everything again on the next watch run.

A run without watch mode always analyzes every file it finds, whether or not watch mode has seen it before.

## Saved results

Every run creates a new folder inside the **Output folder**, named after the time the run started. Inside it there is
one folder per image file:

```text
~/walkman_results/KPF/
└── 20261007-134901/                     one folder per run
    ├── run_config.json                  the settings used for this run
    └── KP.20250219.59086.42/            one folder per image file
        ├── noise_results.fits           the results
        └── NoiseResult_metadata.json
```

Each image's results are saved as soon as it is analyzed, so stopping a run or closing the dashboard loses nothing
that was already processed.

To work with a run's results in Python, load the run folder:

```python
from walkman.noise import NoiseResult

result = NoiseResult.load_run("/home/observer/walkman_results/KPF/20261007-134901")
df = result.data  # a pandas DataFrame with one row per image, detector, output and region
print(df[["det_id", "output", "region", "noise", "time"]])
```

The table has these columns:

| Column                     | Content |
|----------------------------|---------|
| `det_id`, `output`, `region` | Which detector, output and region the row is for. |
| `noise`                    | Standard deviation of the pixel values. |
| `mean`, `median`, `mad`    | Mean, median and median absolute deviation of the pixel values. |
| `time`                     | Time of the image in MJD. |
| `filename`                 | The image file. |
| `psd`                      | `(frequencies, power)` arrays of the PSD. |
| `histogram`                | `(bin_edges, counts)` arrays of the histogram. |

To load a single image's results instead, use `NoiseResult.load` with that image's folder.

## Close the dashboard

Closing the browser tab does not stop walkman. To shut it down, either press `Ctrl+C` twice in the terminal where
`walkman start` is running, or run this from any terminal:

```bash
walkman stop
```

`walkman stop` shuts down all running walkman dashboards. Give an instrument name, for example `walkman stop KPF`,
to stop only that instrument's dashboards. Your saved results are not affected.
