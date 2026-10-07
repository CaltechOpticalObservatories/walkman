import os
import numpy as np
import pandas as pd
from typing import Literal, Optional, Callable
from pydantic import Field, ConfigDict, field_validator

from eregion.tasks import Task, TaskResult
from eregion.datamodels import DetImage, ImageBundle, CCDOutput
from eregion.utils import save_dataframe_to_fits, load_dataframe_from_fits
from eregion.core.image_stats import do_statistics, STATFUNCS
from eregion.core.welch2d import raveled_welch
from eregion.core.entropy import entropy_optimal_histogram

class AtomicNoiseResult(TaskResult):
    det_id: str = Field(..., description="Detector ID or identifier for the DetImage.")
    output: str = Field(..., description="Output (Channel/amplifier) ID.")
    region: Literal["full", "image", "overscan"] = Field(..., description="Region of the image analyzed for noise.")
    noise: float = Field(np.nan, description="Estimated noise level in the region.")
    histogram: tuple[np.ndarray, np.ndarray] = Field((np.array([]), np.array([])),
                                description="Histogram of pixel values in the region. Tuple of (bin_edges, counts).")
    psd: tuple[np.ndarray, np.ndarray] = Field((np.array([]), np.array([])),
                                description="One-dimensional raveled-welch PSD of the region.")

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

class NoiseResult(TaskResult):
    """ Holds a dataframe made from a list of AtomicNoiseResult objects."""
    data: pd.DataFrame = Field(pd.DataFrame(),
                               description="DataFrame containing noise analysis results for multiple DetImages. "
                                           "Can pass a list of AtomicNoiseResult objects or a pre-constructed DataFrame.")

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    @field_validator("data", mode="before")
    def validate_data(cls, v):
        if isinstance(v, list) and all(isinstance(item, AtomicNoiseResult) for item in v):
            # Convert list of AtomicNoiseResult to DataFrame
            return pd.DataFrame([item.model_dump() for item in v])
        elif isinstance(v, pd.DataFrame):
            return v
        else:
            raise ValueError("data must be a list of AtomicNoiseResult or a pandas DataFrame.")

    def save(self, filepath: str) -> None:
        """ Save the NoiseResult to a FITS file. """
        save_dataframe_to_fits(self.data, os.path.join(filepath, 'noise_results.fits'))
        super().save(filepath)

    @classmethod
    def load(cls, filepath: str) -> "NoiseResult":
        """ Load the NoiseResult from a FITS file. """
        data = load_dataframe_from_fits(os.path.join(filepath, 'noise_results.fits'))
        metadata = cls.load_metadata(filepath)
        return cls(data=data, **metadata)


class NoisePSD(Task):
    """
    Task to compute the power spectral density (PSD) of an image to analyze its noise characteristics.
    """
    task_result = NoiseResult

    def __init__(self,
                 name: Optional[str] = None,
                 **kwargs):
        kwargs["timestamp_key"] = kwargs.get("timestamp_key", "MJD-OBS")
        super().__init__(name=name, **kwargs)

    def run(self,
            images: ImageBundle | list[DetImage],
            regions: list[Literal["full", "image", "overscan"]] = ["full", "overscan"],
            trim_start: int = 0,
            trim_end: int = 0,
            target_shape: Optional[int] = None,
            window_func: str | Callable = "hamming",
            **kwargs) -> NoiseResult:
        images = images if isinstance(images, ImageBundle) else ImageBundle(images)
        target_shape = target_shape or min(512, np.max([list(img.shape) for img in images]))

        atomic_noise_results = []
        for img in images:
            for out_id, output in img.outputs.items():
                for region in regions:
                    match region:
                        case "full":
                            region_data = output.data
                        case "image":
                            region_data, _ = output.get_image_region()
                        case "overscan":
                            if not isinstance(output, CCDOutput):
                                raise ValueError("Overscan region is only available for CCDOutput.")
                            region_data = output.get_overscan('serial', corner=False)
                    # region trimmed
                    trimslice = (slice(trim_start, region_data.shape[0] - trim_end),
                                    slice(trim_start, region_data.shape[1] - trim_end))
                    trimdat = region_data.values[trimslice]
                    if trimdat.size == 0:
                        self.logger.warning(f"Trimmed region is empty for det_id={img.id}, output={out_id}, "
                                            f"region={region}. Skipping.")
                        continue
                    # compute basic stats
                    BASICSTATS = {key: STATFUNCS[key] for key in ["mean", "median", "std", "mad"]}
                    region_stats = do_statistics(trimdat, which=BASICSTATS)
                    hist = entropy_optimal_histogram(trimdat, dither=True)
                    f, psd = raveled_welch(trimdat, target_shape=target_shape, window_func=window_func, **kwargs)

                    resdict = {"det_id": img.id, "output": out_id, "region": region,
                               "noise": region_stats.pop("std"), "histogram": (hist["bin_edges"], hist["counts"]),
                               "psd": (f, psd)}
                    resdict.update(region_stats)
                    resdict["filename"] = img.meta.get("filename", None)
                    resdict["time"] = img.meta.get(self.meta["timestamp_key"], None)
                    atomic_noise_results.append(AtomicNoiseResult(**resdict))

        return self.task_result(data=atomic_noise_results)


