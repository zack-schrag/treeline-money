"""Braille canvas for high-resolution plotting (2×4 pixels per character)."""

from typing import List

from treeline.pyplot.canvas.base import Canvas
from treeline.pyplot.utils import BRAILLE_BASE, BRAILLE_DOTS, colorize


class BrailleCanvas(Canvas):
    """High-resolution canvas using Unicode braille characters.

    Each character represents 2×4 pixels using braille dots.
    Braille Unicode range: U+2800 to U+28FF
    """

    X_PIXELS_PER_CHAR = 2
    Y_PIXELS_PER_CHAR = 4

    def __init__(self, width: int, height: int):
        """Initialize braille canvas.

        Args:
            width: Width in characters
            height: Height in characters
        """
        super().__init__(width, height)
        self.pixel_width = width * self.X_PIXELS_PER_CHAR
        self.pixel_height = height * self.Y_PIXELS_PER_CHAR

        # Grid stores Unicode codepoints (start with blank braille char)
        self.grid: List[List[int]] = [
            [BRAILLE_BASE] * width for _ in range(height)
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

        # Get position within the character (which dot)
        dot_x = x % self.X_PIXELS_PER_CHAR
        dot_y = y % self.Y_PIXELS_PER_CHAR

        # Set the appropriate braille dot using bitwise OR
        self.grid[char_y][char_x] |= BRAILLE_DOTS[dot_x][dot_y]

        # Set color if provided
        if color:
            self.colors[char_y][char_x] = color

    def render(self) -> str:
        """Render the canvas to a string.

        Returns:
            String with braille characters representing the plot
        """
        lines = []
        for y in range(self.height):
            line_chars = []
            for x in range(self.width):
                char = chr(self.grid[y][x])
                color = self.colors[y][x]

                if color:
                    char = colorize(char, color)

                line_chars.append(char)

            lines.append(''.join(line_chars))

        return '\n'.join(lines)

    def clear(self) -> None:
        """Clear the canvas to blank braille characters."""
        self.grid = [
            [BRAILLE_BASE] * self.width for _ in range(self.height)
        ]
        self.colors = [
            [None] * self.width for _ in range(self.height)
        ]
