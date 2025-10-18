"""TUI theme integration for Textual applications.

This module provides Treeline's custom theme using Textual's native Theme system,
and supports auto-discovery of user themes from ~/.treeline/themes/.
"""

import importlib.util
from pathlib import Path
from typing import Iterator

from textual.app import App
from textual.theme import Theme


def get_treeline_theme() -> Theme:
    """Get Treeline's custom dark theme with sage green colors.

    Returns:
        Textual Theme instance with Treeline branding
    """
    return Theme(
        name="treeline",
        primary="#44755a",  # Sage green
        secondary="#7C9885",  # Lighter sage
        accent="#75B58F",  # Accent green
        warning="#FBBF24",  # Warm yellow
        error="#F87171",  # Soft red
        success="#4A7C59",  # Forest green
        background="#1a1a1a",  # Dark background
        surface="#2a2a2a",  # Slightly lighter surface
        panel="#1f1f1f",  # Panel background
        foreground="#F9FAFB",  # Light text
        dark=True,
    )


def load_user_themes() -> Iterator[Theme]:
    """Load user-defined themes from ~/.treeline/themes/ directory.

    User themes should be Python files that define a `theme` variable
    containing a Textual Theme instance.

    Example user theme file (~/.treeline/themes/my_theme.py):
        from textual.theme import Theme

        theme = Theme(
            name="my-custom-theme",
            primary="#ff6b6b",
            dark=True,
        )

    Yields:
        Theme instances from user theme files
    """
    themes_dir = Path.home() / ".treeline" / "themes"

    if not themes_dir.exists():
        return

    for theme_file in themes_dir.glob("*.py"):
        if theme_file.name.startswith("_"):
            continue

        try:
            # Load the Python module
            spec = importlib.util.spec_from_file_location(
                f"user_theme_{theme_file.stem}", theme_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for a 'theme' variable
                if hasattr(module, "theme") and isinstance(module.theme, Theme):
                    yield module.theme

        except Exception:
            # Silently skip invalid theme files
            # TODO: Consider logging these failures
            continue


class ThemedApp(App):
    """Base class for Treeline TUI applications with consistent theming.

    All Treeline TUI modes should inherit from this class to ensure:
    - Treeline custom theme is available
    - User custom themes from ~/.treeline/themes/ are auto-discovered
    - Access to Textual's built-in theme picker (Ctrl+\\ or Ctrl+P)

    The default theme is set to "treeline" but users can switch via
    the command palette.

    Example:
        class AnalysisApp(ThemedApp):
            TITLE = "Analysis Mode"

            def on_mount(self) -> None:
                self.push_screen(AnalysisScreen())
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Register Treeline custom theme
        self.register_theme(get_treeline_theme())

        # Auto-discover and register user themes
        for user_theme in load_user_themes():
            self.register_theme(user_theme)

        # Set default theme to Treeline
        self.theme = "treeline"
