"""Base canvas class for plotting."""

from abc import ABC, abstractmethod
from typing import List, Tuple


class Canvas(ABC):
    """Abstract base class for plot canvases."""

    def __init__(self, width: int, height: int):
        """Initialize canvas.

        Args:
            width: Width in characters
            height: Height in characters
        """
        self.width = width
        self.height = height

    @abstractmethod
    def pixel(self, x: int, y: int, color: str | None = None) -> None:
        """Set a pixel in the canvas.

        Args:
            x: X coordinate (pixel coordinates, not character coordinates)
            y: Y coordinate (pixel coordinates, not character coordinates)
            color: Optional color for the pixel
        """
        pass

    @abstractmethod
    def render(self) -> str:
        """Render the canvas to a string.

        Returns:
            String representation of the canvas
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the canvas."""
        pass

    def line(self, x0: int, y0: int, x1: int, y1: int, color: str | None = None) -> None:
        """Draw a line using Bresenham's algorithm.

        Args:
            x0: Start X coordinate
            y0: Start Y coordinate
            x1: End X coordinate
            y1: End Y coordinate
            color: Optional color for the line
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.pixel(x0, y0, color)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
