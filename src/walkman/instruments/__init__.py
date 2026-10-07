"""
Instrument packages. Each subpackage holds detector YAML configs and may define:

- `DEFAULT_CONFIG`: name of the default detector YAML config.
- `load_image`: custom file loader for ImageCreator.
- `identify_image`: custom image-type identifier for ImageCreator.
"""
from pathlib import Path
from types import ModuleType
from typing import Optional
import importlib

from eregion.tasks.imagegen import ImageCreator

INSTRUMENT_ENV_VAR = "WALKMAN_INSTRUMENT"
CONFIG_ENV_VAR = "WALKMAN_CONFIG"


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


def build_image_creator(instrument_module: ModuleType, config_path: str | Path, **kwargs) -> ImageCreator:
    """
    Instantiate an ImageCreator with the instrument's custom file loader and identifier, if defined.

    :param instrument_module: Imported instrument module.
    :param config_path: Path to the detector config.
    :param kwargs: Extra keyword arguments for ImageCreator.
    :return: Configured ImageCreator.
    """
    creator = ImageCreator(detector_config=str(config_path), **kwargs)
    custom_loader = getattr(instrument_module, "load_image", None)
    custom_identifier = getattr(instrument_module, "identify_image", None)
    if custom_loader:
        creator.set_fileloader(custom_loader)
    if custom_identifier:
        creator.set_identifier(custom_identifier)
    return creator
