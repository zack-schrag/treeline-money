"""High-level API for pyplot - main entry points for creating plots."""

from typing import Any, List

from treeline.pyplot.plots.bar import Barplot
from treeline.pyplot.plots.box import Boxplot
from treeline.pyplot.plots.histogram import Histogram
from treeline.pyplot.plots.line import Lineplot
from treeline.pyplot.plots.scatter import Scatterplot


def barplot(
    labels: List[Any],
    values: List[float],
    title: str = "",
    xlabel: str = "",
    width: int = 60,
    color: str = "green",
    symbol: str = "■",
) -> Barplot:
    """Create a horizontal bar plot.

    Args:
        labels: Labels for each bar
        values: Values for each bar (must be non-negative)
        title: Plot title
        xlabel: X-axis label
        width: Plot width in characters
        color: Bar color (green, blue, red, yellow, cyan, magenta)
        symbol: Character to use for bars

    Returns:
        Barplot object (call .render() to get string output)

    Example:
        >>> chart = barplot(
        ...     labels=["Mon", "Tue", "Wed"],
        ...     values=[120, 150, 90],
        ...     title="Daily Sales",
        ...     xlabel="Sales ($)"
        ... )
        >>> print(chart.render())
    """
    return Barplot(
        labels=labels,
        values=values,
        title=title,
        xlabel=xlabel,
        width=width,
        color=color,
        symbol=symbol,
    )


def lineplot(
    x: List[float] | None = None,
    y: List[float] | None = None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    width: int = 60,
    height: int = 20,
    color: str = "blue",
) -> Lineplot:
    """Create a line plot with smooth curves.

    Args:
        x: X values (if None, uses indices 0, 1, 2, ...)
        y: Y values (required)
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        width: Plot width in characters
        height: Plot height in characters
        color: Line color

    Returns:
        Lineplot object (call .render() to get string output)

    Example:
        >>> chart = lineplot(
        ...     x=[1, 2, 3, 4, 5],
        ...     y=[10, 25, 15, 30, 20],
        ...     title="Temperature",
        ...     xlabel="Time (hours)",
        ...     ylabel="Temp (°C)"
        ... )
        >>> print(chart.render())
    """
    return Lineplot(
        x=x,
        y=y,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        width=width,
        height=height,
        color=color,
    )


def histogram(
    values: List[float],
    bins: int = 10,
    title: str = "",
    xlabel: str = "",
    width: int = 60,
    color: str = "cyan",
    symbol: str = "■",
) -> Histogram:
    """Create a histogram showing value distribution.

    Args:
        values: Data values to bin
        bins: Number of bins
        title: Plot title
        xlabel: X-axis label
        width: Plot width in characters
        color: Bar color
        symbol: Character to use for bars

    Returns:
        Histogram object (call .render() to get string output)

    Example:
        >>> import random
        >>> data = [random.gauss(100, 15) for _ in range(1000)]
        >>> chart = histogram(data, bins=20, title="Distribution")
        >>> print(chart.render())
    """
    return Histogram(
        values=values,
        bins=bins,
        title=title,
        xlabel=xlabel,
        width=width,
        color=color,
        symbol=symbol,
    )


def scatterplot(
    x: List[float],
    y: List[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    width: int = 60,
    height: int = 20,
    color: str = "magenta",
) -> Scatterplot:
    """Create a scatter plot.

    Args:
        x: X values
        y: Y values
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        width: Plot width in characters
        height: Plot height in characters
        color: Point color

    Returns:
        Scatterplot object (call .render() to get string output)

    Example:
        >>> chart = scatterplot(
        ...     x=[1, 2, 3, 4, 5],
        ...     y=[2, 4, 3, 5, 6],
        ...     title="Correlation",
        ...     xlabel="X",
        ...     ylabel="Y"
        ... )
        >>> print(chart.render())
    """
    return Scatterplot(
        x=x,
        y=y,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        width=width,
        height=height,
        color=color,
    )


def boxplot(
    data: List[List[float]],
    labels: List[str] | None = None,
    title: str = "",
    ylabel: str = "",
    width: int = 60,
    height: int = 20,
    color: str = "blue",
) -> Boxplot:
    """Create a box-and-whisker plot.

    Args:
        data: List of data series (one box per series)
        labels: Labels for each series (if None, uses "Box 1", "Box 2", etc.)
        title: Plot title
        ylabel: Y-axis label
        width: Plot width in characters
        height: Plot height in characters
        color: Box color

    Returns:
        Boxplot object (call .render() to get string output)

    Example:
        >>> chart = boxplot(
        ...     data=[[1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7]],
        ...     labels=["Group A", "Group B"],
        ...     title="Comparison"
        ... )
        >>> print(chart.render())
    """
    return Boxplot(
        data=data,
        labels=labels,
        title=title,
        ylabel=ylabel,
        width=width,
        height=height,
        color=color,
    )
