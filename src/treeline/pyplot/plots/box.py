"""Box plot implementation for statistical visualization."""

import statistics
from typing import List

from treeline.pyplot.plots.base import Plot
from treeline.pyplot.utils import BOX_LIGHT, colorize, format_number


def compute_quartiles(values: List[float]) -> tuple[float, float, float, float, float]:
    """Compute five-number summary (min, Q1, median, Q3, max).

    Args:
        values: Data values

    Returns:
        Tuple of (min, q1, median, q3, max)
    """
    sorted_values = sorted(values)
    n = len(sorted_values)

    if n == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    min_val = sorted_values[0]
    max_val = sorted_values[-1]
    median = statistics.median(sorted_values)

    # Q1 is median of lower half
    lower_half = sorted_values[:n // 2]
    q1 = statistics.median(lower_half) if lower_half else min_val

    # Q3 is median of upper half
    upper_half = sorted_values[(n + 1) // 2:]
    q3 = statistics.median(upper_half) if upper_half else max_val

    return (min_val, q1, median, q3, max_val)


class Boxplot(Plot):
    """Box-and-whisker plot for showing distribution statistics."""

    def __init__(
        self,
        data: List[List[float]],
        labels: List[str] | None = None,
        title: str = "",
        ylabel: str = "",
        width: int = 60,
        height: int = 20,
        color: str = "blue",
    ):
        """Initialize boxplot.

        Args:
            data: List of data series (one box per series)
            labels: Labels for each series
            title: Plot title
            ylabel: Y-axis label
            width: Plot width in characters
            height: Plot height in characters
            color: Box color
        """
        super().__init__(
            title=title,
            xlabel="",
            ylabel=ylabel,
            width=width,
            height=height,
        )

        self.data = data
        self.labels = labels if labels else [f"Box {i+1}" for i in range(len(data))]
        self.color = color

        if len(self.labels) != len(self.data):
            raise ValueError("Number of labels must match number of data series")

    def render(self) -> str:
        """Render the boxplot.

        Returns:
            String representation of the boxplot
        """
        if not self.data:
            return "Empty plot (no data)"

        lines = []

        # Title
        if self.title:
            lines.append(f"  {self.title}")
            lines.append("")

        # Compute statistics for each series
        stats = [compute_quartiles(series) for series in self.data]

        # Get global min/max for scaling
        all_mins = [s[0] for s in stats]
        all_maxs = [s[4] for s in stats]
        global_min = min(all_mins)
        global_max = max(all_maxs)

        if global_min == global_max:
            global_max = global_min + 1

        # Calculate dimensions
        max_label_len = max(len(label) for label in self.labels)
        y_label_width = 10

        # Available width for box plot
        available_width = self.width - max_label_len - y_label_width - 6

        if available_width < 20:
            available_width = 20

        # Create each box
        for label, (min_val, q1, median, q3, max_val) in zip(self.labels, stats):
            # Scale positions to available width
            value_range = global_max - global_min

            def scale_pos(value: float) -> int:
                return int(((value - global_min) / value_range) * available_width)

            min_pos = scale_pos(min_val)
            q1_pos = scale_pos(q1)
            med_pos = scale_pos(median)
            q3_pos = scale_pos(q3)
            max_pos = scale_pos(max_val)

            # Build box visualization
            # Format: "  <label>  |-----[===|===]-----|"
            #                     min  q1 med q3    max

            box_line = [' '] * available_width

            # Whiskers
            for i in range(min_pos, q1_pos):
                box_line[i] = '─'
            for i in range(q3_pos, max_pos + 1):
                box_line[i] = '─'

            # Box (Q1 to Q3)
            for i in range(q1_pos, q3_pos + 1):
                box_line[i] = '█'

            # Median line
            if med_pos < len(box_line):
                box_line[med_pos] = '│'

            # Whisker endpoints
            if min_pos < len(box_line):
                box_line[min_pos] = '├'
            if max_pos < len(box_line):
                box_line[max_pos] = '┤'

            # Join and colorize
            box_str = ''.join(box_line)
            if self.color:
                box_str = colorize(box_str, self.color)

            # Format line
            label_part = f"{label:>{max_label_len}}"
            line = f"  {label_part}  {box_str}"
            lines.append(line)

        # Add scale at bottom
        lines.append("")
        scale_line = " " * (max_label_len + 4)
        scale_line += f"├{'─' * available_width}┤"
        lines.append(scale_line)

        # Add tick labels
        tick_line = " " * (max_label_len + 4)
        tick_line += format_number(global_min)

        mid_val = (global_min + global_max) / 2
        mid_label = format_number(mid_val)
        mid_padding = available_width // 2 - len(tick_line) + max_label_len + 4 - len(mid_label) // 2
        tick_line += " " * mid_padding + mid_label

        # Right-align max label
        max_label = format_number(global_max)
        max_padding = available_width - (len(tick_line) - max_label_len - 4) - len(max_label)
        tick_line += " " * max_padding + max_label

        lines.append(tick_line)

        # Y-axis label
        if self.ylabel:
            label_padding = (self.width - len(self.ylabel)) // 2
            lines.append(f"{' ' * label_padding}{self.ylabel}")

        return '\n'.join(lines)
