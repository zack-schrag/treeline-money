"""Base plot class."""

from abc import ABC, abstractmethod


class Plot(ABC):
    """Abstract base class for plots."""

    def __init__(
        self,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        width: int = 60,
        height: int = 20,
    ):
        """Initialize plot.

        Args:
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            width: Plot width in characters
            height: Plot height in characters
        """
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.width = width
        self.height = height

    @abstractmethod
    def render(self) -> str:
        """Render the plot to a string.

        Returns:
            String representation of the plot
        """
        pass
