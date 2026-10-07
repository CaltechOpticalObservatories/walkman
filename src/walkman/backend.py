"""
Backend for the walkman dashboards. All eregion pipeline execution happens here, dashboards only consume the results.
"""
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Literal, Optional
import json

from eregion.tasks.imagegen import ImageCreator

from walkman.noise import NoisePSD, NoiseResult


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


def _image_stem(filename: Optional[str], index: int) -> str:
    # e.g. 'KP.20250219.59086.42.fits.fz' -> 'KP.20250219.59086.42'
    return Path(filename).name.split(".fits")[0] if filename else f"image_{index:05d}"


def _new_run_dir(output_dir: Path) -> Path:
    # timestamped, with a numeric suffix if a run was already started within the same second
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("", *(f"_{n}" for n in range(1, 100))):
        run_dir = output_dir / f"{stamp}{suffix}"
        try:
            run_dir.mkdir()
            return run_dir
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not create a new run folder for {stamp} in '{output_dir}'.")


class NoiseAnalysis:
    """
    Runs NoisePSD on images from an instrument, one image at a time, saving each image's NoiseResult as it goes.

    The ImageCreator lives as long as this object (or until reset), so in watch mode files seen in earlier runs are
    not processed again.
    """
    def __init__(self, instrument_module: ModuleType, config_path: str | Path):
        """
        :param instrument_module: Imported instrument module.
        :param config_path: Path to the detector config.
        """
        self.instrument_module = instrument_module
        self.config_path = Path(config_path)
        self.task = NoisePSD(timestamp_key=self.instrument_module.TIMESTAMP_HDRKEY,
                             timestamp_format=self.instrument_module.TIMESTAMP_FORMAT)
        self.reset()
        self.result = NoiseResult.model_construct()  # accumulated over the current run
        self.run_dir: Optional[Path] = None

    def reset(self) -> None:
        """
        Rebuild the ImageCreator, which forgets the files seen in earlier watch mode runs.
        """
        self.creator = build_image_creator(self.instrument_module, self.config_path, max_batch_size=1)

    def stop(self) -> None:
        """
        Stop a running `run` after the current image. Safe to call from another thread.
        """
        self.creator.stop()

    def run(self,
            input_paths: str | list[str],
            output_dir: str | Path,
            regions: list[Literal["full", "image", "overscan"]],
            trim_start: int = 0,
            trim_end: int = 0,
            target_shape: Optional[int] = None,
            window_func: str | Callable = "hamming",
            watch: bool = False,
            poll_interval: float = 5.0,
            settle_time: float = 2.0) -> Iterator[NoiseResult]:
        """
        Analyze images one at a time. Each image's NoiseResult is saved to `<run_dir>/<image stem>/` and accumulated
        into `self.result` before it is yielded. `run_dir` is a new timestamped folder in `output_dir`.

        :param input_paths: FITS file, folder or glob pattern, or a list of them.
        :param output_dir: Folder in which the run folder is created.
        :param regions: Image regions to analyze.
        :param trim_start: Pixels trimmed from the start of each region axis.
        :param trim_end: Pixels trimmed from the end of each region axis.
        :param target_shape: Target shape of the raveled Welch PSD. None picks it automatically.
        :param window_func: Window function of the PSD.
        :param watch: Keep watching the inputs for new files until `stop` is called.
        :param poll_interval: Seconds between checks for new files in watch mode.
        :param settle_time: Seconds a file must be unmodified before it is processed in watch mode.
        :return: Generator of per-image NoiseResults.
        """
        self.creator.watch_mode = watch
        self.creator.poll_interval = poll_interval
        self.creator.settle_time = settle_time

        self.run_dir = _new_run_dir(Path(output_dir).expanduser().resolve())
        self.result = NoiseResult.model_construct()
        run_config = {
            "instrument": self.instrument_module.__name__.rsplit(".", 1)[-1],
            "config_path": str(self.config_path),
            "input_paths": input_paths,
            "regions": regions,
            "trim_start": trim_start,
            "trim_end": trim_end,
            "target_shape": target_shape,
            "window_func": window_func if isinstance(window_func, str) else repr(window_func),
            "watch": watch,
            "poll_interval": poll_interval,
            "settle_time": settle_time,
        }
        (self.run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2))

        # max_batch_size=1, so each ImageResult holds the images built from a single file
        for index, imres in enumerate(self.creator.lazy_run(input_source=input_paths)):
            bundle = imres.data
            if len(bundle) == 0:
                continue
            noiseres = self.task.run(bundle, regions=regions, trim_start=trim_start, trim_end=trim_end,
                                     target_shape=target_shape, window_func=window_func)
            if noiseres.data.empty:
                self.task.logger.warning(f"No noise results for {bundle[0].meta.get('filename')}, nothing saved.")
                continue
            noiseres.save(str(self.run_dir / _image_stem(bundle[0].meta.get("filename"), index)))
            self.result = self.result.combine(noiseres)
            yield noiseres
