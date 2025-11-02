"""Utility functions for Treeline."""

from pathlib import Path


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the user's home directory.

    Returns:
        Path to the treeline directory (default: ~/.treeline)
    """
    return Path.home() / ".treeline"
