"""Horizontal bar plot implementation."""

from typing import Any, List

from treeline.pyplot.plots.base import Plot
from treeline.pyplot.utils import BOX_LIGHT, colorize, format_number


class Barplot(Plot):
    """Horizontal bar chart with Unicode box drawing."""

    def __init__(
        self,
        labels: List[Any],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        width: int = 60,
        color: str = "green",
        symbol: str = "■",
    ):
        """Initialize barplot.

        Args:
            labels: Labels for each bar
            values: Values for each bar (must be non-negative)
            title: Plot title
            xlabel: X-axis label
            width: Plot width in characters
            color: Bar color
            symbol: Character to use for bars
        """
        # Height is determined by number of bars
        super().__init__(
            title=title,
            xlabel=xlabel,
            ylabel="",
            width=width,
            height=len(values),
        )

        if len(labels) != len(values):
            raise ValueError("labels and values must have the same length")

        if any(v < 0 for v in values):
            raise ValueError("All values must be non-negative")

        self.labels = [str(label) for label in labels]
        self.values = values
        self.color = color
        self.symbol = symbol

    def render(self) -> str:
        """Render the barplot.

        Returns:
            String representation of the barplot
        """
        if not self.values:
            return "Empty plot (no data)"

        lines = []

        # Title
        if self.title:
            title_line = f"  {self.title}"
            lines.append(title_line)
            lines.append("")

        # Calculate dimensions
        max_label_len = max(len(label) for label in self.labels) if self.labels else 0
        max_value = max(self.values) if self.values else 1

        # Format values to determine value column width
        formatted_values = [format_number(v) for v in self.values]
        max_value_len = max(len(fv) for fv in formatted_values)

        # Available width for bars
        # Format: "  <label> ┤<bar> <value>"
        available_width = self.width - max_label_len - max_value_len - 6

        if available_width < 10:
            available_width = 10

        # Top border
        border_padding = " " * max_label_len
        border = f"  {border_padding} ┌{'─' * (available_width + max_value_len + 2)}┐"
        lines.append(border)

        # Bars
        for label, value, formatted_value in zip(self.labels, self.values, formatted_values):
            # Calculate bar length
            if max_value > 0:
                bar_len = int((value / max_value) * available_width)
            else:
                bar_len = 0

            # Create bar
            bar = self.symbol * bar_len

            # Apply color
            if self.color:
                bar = colorize(bar, self.color)

            # Format line: "  <label> ┤<bar> <value>"
            label_part = f"{label:>{max_label_len}}"
            value_part = f"{formatted_value:>{max_value_len}}"
            line = f"  {label_part} ┤{bar} {value_part}"

            lines.append(line)

        # Bottom border
        border = f"  {border_padding} └{'─' * (available_width + max_value_len + 2)}┘"
        lines.append(border)

        # X-axis label
        if self.xlabel:
            label_padding = (self.width - len(self.xlabel)) // 2
            xlabel_line = f"{' ' * label_padding}{self.xlabel}"
            lines.append(xlabel_line)

        return '\n'.join(lines)
