"""Utility functions for Treeline."""

import os
from pathlib import Path


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the user's home directory.

    Returns:
        Path to the treeline directory (default: ~/.treeline)
        Can be overridden with TREELINE_DIR environment variable for testing.
    """
    treeline_dir_override = os.getenv("TREELINE_DIR")
    if treeline_dir_override:
        return Path(treeline_dir_override)
    return Path.home() / ".treeline"
