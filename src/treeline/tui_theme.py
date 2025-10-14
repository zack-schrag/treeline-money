"""TUI theme integration for Textual applications.

This module bridges Treeline's theme system with Textual's CSS styling,
providing a consistent look and feel across all TUI modes.
"""

from textual.app import App

from treeline.theme import Theme, get_theme


def generate_textual_css(theme: Theme) -> str:
    """Generate Textual CSS from Treeline theme.

    Args:
        theme: Treeline theme instance

    Returns:
        CSS string for Textual apps
    """
    # Parse colors to extract hex values (remove 'bold', 'dim', etc.)
    def parse_color(color_str: str) -> str:
        """Extract hex color or color name from theme string."""
        if "#" in color_str:
            # Extract hex code
            parts = color_str.split()
            for part in parts:
                if part.startswith("#"):
                    return part
        # Return as-is if no hex (might be named color or modifier)
        return color_str.split()[0] if " " in color_str else color_str

    primary = parse_color(theme.primary)
    success = parse_color(theme.success)
    error = parse_color(theme.error)
    warning = parse_color(theme.warning)
    info = parse_color(theme.info)
    neutral = parse_color(theme.neutral)
    muted = parse_color(theme.muted)

    return f"""
    /* Treeline TUI Theme - CSS Variables */

    /* Color palette from theme */
    $primary: {primary};
    $success: {success};
    $error: {error};
    $warning: {warning};
    $accent: {info};

    /* Backgrounds */
    $background: #1a1a1a;
    $surface: #2a2a2a;
    $panel: #1f1f1f;

    /* Text colors */
    $text: {neutral};
    $text-muted: {muted};
    $text-disabled: #6b6b6b;

    /* Border colors */
    $border: {primary};
    $border-accent: {info};

    /* Default text styling */
    Screen {{
        background: $background;
        color: $text;
    }}

    /* Headers */
    Header {{
        background: $primary;
        color: $background;
    }}

    Footer {{
        background: $panel;
    }}

    /* Containers with borders */
    Container {{
        background: $panel;
    }}

    /* Data table styling */
    DataTable {{
        background: $surface;
        color: $text;
    }}

    DataTable > .datatable--cursor {{
        background: $primary 20%;
    }}

    DataTable > .datatable--header {{
        background: $panel;
        color: $accent;
        text-style: bold;
    }}

    /* Text editor styling */
    TextArea {{
        background: $surface;
        color: $text;
    }}

    TextArea:focus {{
        border: solid $primary;
    }}

    /* Button styling */
    Button {{
        background: $panel;
        color: $text;
        border: solid $border;
    }}

    Button:hover {{
        background: $primary;
        color: $background;
    }}

    Button.-primary {{
        background: $primary;
        color: $background;
    }}

    Button.-primary:hover {{
        background: $success;
    }}

    /* Input styling */
    Input {{
        background: $surface;
        color: $text;
        border: solid $border;
    }}

    Input:focus {{
        border: solid $accent;
    }}

    /* Static content styling */
    Static {{
        color: $text;
    }}

    .error {{
        color: $error;
    }}

    .success {{
        color: $success;
    }}

    .warning {{
        color: $warning;
    }}

    .muted {{
        color: $text-muted;
    }}
    """


class ThemedApp(App):
    """Base class for Treeline TUI applications with consistent theming.

    All Treeline TUI modes should inherit from this class to ensure
    consistent look and feel across the application.

    Example:
        class AnalysisApp(ThemedApp):
            TITLE = "Analysis Mode"

            def on_mount(self) -> None:
                self.push_screen(AnalysisScreen())
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply theme CSS
        theme = get_theme()
        self.theme_css = generate_textual_css(theme)

    @property
    def CSS(self) -> str:
        """Return combined theme + app-specific CSS."""
        # Combine theme CSS with any app-specific CSS
        app_css = getattr(super(), 'CSS', '')
        return self.theme_css + "\n" + app_css
