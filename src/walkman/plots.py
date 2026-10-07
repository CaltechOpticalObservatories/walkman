"""
Interactive plots for the walkman dashboard, rendered with ipympl.

Each plot owns one figure whose artists are updated in place, so plots can be refreshed from a background thread
while keeping widget identity. Run `%matplotlib widget` in the notebook before creating plots.
"""
from collections.abc import Hashable
from html import escape

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import MaxNLocator
import numpy as np

SURFACE = "#fcfcfb"
GRID = "#e3e2de"
TEXT_SECONDARY = "#52514e"
# categorical hues, assigned in this fixed order
CATEGORICAL = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")


def series_color(index: int) -> str:
    """
    Color for the index-th series. Colors repeat after len(CATEGORICAL) series.

    :param index: Order in which the series first appeared.
    :return: Hex color.
    """
    return CATEGORICAL[index % len(CATEGORICAL)]


def noise_label_html(det_id: str, output: str, region: str, color: str) -> str:
    """
    Render the identity cell of a noise table row.

    :param det_id: Detector ID.
    :param output: Output ID.
    :param region: Image region.
    :param color: Series color of the row.
    :return: HTML string.
    """
    return (f"<div style='padding:6px 12px;font-weight:700;color:{color};line-height:1.3'>"
            f"<div style='font-size:18px'>DETECTOR: {escape(str(det_id))}</div>"
            f"<div style='font-size:16px'>{escape(str(output))}</div>"
            f"<div style='font-size:16px'>{escape(str(region))}</div></div>")


def noise_value_html(noise: float, color: str) -> str:
    """
    Render the noise cell of a noise table row.

    :param noise: Noise value.
    :param color: Series color of the row.
    :return: HTML string.
    """
    return (f"<div style='padding:6px 12px;text-align:right;font-size:44px;font-weight:700;color:{color}'>"
            f"{noise:.3g}</div>")


def _style_axes(ax: Axes, xlabel: str | None, ylabel: str | None) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT_SECONDARY, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_SECONDARY, fontsize=9)


def _check_pair(x: np.ndarray, y: np.ndarray, x_extra: int, names: str) -> tuple[np.ndarray, np.ndarray]:
    x, y = np.asarray(x), np.asarray(y)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size + x_extra or y.size < 1:
        raise ValueError(f"{names} must be non-empty 1D arrays with len(x) == len(y) + {x_extra}, got shapes "
                         f"{x.shape} and {y.shape}.")
    return x, y


class _Figure:
    """
    Base class for a figure whose ipympl canvas is used as a widget.
    """
    def __init__(self, figsize: tuple[float, float]):
        # ioff stops pyplot from displaying the figure on its own, the canvas is placed in a widget layout instead
        with plt.ioff():
            self.fig = plt.figure(figsize=figsize, layout="constrained", facecolor=SURFACE)
        self.fig.canvas.header_visible = False
        self.fig.canvas.toolbar_position = "left"

    @property
    def widget(self):
        """
        :return: The ipympl canvas widget of the figure.
        """
        return self.fig.canvas

    def close(self) -> None:
        """
        Close the figure and release it from pyplot.
        """
        plt.close(self.fig)


class _SeriesPlot(_Figure):
    """
    Base class for a single-axes figure with one Line2D per series key, which can be shown or hidden.
    """
    #: Whether rescaling also autoscales the x axis. Subclasses with a fixed x range set this to False.
    scalex = True

    def __init__(self, figsize: tuple[float, float], xlabel: str, ylabel: str):
        super().__init__(figsize)
        self.ax = self.fig.add_subplot()
        _style_axes(self.ax, xlabel, ylabel)
        self.lines = {}

    def _set_series(self, key: Hashable, x: np.ndarray, y: np.ndarray, **style) -> None:
        if key not in self.lines:
            self.lines[key], = self.ax.plot([], [], **style)
        self.lines[key].set_data(x, y)

    def set_visible(self, key: Hashable, visible: bool) -> None:
        """
        Show or hide a series, and rescale to the visible series.

        :param key: Series key.
        :param visible: Whether the series is shown.
        """
        if key not in self.lines:
            raise KeyError(f"No series {key!r} in {type(self).__name__}.")
        self.lines[key].set_visible(visible)
        self._rescale()

    def _rescale(self) -> None:
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view(scalex=self.scalex)
        self.fig.canvas.draw_idle()

    def clear(self) -> None:
        """
        Remove all series.
        """
        for line in self.lines.values():
            line.remove()
        self.lines = {}
        self.fig.canvas.draw_idle()


class PSDPlot(_SeriesPlot):
    """
    One-sided PSDs of several series on a log scale against frequency, over 0 to 0.5 cycles/pixel.
    """
    #: The x axis keeps its fixed 0 to 0.5 cycles/pixel range when rescaling.
    scalex = False

    def __init__(self, figsize: tuple[float, float] = (6, 3.6)):
        super().__init__(figsize, xlabel="Frequency (cycles/pixel)", ylabel="PSD")
        self.ax.set_yscale("log")
        self.ax.set_xlim(0, 0.5)

    def update(self, series: dict[Hashable, tuple[str, np.ndarray, np.ndarray]]) -> None:
        """
        Add or refresh lines, one per series key.

        :param series: Mapping of key to (color, freqs, psd). freqs are in cycles/pixel, same length as psd.
        """
        checked = {key: (color, *_check_pair(freqs, psd, 0, "freqs and psd"))
                   for key, (color, freqs, psd) in series.items()}
        for key, (color, freqs, psd) in checked.items():
            self._set_series(key, freqs, psd, color=color, linewidth=2,
                             solid_joinstyle="round", solid_capstyle="round")
        self._rescale()


class NoiseTrendPlot(_SeriesPlot):
    """
    Scatter of noise values against time, one marker series per series key.
    """
    def __init__(self, figsize: tuple[float, float] = (10.4, 3), xlabel: str = "Time"):
        super().__init__(figsize, xlabel=xlabel, ylabel="Noise")
        self.ax.xaxis.set_major_locator(MaxNLocator(6))
        self.ax.ticklabel_format(axis="x", useOffset=False)

    def update(self, series: dict[Hashable, tuple[str, np.ndarray, np.ndarray]]) -> None:
        """
        Add or refresh marker series, one per series key.

        :param series: Mapping of key to (color, times, noise). times must be numeric, same length as noise.
        """
        checked = {key: (color, *_check_pair(times, noise, 0, "times and noise"))
                   for key, (color, times, noise) in series.items()}
        for key, (color, times, noise) in checked.items():
            # the surface-colored marker edge keeps overlapping points legible
            self._set_series(key, times, noise, color=color, linestyle="none", marker="o", markersize=8,
                             markeredgecolor=SURFACE, markeredgewidth=2)
        self._rescale()


class HistogramGrid(_Figure):
    """
    Grid of pixel-value histograms with log counts, one titled subplot per series, filled row by row.
    """
    def __init__(self, ncols: int = 4, col_width: float = 2.6, row_height: float = 2.4):
        super().__init__((ncols * col_width, row_height))
        self.ncols = ncols
        self.row_height = row_height
        self.steps = {}

    def update(self, series: dict[Hashable, tuple[str, str, np.ndarray, np.ndarray]]) -> None:
        """
        Refresh histograms, rebuilding the grid when the set of series keys changes.

        :param series: Mapping of key to (title, color, bin_edges, counts). bin_edges is one longer than counts.
        """
        checked = {key: (title, color, *_check_pair(edges, counts, 1, "bin_edges and counts"))
                   for key, (title, color, edges, counts) in series.items()}
        if not checked:
            return
        if list(checked) != list(self.steps):
            self.fig.clear()
            nrows = -(-len(checked) // self.ncols)
            self.fig.set_size_inches(self.fig.get_figwidth(), nrows * self.row_height)
            axes = self.fig.subplots(nrows, self.ncols, squeeze=False).ravel()
            for ax in axes[len(checked):]:
                ax.set_visible(False)
            self.steps = {}
            for ax, (key, (title, color, _, _)) in zip(axes, checked.items()):
                _style_axes(ax, None, None)
                ax.set_title(title, color=TEXT_SECONDARY, fontsize=9)
                ax.set_yscale("log")
                ax.xaxis.set_major_locator(MaxNLocator(3))
                ax.ticklabel_format(axis="x", useOffset=False)
                self.steps[key] = ax.stairs([1], [0, 1], fill=True, color=color)
            self.fig.supxlabel("Pixel value", color=TEXT_SECONDARY, fontsize=9)
            self.fig.supylabel("Counts", color=TEXT_SECONDARY, fontsize=9)
        for key, (_, _, edges, counts) in checked.items():
            step = self.steps[key]
            step.set_data(counts, edges)
            step.axes.relim()
            step.axes.autoscale_view()
        self.fig.canvas.draw_idle()

    def clear(self) -> None:
        """
        Remove all histograms.
        """
        self.fig.clear()
        self.steps = {}
        self.fig.canvas.draw_idle()
