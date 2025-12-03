"""Configuration management for Treeline."""

import json
from pathlib import Path
from typing import Any, Dict

from treeline.utils import get_treeline_dir


def get_config_path() -> Path:
    """Get path to config file."""
    return get_treeline_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """Load config from file, returning empty dict if not found."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save config to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def is_demo_mode() -> bool:
    """Check if demo mode is enabled.

    Demo mode can be enabled via:
    1. Config file (tl demo on)
    2. Environment variable TREELINE_DEMO_MODE (for CI/testing)
    """
    import os

    # Env var takes precedence (for CI/testing)
    env_demo = os.getenv("TREELINE_DEMO_MODE", "").lower()
    if env_demo in ("true", "1", "yes"):
        return True
    if env_demo in ("false", "0", "no"):
        return False

    # Fall back to config file
    config = load_config()
    return config.get("demo_mode", False)


def set_demo_mode(enabled: bool) -> None:
    """Set demo mode in config file."""
    config = load_config()
    config["demo_mode"] = enabled
    save_config(config)
