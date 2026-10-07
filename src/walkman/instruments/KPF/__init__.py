"""
Keck Planet Finder (KPF): green and red science CCDs with 2 outputs each, and the Ca H&K CCD with 1 output, all
read from one FITS file per exposure.

Detector configs: `kpf.yaml`. Images are loaded with eregion's `load_image_fits_KPF`.
"""
from eregion.tasks.custom import load_image_fits_KPF as load_image

#: Detector config used when `walkman start KPF` is given no `--config`.
DEFAULT_CONFIG = "kpf.yaml"
#: Header keyword holding the exposure time.
TIMESTAMP_HDRKEY = "MJD-OBS"
#: astropy.time.Time format of the exposure time.
TIMESTAMP_FORMAT = "mjd"
