# Walkman

A generic tool for identification and analysis of electronic noise sources in astronomical detectors. 
Built upon the detector characterization framework `eregion`.

## Key Features

- Image loading and processing orchestrated using the Eregion framework which supports multiple detector types.
- Jupyter notebook interface powered by `ipywidgets` for interactive exploration of live data.

## Installation

```bash
git clone git@github.com:CaltechOpticalObservatories/walkman.git
cd walkman
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install additional dependencies for testing and development:

```bash
pip install -e '.[dev,test]'
```

## Usage


```{toctree}
:hidden:
:maxdepth: 2

design/index
api/index
```
