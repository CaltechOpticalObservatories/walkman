# Walkman

A generic tool for identification and analysis of electronic noise sources in astronomical detectors. 
Built upon the detector characterization framework `eregion`.

## Key Features

- Image loading and processing orchestrated using the Eregion framework which supports multiple detector types.
- Jupyter notebook interface powered by `ipywidgets` for interactive exploration of live data.

## Getting started

```bash
git clone git@github.com:CaltechOpticalObservatories/walkman.git
cd walkman
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
walkman start KPF
```

- [How To Install](install.md): requirements, optional extras, updating, and troubleshooting.
- [How To Use](usage.md): starting the dashboard, running an analysis, reading the plots, and the saved results.

```{toctree}
:hidden:
:maxdepth: 2

install
usage
design/index
api/index
```
