# Custom Themes for Treeline TUI

Treeline's TUI (Text User Interface) modes support custom themes using Textual's native theming system.

## Available Built-in Themes

Treeline comes with access to these themes:
- **treeline** (default) - Sage green theme inspired by nature
- **textual-dark** - Textual's default dark theme
- **textual-light** - Textual's light theme
- **nord** - Popular Nordic-inspired theme
- **dracula** - Dark theme with purple accents
- **gruvbox** - Retro groove color scheme
- **catppuccin-mocha** - Warm dark theme
- **catppuccin-latte** - Warm light theme
- **tokyo-night** - Dark theme inspired by Tokyo nights
- **monokai** - Classic monokai color scheme
- **solarized-light** - Popular light theme
- **flexoki** - Modern neutral theme

## Switching Themes

While in any TUI mode (analysis, tag, queries, charts), you can switch themes using the command palette:

1. Press `Ctrl+\` (or `Ctrl+P`) to open the command palette
2. Type "theme" to filter commands
3. Select "Change theme"
4. Choose your desired theme from the list

The theme change applies immediately and persists for the current session.

## Creating Custom Themes

You can create your own custom themes by placing Python files in `~/.treeline/themes/`.

### Step 1: Create the themes directory

```bash
mkdir -p ~/.treeline/themes
```

### Step 2: Create a theme file

Create a Python file (e.g., `~/.treeline/themes/my_theme.py`):

```python
"""My custom Treeline theme."""
from textual.theme import Theme

theme = Theme(
    name="my-custom-theme",
    primary="#FF6B6B",      # Main accent color
    secondary="#FFA07A",    # Secondary accent
    accent="#FFD93D",       # Additional accent
    warning="#F4A460",      # Warning color
    error="#DC143C",        # Error color
    success="#98D8C8",      # Success color
    background="#1a1a1a",   # Background color
    surface="#2a2a2a",      # Surface color
    panel="#1f1f1f",        # Panel background
    foreground="#F9FAFB",   # Text color
    dark=True,              # Dark or light theme
)
```

### Step 3: Restart Treeline TUI

Your custom theme will be automatically discovered and added to the theme list when you next launch a TUI mode.

## Theme Parameters

When creating a theme, you can customize these colors:

- **primary** (required) - Main brand/accent color
- **secondary** - Secondary accent color
- **accent** - Additional accent for highlights
- **warning** - Warning state color
- **error** - Error state color
- **success** - Success state color
- **background** - Main background color
- **surface** - Surface/container background
- **panel** - Panel background color
- **foreground** - Main text color
- **boost** - Boost/emphasis color
- **dark** - Boolean indicating if theme is dark (default: True)

Textual automatically generates color variations and CSS variables from these base colors.

## Tips for Theme Design

1. **Start with primary** - This is the only required color. Textual will generate others if not specified.
2. **Use hex colors** - Format as `"#RRGGBB"` for consistency
3. **Test contrast** - Ensure text is readable on backgrounds
4. **Consider dark mode** - Set `dark=True` for dark themes, `dark=False` for light themes
5. **Reference existing themes** - Look at Textual's built-in themes for inspiration

## Example Themes

### Warm Sunset Theme

```python
from textual.theme import Theme

theme = Theme(
    name="sunset",
    primary="#FF6B6B",
    secondary="#FFA07A",
    accent="#FFD93D",
    dark=True,
)
```

### Cool Ocean Theme

```python
from textual.theme import Theme

theme = Theme(
    name="ocean",
    primary="#4A90E2",
    secondary="#50C8E8",
    accent="#7ED3ED",
    success="#98D8C8",
    dark=True,
)
```

### Light Professional Theme

```python
from textual.theme import Theme

theme = Theme(
    name="professional-light",
    primary="#2563EB",
    secondary="#7C3AED",
    background="#FFFFFF",
    surface="#F9FAFB",
    panel="#F3F4F6",
    foreground="#111827",
    dark=False,
)
```

## Troubleshooting

**Theme not appearing in list:**
- Ensure the file is in `~/.treeline/themes/`
- Verify the file has a `.py` extension
- Check that the file defines a variable named `theme`
- Make sure the `theme` variable is a Textual `Theme` instance
- Restart the TUI application

**Theme looks broken:**
- Verify all hex colors are properly formatted (`#RRGGBB`)
- Check that `dark` is set correctly (True/False)
- Try setting more color parameters explicitly instead of relying on auto-generation

**Invalid theme file:**
- Treeline silently skips invalid theme files
- Check for Python syntax errors in your theme file
- Ensure you've imported `Theme` from `textual.theme`

## Resources

- [Textual Theme Documentation](https://textual.textualize.io/guide/design/)
- [Color Picker Tool](https://colorpicker.me/)
- [Coolors Color Scheme Generator](https://coolors.co/)
