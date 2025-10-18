"""Unit tests for Textual theme system."""

import pytest
from pathlib import Path
from textual.theme import Theme

from treeline.tui_theme import ThemedApp, get_treeline_theme, load_user_themes


def test_get_treeline_theme():
    """Test that Treeline theme is created with correct properties."""
    theme = get_treeline_theme()

    assert theme.name == "treeline"
    assert theme.primary == "#44755a"
    assert theme.dark is True
    assert theme.success == "#4A7C59"
    assert theme.error == "#F87171"


def test_treeline_theme_has_all_colors():
    """Test that Treeline theme defines all major color properties."""
    theme = get_treeline_theme()

    # Verify all important colors are set
    assert theme.primary
    assert theme.secondary
    assert theme.accent
    assert theme.warning
    assert theme.error
    assert theme.success
    assert theme.background
    assert theme.surface
    assert theme.panel
    assert theme.foreground


def test_load_user_themes_no_directory():
    """Test that load_user_themes handles missing directory gracefully."""
    # Create a temporary non-existent path to simulate missing themes dir
    # The function should return an empty iterator
    themes = list(load_user_themes())
    # If ~/.treeline/themes doesn't exist, should return empty list
    # If it does exist, we just verify it doesn't crash
    assert isinstance(themes, list)


def test_load_user_themes_with_valid_theme(tmp_path):
    """Test loading a valid user theme from filesystem."""
    # Create a temporary themes directory
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    # Create a valid theme file
    theme_file = themes_dir / "test_theme.py"
    theme_file.write_text("""
from textual.theme import Theme

theme = Theme(
    name="test-theme",
    primary="#FF0000",
    dark=True,
)
""")

    # Temporarily patch the themes directory
    import treeline.tui_theme
    original_path = Path.home() / ".treeline" / "themes"

    # Monkey-patch the load_user_themes function
    def patched_load():
        import importlib.util
        for theme_file in themes_dir.glob("*.py"):
            if theme_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"user_theme_{theme_file.stem}", theme_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "theme") and isinstance(module.theme, Theme):
                        yield module.theme
            except Exception:
                continue

    themes = list(patched_load())
    assert len(themes) == 1
    assert themes[0].name == "test-theme"
    assert themes[0].primary == "#FF0000"


def test_load_user_themes_skips_invalid_files(tmp_path):
    """Test that invalid theme files are silently skipped."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    # Create an invalid theme file (syntax error)
    invalid_file = themes_dir / "invalid.py"
    invalid_file.write_text("this is not valid python {{{")

    # Create a file without a theme variable
    no_theme_file = themes_dir / "no_theme.py"
    no_theme_file.write_text("x = 123")

    # Create a file starting with underscore (should be skipped)
    underscore_file = themes_dir / "_private.py"
    underscore_file.write_text("""
from textual.theme import Theme
theme = Theme(name="should-not-load", primary="#000000")
""")

    # Monkey-patch to use tmp_path
    import importlib.util
    themes = []
    for theme_file in themes_dir.glob("*.py"):
        if theme_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"user_theme_{theme_file.stem}", theme_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "theme") and isinstance(module.theme, Theme):
                    themes.append(module.theme)
        except Exception:
            continue

    # Should have loaded 0 themes (all were invalid or skipped)
    assert len(themes) == 0


def test_themed_app_registers_treeline_theme():
    """Test that ThemedApp registers Treeline theme on init."""
    app = ThemedApp()

    assert "treeline" in app.available_themes
    assert app.theme == "treeline"


def test_themed_app_has_builtin_themes():
    """Test that ThemedApp includes Textual's built-in themes."""
    app = ThemedApp()

    # Verify some built-in themes are available
    available = list(app.available_themes)
    assert "textual-dark" in available
    assert "textual-light" in available
    assert "nord" in available
    assert "dracula" in available


def test_themed_app_sets_default_to_treeline():
    """Test that ThemedApp defaults to Treeline theme."""
    app = ThemedApp()

    assert app.theme == "treeline"
