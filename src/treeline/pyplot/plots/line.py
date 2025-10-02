"""Line plot implementation using braille canvas."""

from typing import List

from treeline.pyplot.canvas.braille import BrailleCanvas
from treeline.pyplot.plots.base import Plot
from treeline.pyplot.utils import BOX_LIGHT, colorize, format_number, get_axis_range, scale_values


class Lineplot(Plot):
    """Line plot using braille canvas for smooth curves."""

    def __init__(
        self,
        x: List[float] | None = None,
        y: List[float] | None = None,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        width: int = 60,
        height: int = 20,
        color: str = "blue",
    ):
        """Initialize lineplot.

        Args:
            x: X values (if None, use indices)
            y: Y values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            width: Plot width in characters
            height: Plot height in characters
            color: Line color
        """
        super().__init__(
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            width=width,
            height=height,
        )

        if y is None:
            raise ValueError("y values are required")

        self.y = y
        self.x = x if x is not None else list(range(len(y)))
        self.color = color

        if len(self.x) != len(self.y):
            raise ValueError("x and y must have the same length")

    def render(self) -> str:
        """Render the lineplot.

        Returns:
            String representation of the lineplot
        """
        if not self.y:
            return "Empty plot (no data)"

        lines = []

        # Title
        if self.title:
            lines.append(f"  {self.title}")
            lines.append("")

        # Reserve space for y-axis labels
        y_label_width = 8

        # Actual plot area width/height
        plot_width = self.width - y_label_width - 4
        plot_height = self.height

        # Create braille canvas
        canvas = BrailleCanvas(plot_width, plot_height)

        # Get data ranges
        x_min, x_max = min(self.x), max(self.x)
        y_min, y_max = get_axis_range(self.y)

        # Scale data to pixel coordinates
        pixel_width = canvas.pixel_width
        pixel_height = canvas.pixel_height

        # Convert data points to pixel coordinates
        x_pixels = scale_values(self.x, 0, pixel_width - 1, x_min, x_max)
        y_pixels = scale_values(self.y, pixel_height - 1, 0, y_min, y_max)  # Invert Y axis

        # Draw line segments
        for i in range(len(x_pixels) - 1):
            x0, y0 = int(x_pixels[i]), int(y_pixels[i])
            x1, y1 = int(x_pixels[i + 1]), int(y_pixels[i + 1])
            canvas.line(x0, y0, x1, y1, self.color)

        # Render canvas
        canvas_lines = canvas.render().split('\n')

        # Add y-axis labels and borders
        y_ticks = [y_max, (y_max + y_min) / 2, y_min]
        y_tick_labels = [format_number(y) for y in y_ticks]
        y_tick_positions = [0, plot_height // 2, plot_height - 1]

        for i, canvas_line in enumerate(canvas_lines):
            # Y-axis label for this line
            y_label = ""
            for tick_label, tick_pos in zip(y_tick_labels, y_tick_positions):
                if i == tick_pos:
                    y_label = f"{tick_label:>{y_label_width}}"
                    break

            if not y_label:
                y_label = " " * y_label_width

            # Add border and y-axis
            if i == 0:
                border = BOX_LIGHT["top_left"] + BOX_LIGHT["horizontal"] * plot_width + BOX_LIGHT["top_right"]
                line = f"{y_label} {border}"
            elif i == plot_height - 1:
                border = BOX_LIGHT["bottom_left"] + BOX_LIGHT["horizontal"] * plot_width + BOX_LIGHT["bottom_right"]
                line = f"{y_label} {border}"
            else:
                line = f"{y_label} {BOX_LIGHT['vertical']}{canvas_line}{BOX_LIGHT['vertical']}"

            lines.append(line)

        # X-axis labels
        x_tick_labels = [format_number(x_min), format_number((x_min + x_max) / 2), format_number(x_max)]
        x_axis_line = " " * y_label_width + " "

        # Distribute x labels across the width
        label_spacing = plot_width // (len(x_tick_labels) - 1) if len(x_tick_labels) > 1 else plot_width

        for i, label in enumerate(x_tick_labels):
            if i == 0:
                x_axis_line += label
            elif i == len(x_tick_labels) - 1:
                # Right-align last label
                padding = plot_width - len(x_axis_line) + y_label_width + 1 - len(label)
                x_axis_line += " " * padding + label
            else:
                # Center middle labels
                padding = i * label_spacing - (len(x_axis_line) - y_label_width - 1) - len(label) // 2
                x_axis_line += " " * padding + label

        lines.append(x_axis_line)

        # Axis labels
        if self.xlabel:
            label_padding = (self.width - len(self.xlabel)) // 2
            lines.append(f"{' ' * label_padding}{self.xlabel}")

        if self.ylabel:
            # Y-label goes on the left side, vertically centered
            ylabel_line = plot_height // 2
            if ylabel_line < len(lines):
                lines.insert(ylabel_line, f"{self.ylabel}")

        return '\n'.join(lines)
