"""
Generate the SYNTHETIC instrument's images, one 1024x1024 FITS file per detector. Two sets are available:

- **White noise** (`make_data`): Gaussian white noise with a different known noise level and bias offset per
  detector. For white noise of standard deviation σ, the one-sided PSD computed by walkman is flat at 2σ², so the
  detectors' PSD base levels are 2, 8, 18, 32 and 50 ADU²/(cycles/pixel). The differing bias offsets show that the
  offset does not change the PSD base level.
- **White noise + sine** (`make_sine_data`): the same white noise (σ = 1 ADU) on every detector, plus a sine of a
  different amplitude A per detector, along the readout order. The sine gives a PSD spike whose area above the base
  level is A²/2, and whose peak height above the base level is (A²/2)·N/ENBW for PSD segment length N and window
  equivalent noise bandwidth ENBW (in bins, 1.363 for hamming).

Usage::

    python -m walkman.instruments.SYNTHETIC.make_data [OUTPUT_DIR] [--sine] [--seed N]
"""
from pathlib import Path
import argparse

from astropy.io import fits
import numpy as np

#: Injected noise standard deviation of each detector, in ADU.
NOISE_LEVELS = (1.0, 2.0, 3.0, 4.0, 5.0)
#: Constant bias offset of each detector, in ADU.
BIAS_LEVELS = (500.0, 1000.0, 1500.0, 2000.0, 2500.0)
#: Image size (rows, columns), must match synthetic.yaml.
SHAPE = (1024, 1024)
#: MJD-OBS of the first image, the next images follow one minute apart.
START_MJD = 61300.0

#: Sine amplitude of each detector in the sine set, in ADU.
SINE_AMPLITUDES = (0.1, 0.3, 1.0, 3.0, 10.0)
#: Sine frequency in cycles/pixel along the readout order. 0.25 is on a frequency bin for any PSD segment length
#: divisible by 4, and keeps the sine phase-continuous when a region of width 1024, 1004, 100 or 80 pixels is raveled.
SINE_FREQUENCY = 0.25
#: White noise standard deviation and bias offset shared by all detectors in the sine set, in ADU.
SINE_SET_NOISE = 1.0
SINE_SET_BIAS = 1000.0


def _write_image(path: Path, data: np.ndarray, header: fits.Header) -> Path:
    # primary HDU holds the header, extension 1 holds the image (ext_id 1 in synthetic.yaml)
    fits.HDUList([fits.PrimaryHDU(header=header), fits.ImageHDU(data, name="A")]).writeto(path, overwrite=True)
    return path


def _base_header(n: int, noise: float, bias: float) -> fits.Header:
    header = fits.Header()
    header["MJD-OBS"] = (START_MJD + (n - 1) / 1440, "synthetic exposure time")
    header["IMAGETYP"] = "bias"
    header["EXPTIME"] = 0.0
    header["NOISE"] = (noise, "injected white noise std (ADU)")
    header["BIAS"] = (bias, "injected bias offset (ADU)")
    return header


def make_data(output_dir: str | Path = "data/synthetic", seed: int = 0) -> list[Path]:
    """
    Write one white noise FITS file per detector.

    Each file has a primary HDU holding the header (MJD-OBS, IMAGETYP, EXPTIME and the injected NOISE and BIAS) and
    one float32 image extension holding `bias + noise * N(0, 1)`. float32 keeps the values unquantized, so the PSD
    base level is exactly 2σ² rather than 2(σ² + 1/12) for integer data.

    :param output_dir: Folder the files are written to, created if missing.
    :param seed: Seed of the random number generator, so the data can be regenerated identically.
    :return: Paths of the written files.
    """
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    paths = []
    for n, (noise, bias) in enumerate(zip(NOISE_LEVELS, BIAS_LEVELS), start=1):
        data = (bias + noise * rng.standard_normal(SHAPE)).astype(np.float32)
        paths.append(_write_image(output_dir / f"SYN_det{n}_bias.fits", data, _base_header(n, noise, bias)))
    return paths


def make_sine_data(output_dir: str | Path = "data/synthetic_sine", seed: int = 1) -> list[Path]:
    """
    Write one white noise + sine FITS file per detector.

    Each image is `bias + noise * N(0, 1) + A * sin(2π f n + φ)`, where n = row * 1024 + col is the pixel's position
    in the readout order, A is the detector's entry in SINE_AMPLITUDES, f is SINE_FREQUENCY and φ is a random phase.
    The header adds SINEAMP, SINEFREQ and SINEPHS to the white noise set's keywords.

    :param output_dir: Folder the files are written to, created if missing. Keep it apart from the white noise set,
        since walkman searches data folders recursively.
    :param seed: Seed of the random number generator, so the data can be regenerated identically.
    :return: Paths of the written files.
    """
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    readout_index = np.arange(SHAPE[0] * SHAPE[1], dtype=np.float64).reshape(SHAPE)
    paths = []
    for n, amplitude in enumerate(SINE_AMPLITUDES, start=1):
        phase = rng.uniform(0, 2 * np.pi)
        sine = amplitude * np.sin(2 * np.pi * SINE_FREQUENCY * readout_index + phase)
        data = (SINE_SET_BIAS + SINE_SET_NOISE * rng.standard_normal(SHAPE) + sine).astype(np.float32)
        header = _base_header(n, SINE_SET_NOISE, SINE_SET_BIAS)
        header["SINEAMP"] = (amplitude, "injected sine amplitude (ADU)")
        header["SINEFREQ"] = (SINE_FREQUENCY, "injected sine frequency (cycles/pixel)")
        header["SINEPHS"] = (phase, "injected sine phase (rad)")
        paths.append(_write_image(output_dir / f"SYN_det{n}_sine.fits", data, header))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the SYNTHETIC instrument's images.")
    parser.add_argument("output_dir", nargs="?", default=None,
                        help="Default: data/synthetic, or data/synthetic_sine with --sine")
    parser.add_argument("--sine", action="store_true", help="Generate the white noise + sine set")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Default: 0, or 1 with --sine")
    args = parser.parse_args()
    if args.sine:
        paths = make_sine_data(args.output_dir or "data/synthetic_sine", 1 if args.seed is None else args.seed)
        # peak above the 2σ² base level for the default 512-pixel PSD segments and hamming window (ENBW 1.363 bins)
        print(f"{'detector':<10}{'sine A':>8}{'freq':>7}{'noise σ':>9}{'base 2σ²':>10}{'area A²/2':>11}"
              f"{'peak (N=512)':>14}  file")
        for n, (path, amplitude) in enumerate(zip(paths, SINE_AMPLITUDES), start=1):
            print(f"{'det_' + str(n):<10}{amplitude:>8g}{SINE_FREQUENCY:>7g}{SINE_SET_NOISE:>9g}"
                  f"{2 * SINE_SET_NOISE ** 2:>10g}{amplitude ** 2 / 2:>11g}{amplitude ** 2 / 2 * 512 / 1.363:>14.4g}"
                  f"  {path}")
    else:
        paths = make_data(args.output_dir or "data/synthetic", 0 if args.seed is None else args.seed)
        print(f"{'detector':<10}{'noise σ':>9}{'bias':>8}{'PSD level 2σ²':>15}  file")
        for n, (path, noise, bias) in enumerate(zip(paths, NOISE_LEVELS, BIAS_LEVELS), start=1):
            print(f"{'det_' + str(n):<10}{noise:>9g}{bias:>8g}{2 * noise ** 2:>15g}  {path}")


if __name__ == "__main__":
    main()
