"""
DEIMOS: 8 science CCDs with 2 outputs each, one FITS file per CCD.

Detector configs: `deimos_long_oscan.yaml` (200-pixel serial overscan) and `deimos_sci.yaml` (20-pixel serial
overscan). Images are loaded with eregion's `load_image_fits_DEIMOS`, and image types are identified from the file
name with `guess_image_type_from_filename_DEIMOS`.
"""
from eregion.tasks.custom import (load_image_fits_DEIMOS as load_image,
                                  guess_image_type_from_filename_DEIMOS as identify_image)

#: Detector config used when `walkman start DEIMOS` is given no `--config`.
DEFAULT_CONFIG = "deimos_long_oscan.yaml"
#: Header keyword holding the exposure time.
TIMESTAMP_HDRKEY = "TIMEUTC"
#: astropy.time.Time format of the exposure time.
TIMESTAMP_FORMAT = "isot"
