"""Block canvas using block drawing characters."""

from typing import List

from treeline.pyplot.canvas.base import Canvas
from treeline.pyplot.utils import colorize


class BlockCanvas(Canvas):
    """Canvas using block characters (█, ▀, ▄).

    Each character represents 1×2 pixels (upper and lower half).
    """

    X_PIXELS_PER_CHAR = 1
    Y_PIXELS_PER_CHAR = 2

    # Block characters for different pixel combinations
    BLOCKS = {
        (False, False): ' ',
        (True, False): '▀',  # Upper half
        (False, True): '▄',  # Lower half
        (True, True): '█',   # Full block
    }

    def __init__(self, width: int, height: int):
        """Initialize block canvas.

        Args:
            width: Width in characters
            height: Height in characters
        """
        super().__init__(width, height)
        self.pixel_width = width * self.X_PIXELS_PER_CHAR
        self.pixel_height = height * self.Y_PIXELS_PER_CHAR

        # Track which half-pixels are set
        # grid[y][x] = (upper, lower) tuple of bools
        self.grid: List[List[tuple[bool, bool]]] = [
            [(False, False)] * width for _ in range(height)
        ]

        # Color for each character
        self.colors: List[List[str | None]] = [
            [None] * width for _ in range(height)
        ]

    def pixel(self, x: int, y: int, color: str | None = None) -> None:
        """Set a pixel in the canvas.

        Args:
            x: X coordinate (0 to pixel_width-1)
            y: Y coordinate (0 to pixel_height-1)
            color: Optional color for the pixel
        """
        # Bounds check
        if not (0 <= x < self.pixel_width and 0 <= y < self.pixel_height):
            return

        # Convert pixel coordinates to character coordinates
        char_x = x // self.X_PIXELS_PER_CHAR
        char_y = y // self.Y_PIXELS_PER_CHAR

        # Determine if upper or lower half
        half = y % self.Y_PIXELS_PER_CHAR  # 0 = upper, 1 = lower

        # Set the appropriate half
        upper, lower = self.grid[char_y][char_x]
        if half == 0:
            upper = True
        else:
            lower = True

        self.grid[char_y][char_x] = (upper, lower)

        # Set color if provided
        if color:
            self.colors[char_y][char_x] = color

    def render(self) -> str:
        """Render the canvas to a string.

        Returns:
            String with block characters representing the plot
        """
        lines = []
        for y in range(self.height):
            line_chars = []
            for x in range(self.width):
                upper, lower = self.grid[y][x]
                char = self.BLOCKS[(upper, lower)]
                color = self.colors[y][x]

                if color:
                    char = colorize(char, color)

                line_chars.append(char)

            lines.append(''.join(line_chars))

        return '\n'.join(lines)

    def clear(self) -> None:
        """Clear the canvas."""
        self.grid = [
            [(False, False)] * self.width for _ in range(self.height)
        ]
        self.colors = [
            [None] * self.width for _ in range(self.height)
        ]
