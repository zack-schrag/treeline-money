"""Histogram implementation."""

from typing import List

from treeline.pyplot.plots.bar import Barplot
from treeline.pyplot.utils import compute_bins, format_number


class Histogram(Barplot):
    """Histogram plot (vertical bars showing distribution)."""

    def __init__(
        self,
        values: List[float],
        bins: int = 10,
        title: str = "",
        xlabel: str = "",
        width: int = 60,
        color: str = "cyan",
        symbol: str = "■",
    ):
        """Initialize histogram.

        Args:
            values: Data values to bin
            bins: Number of bins
            title: Plot title
            xlabel: X-axis label
            width: Plot width in characters
            color: Bar color
            symbol: Character to use for bars
        """
        # Compute bins
        bin_edges, counts = compute_bins(values, bins)

        # Create labels for bins (show range)
        labels = []
        for i in range(len(counts)):
            if i < len(bin_edges) - 1:
                start = format_number(bin_edges[i], precision=1)
                end = format_number(bin_edges[i + 1], precision=1)
                labels.append(f"{start}-{end}")
            else:
                labels.append(f"{format_number(bin_edges[i], precision=1)}+")

        # Initialize as barplot with bin counts
        super().__init__(
            labels=labels,
            values=counts,
            title=title or "Histogram",
            xlabel=xlabel or "Value",
            width=width,
            color=color,
            symbol=symbol,
        )
