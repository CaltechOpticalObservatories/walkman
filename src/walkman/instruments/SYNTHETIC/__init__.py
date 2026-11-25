"""
SYNTHETIC: 5 single-output detectors of pure Gaussian white noise, one FITS file per detector, each with a different
known noise level. Used to show that the PSD base level of white noise is 2σ². A second image set adds a sine of a
different amplitude per detector, to show how a sine's amplitude maps to the height and area of its PSD spike.

Detector configs: `synthetic.yaml`. Generate the images with `python -m walkman.instruments.SYNTHETIC.make_data`
(white noise, into `data/synthetic`) or with `--sine` (white noise + sine, into `data/synthetic_sine`).
Images are loaded with eregion's default FITS loader and header-based image-type identifier.
"""

#: Detector config used when `walkman start SYNTHETIC` is given no `--config`.
DEFAULT_CONFIG = "synthetic.yaml"
#: Header keyword holding the exposure time.
TIMESTAMP_HDRKEY = "MJD-OBS"
#: astropy.time.Time format of the exposure time.
TIMESTAMP_FORMAT = "mjd"
