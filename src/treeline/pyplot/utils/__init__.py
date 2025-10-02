"""Utility modules for pyplot."""

from treeline.pyplot.utils.colors import colorize, strip_colors
from treeline.pyplot.utils.scaling import scale_values, get_axis_range, compute_bins, format_number
from treeline.pyplot.utils.unicode import BOX_LIGHT, BLOCKS, MARKERS, BRAILLE_BASE, BRAILLE_DOTS

__all__ = [
    "colorize",
    "strip_colors",
    "scale_values",
    "get_axis_range",
    "compute_bins",
    "format_number",
    "BOX_LIGHT",
    "BLOCKS",
    "MARKERS",
    "BRAILLE_BASE",
    "BRAILLE_DOTS",
]
