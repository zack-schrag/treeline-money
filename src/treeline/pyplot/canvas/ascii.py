"""ASCII canvas using basic characters (fallback for limited terminals)."""

from typing import List

from treeline.pyplot.canvas.base import Canvas


class AsciiCanvas(Canvas):
    """Simple ASCII canvas using * and # characters.

    No color support, 1:1 pixel to character mapping.
    """

    def __init__(self, width: int, height: int, fill_char: str = '*'):
        """Initialize ASCII canvas.

        Args:
            width: Width in characters
            height: Height in characters
            fill_char: Character to use for filled pixels
        """
        super().__init__(width, height)
        self.pixel_width = width
        self.pixel_height = height
        self.fill_char = fill_char

        # Simple character grid
        self.grid: List[List[str]] = [
            [' '] * width for _ in range(height)
        ]

    def pixel(self, x: int, y: int, color: str | None = None) -> None:
        """Set a pixel in the canvas.

        Args:
            x: X coordinate (0 to width-1)
            y: Y coordinate (0 to height-1)
            color: Ignored (ASCII canvas doesn't support color)
        """
        # Bounds check
        if not (0 <= x < self.pixel_width and 0 <= y < self.pixel_height):
            return

        self.grid[y][x] = self.fill_char

    def render(self) -> str:
        """Render the canvas to a string.

        Returns:
            String with ASCII characters representing the plot
        """
        return '\n'.join(''.join(row) for row in self.grid)

    def clear(self) -> None:
        """Clear the canvas."""
        self.grid = [
            [' '] * self.width for _ in range(self.height)
        ]
