# TUI Theming Pattern

## Overview

All Treeline TUI applications use Textual with consistent theming based on the project's theme system (`theme.py` / `themes/default.json`). This ensures a uniform look and feel across all interactive modes.

## Architecture

```
theme.py (Theme class)
    ↓
themes/default.json (color definitions)
    ↓
tui_theme.py (ThemedApp base class)
    ↓ generates Textual CSS
analysis_textual.py (AnalysisApp extends ThemedApp)
tag_textual.py (future - TagApp extends ThemedApp)
queries_textual.py (future - QueriesApp extends ThemedApp)
```

## Implementation Pattern

### 1. Create TUI App Class

All TUI applications should inherit from `ThemedApp`:

```python
from treeline.tui_theme import ThemedApp

class MyTuiApp(ThemedApp):
    """My TUI application with consistent theming."""

    TITLE = "My Mode"

    def on_mount(self) -> None:
        """Initialize the app."""
        self.push_screen(MyMainScreen())
```

### 2. Use Theme Colors in CSS

The `ThemedApp` base class provides these CSS variables:

**Colors:**
- `$primary` - Primary brand color (sage green #44755a)
- `$success` - Success state (green #4A7C59)
- `$error` - Error state (red #F87171)
- `$warning` - Warning state (yellow #FBBF24)
- `$accent` - Accent color (cyan #7C9885)

**Backgrounds:**
- `$background` - Main background (#1a1a1a)
- `$surface` - Surface color (#2a2a2a)
- `$panel` - Panel color (#1f1f1f)

**Text:**
- `$text` - Primary text color
- `$text-muted` - Muted/dimmed text
- `$text-disabled` - Disabled state text

**Borders:**
- `$border` - Standard border (uses $primary)
- `$border-accent` - Accent border (uses $accent)

### 3. Example Screen with CSS

```python
from textual.screen import Screen
from textual.widgets import DataTable, TextArea, Static

class MyScreen(Screen):
    """Example screen using theme colors."""

    CSS = """
    MyScreen {
        background: $background;
    }

    #data_panel {
        border: solid $primary;
        background: $surface;
    }

    #error_message {
        color: $error;
        background: $panel;
    }

    .success {
        color: $success;
    }

    .muted {
        color: $text-muted;
    }
    """

    def compose(self):
        with Container(id="data_panel"):
            yield DataTable()
        yield Static("", id="error_message", classes="hidden")
```

## Benefits

1. **Consistency**: All TUI modes use the same color palette
2. **Maintainability**: Update theme once, applies everywhere
3. **Flexibility**: Easy to add new themes (e.g., light mode)
4. **Simplicity**: No need to hardcode colors in each TUI

## Color Palette Reference

Current default theme colors:

| Element | Hex | Usage |
|---------|-----|-------|
| Primary | #44755a | Headers, borders, highlights |
| Success | #4A7C59 | Success messages, positive actions |
| Error | #F87171 | Error messages, warnings |
| Warning | #FBBF24 | Warning messages |
| Accent | #7C9885 | Secondary highlights |
| Muted | #9CA3AF | Dimmed text, hints |
| Neutral | #F9FAFB | Primary text |

## Future Enhancements

- [ ] Support for light theme
- [ ] User-configurable themes
- [ ] Theme preview command
- [ ] Per-mode theme customization

## Migration Checklist

When creating a new TUI or migrating an existing one:

- [ ] Import `ThemedApp` from `treeline.tui_theme`
- [ ] Inherit from `ThemedApp` instead of `App`
- [ ] Use theme CSS variables in your Screen CSS
- [ ] Remove hardcoded colors
- [ ] Test with theme system to ensure colors are correct
