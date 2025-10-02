"""ANSI color utilities for terminal output."""

import sys
from typing import Dict


# ANSI color codes
COLORS: Dict[str, str] = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "normal": "\033[0m",
}

RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Apply ANSI color to text if terminal supports it.

    Args:
        text: Text to colorize
        color: Color name (e.g., 'green', 'blue', 'red')

    Returns:
        Colorized text if terminal supports it, otherwise plain text
    """
    if not sys.stdout.isatty():
        return text

    color_code = COLORS.get(color.lower(), "")
    if not color_code:
        return text

    return f"{color_code}{text}{RESET}"


def strip_colors(text: str) -> str:
    """Remove ANSI color codes from text.

    Args:
        text: Text potentially containing ANSI codes

    Returns:
        Text with color codes removed
    """
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    return ansi_escape.sub('', text)
