"""
Instrument packages. Each subpackage holds detector YAML configs and must define:

- `TIMESTAMP_HDRKEY`: header keyword holding the exposure time.
- `TIMESTAMP_FORMAT`: astropy.time.Time format of that value, e.g. 'mjd' or 'isot'.

It may also define:

- `DEFAULT_CONFIG`: name of the default detector YAML config.
- `load_image`: custom file loader for ImageCreator.
- `identify_image`: custom image-type identifier for ImageCreator.

The ImageCreator itself is built in `walkman.backend`.
"""
from pathlib import Path
from types import ModuleType
from typing import Optional
import importlib

INSTRUMENT_ENV_VAR = "WALKMAN_INSTRUMENT"
CONFIG_ENV_VAR = "WALKMAN_CONFIG"
OUTPUT_ENV_VAR = "WALKMAN_OUTPUT"


def load_instrument(instrument: str) -> ModuleType:
    """
    Import an instrument package.

    :param instrument: Name of the instrument package (case sensitive), e.g. 'KPF'.
    :return: The imported instrument module.
    """
    return importlib.import_module(f"{__name__}.{instrument}")


def resolve_config(instrument_module: ModuleType, config: Optional[str] = None) -> Path:
    """
    Resolve the detector config path inside an instrument package.

    :param instrument_module: Imported instrument module.
    :param config: Name of the detector YAML config. Defaults to the module's DEFAULT_CONFIG.
    :return: Absolute path to the detector config.
    """
    config = config or getattr(instrument_module, "DEFAULT_CONFIG", None)
    if config is None:
        raise ValueError(f"No detector config name provided and '{instrument_module.__name__}' "
                         f"defines no DEFAULT_CONFIG.")
    config_path = (Path(instrument_module.__file__).parent / config).resolve()
    if not config_path.exists():
        raise ValueError(f"Detector config not found at '{config_path}'.")
    return config_path
