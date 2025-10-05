# PyPlot: A Python Port of YouPlot for Terminal Visualization

## Executive Summary

This document explores creating **PyPlot** - a Python-native port of YouPlot's core visualization capabilities, optimized for Treeline's use case. Instead of bundling Ruby binaries or executing shell commands, we'd have a clean Python API that works directly with DuckDB result sets.

## Why Port YouPlot?

### Current State Analysis

**YouPlot strengths:**
- Beautiful Unicode rendering (box drawing, braille dots)
- Clean, professional output
- Proven DuckDB integration via pipe
- Simple bar, line, scatter, histogram support

**Plotext weaknesses (observed in testing):**
- Poor rendering even with 'clear' theme
- ANSI escape code issues in some terminals
- Less aesthetic output
- Not designed for data piping workflows

**Why not bundle youplot binary:**
- ~15-20MB per platform
- Need Ruby runtime or standalone packaging
- Shell command execution complexity
- Multi-platform binary maintenance

### The Opportunity

YouPlot is actually a thin wrapper around `unicode_plot.rb`. The architecture is:
```
youplot (CLI tool, ~500 LOC)
  ├── DSV parsing (CSV/TSV input)
  ├── Parameter handling
  └── unicode_plot.rb (core rendering, ~2400 LOC)
      ├── Canvas implementations (Braille, Block, ASCII)
      ├── Plot types (Bar, Line, Scatter, Histogram, Box)
      └── Unicode box drawing
```

**Key insight:** We can port the core rendering logic (~2400 LOC Ruby → ~2000 LOC Python) and create a better API for our use case.

## Proposed Architecture

### PyPlot: Python-Native API

```python
from pyplot import barplot, lineplot, histogram, scatterplot

# Direct integration with DuckDB
result = conn.execute("SELECT week, SUM(amount) FROM ...").fetchall()
labels = [row[0] for row in result]
values = [row[1] for row in result]

# Clean API - no shell commands, no piping
chart = barplot(
    labels=labels,
    values=values,
    title="Weekly Spending",
    xlabel="Week",
    width=60,
    color="green"
)

# Returns string ready to print
print(chart.render())
```

### Key Differences from YouPlot

| Feature | YouPlot | PyPlot |
|---------|---------|--------|
| **Input** | Piped CSV/TSV via stdin | Python lists/arrays directly |
| **Runtime** | Ruby gem + shell exec | Pure Python package |
| **API** | CLI tool only | Library-first with optional CLI |
| **DuckDB** | Shell pipe: `duckdb \| uplot` | Native: `conn.execute().fetchall()` |
| **Platform** | Requires Ruby or binary bundle | pip install, works everywhere |
| **Size** | ~1MB gem or ~20MB binary | ~200KB pure Python |

## Technical Deep Dive

### Core Components to Port

#### 1. Canvas System (~600 LOC)

The foundation - renders pixels to Unicode characters.

**BrailleCanvas** - High resolution using braille dots (2×4 pixels per char):
```ruby
# Unicode braille: U+2800 to U+28FF
# Each character represents 8 dots in 2x4 grid
BRAILLE_SIGNS = [
  [0x2801, 0x2802, 0x2804, 0x2840],  # Left column dots
  [0x2808, 0x2810, 0x2820, 0x2880]   # Right column dots
]

def pixel!(pixel_x, pixel_y, color)
  # Map pixel coordinate to character cell
  char_x = pixel_x / 2
  char_y = pixel_y / 4

  # Calculate dot position within character
  dot_x = pixel_x % 2
  dot_y = pixel_y % 4

  # Set the appropriate braille dot
  @grid[char_y][char_x] |= BRAILLE_SIGNS[dot_x][dot_y]
end
```

**Python equivalent:**
```python
class BrailleCanvas:
    """High-res canvas using Unicode braille (2×4 pixels per char)."""

    BRAILLE_BASE = 0x2800
    BRAILLE_DOTS = [
        [0x01, 0x02, 0x04, 0x40],  # Left column
        [0x08, 0x10, 0x20, 0x80]   # Right column
    ]

    def __init__(self, width: int, height: int):
        # Each char = 2×4 pixels
        self.width = width
        self.height = height
        self.grid = [[0x2800] * width for _ in range(height)]
        self.colors = [[None] * width for _ in range(height)]

    def pixel(self, x: int, y: int, color: str = None) -> None:
        """Set a pixel in the canvas."""
        char_x = x // 2
        char_y = y // 4
        dot_x = x % 2
        dot_y = y % 4

        # Combine braille dots using bitwise OR
        self.grid[char_y][char_x] |= self.BRAILLE_DOTS[dot_x][dot_y]
        if color:
            self.colors[char_y][char_x] = color

    def render(self) -> str:
        """Render canvas to string."""
        lines = []
        for y in range(self.height):
            line = ''.join(chr(self.grid[y][x]) for x in range(self.width))
            lines.append(line)
        return '\n'.join(lines)
```

**BlockCanvas** - Lower res using block characters (▀▄█):
```python
class BlockCanvas:
    """Medium-res canvas using block drawing characters."""

    BLOCKS = {
        (False, False): ' ',
        (True, False): '▀',  # Upper half
        (False, True): '▄',  # Lower half
        (True, True): '█'    # Full block
    }

    # 1×2 pixels per character
    # Similar implementation to BrailleCanvas
```

#### 2. Barplot Implementation (~200 LOC)

Horizontal bars with Unicode box drawing:

```ruby
# Current YouPlot implementation
def barplot(labels, heights, width:, color:, symbol: '■')
  max_val = heights.max
  max_label_len = labels.map(&:length).max

  labels.zip(heights).map do |label, value|
    # Calculate bar width proportional to value
    bar_width = (value / max_val * available_width).round
    bar = symbol * bar_width

    # Format: "    Label ┤■■■■■■ 123.45"
    "#{label.rjust(max_label_len)} ┤#{colorize(bar, color)} #{value}"
  end
end
```

**Python implementation with improvements:**
```python
class Barplot:
    """Horizontal bar chart with Unicode box drawing."""

    def __init__(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        width: int = 60,
        color: str = "green",
        symbol: str = "■"
    ):
        self.labels = labels
        self.values = values
        self.title = title
        self.xlabel = xlabel
        self.width = width
        self.color = color
        self.symbol = symbol

    def render(self) -> str:
        """Render the barplot as a string."""
        max_val = max(self.values)
        max_label_len = max(len(label) for label in self.labels)

        # Calculate bar width
        available_width = self.width - max_label_len - 10

        lines = []

        # Title
        if self.title:
            lines.append(f"  {self.title}")
            lines.append("")

        # Top border
        lines.append(f"  {' ' * max_label_len} ┌{'─' * available_width}┐")

        # Bars
        for label, value in zip(self.labels, self.values):
            bar_len = int((value / max_val) * available_width)
            bar = self.symbol * bar_len

            # Apply color if terminal supports it
            if self.color and sys.stdout.isatty():
                bar = self._colorize(bar, self.color)

            line = f"  {label:>{max_label_len}} ┤{bar} {value}"
            lines.append(line)

        # Bottom border
        lines.append(f"  {' ' * max_label_len} └{'─' * available_width}┘")

        # X-label
        if self.xlabel:
            padding = (self.width - len(self.xlabel)) // 2
            lines.append(f"{' ' * padding}{self.xlabel}")

        return '\n'.join(lines)

    @staticmethod
    def _colorize(text: str, color: str) -> str:
        """Apply ANSI color codes."""
        colors = {
            'green': '\033[32m',
            'blue': '\033[34m',
            'red': '\033[31m',
            'yellow': '\033[33m',
            'cyan': '\033[36m',
            'magenta': '\033[35m',
        }
        reset = '\033[0m'
        return f"{colors.get(color, '')}{text}{reset}"
```

#### 3. Lineplot Implementation (~300 LOC)

Uses BrailleCanvas for smooth curves:

```python
class Lineplot:
    """Line plot using braille canvas for smooth curves."""

    def __init__(
        self,
        x: List[float],
        y: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        width: int = 60,
        height: int = 20,
        color: str = "blue"
    ):
        self.x = x
        self.y = y
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.width = width
        self.height = height
        self.color = color

    def render(self) -> str:
        """Render line plot using braille canvas."""
        # Create canvas (each char = 2×4 pixels)
        canvas = BrailleCanvas(self.width, self.height)

        # Scale data to canvas coordinates
        x_min, x_max = min(self.x), max(self.x)
        y_min, y_max = min(self.y), max(self.y)

        pixel_width = self.width * 2
        pixel_height = self.height * 4

        # Plot points
        for i in range(len(self.x)):
            # Scale to pixel coordinates
            px = int((self.x[i] - x_min) / (x_max - x_min) * pixel_width)
            py = int((self.y[i] - y_min) / (y_max - y_min) * pixel_height)
            canvas.pixel(px, py, self.color)

            # Draw line to next point
            if i < len(self.x) - 1:
                next_px = int((self.x[i+1] - x_min) / (x_max - x_min) * pixel_width)
                next_py = int((self.y[i+1] - y_min) / (y_max - y_min) * pixel_height)
                self._draw_line(canvas, px, py, next_px, next_py)

        # Render canvas and add borders/labels
        return self._add_frame(canvas.render())

    @staticmethod
    def _draw_line(canvas, x0, y0, x1, y1):
        """Bresenham's line algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            canvas.pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
```

#### 4. Additional Plot Types

**Histogram** (~150 LOC) - Bin data and render as vertical bars
**Scatterplot** (~100 LOC) - BrailleCanvas with different symbols
**Boxplot** (~200 LOC) - Statistical box-and-whisker plots

### Estimated Port Effort

| Component | Ruby LOC | Python LOC | Complexity | Time Estimate |
|-----------|----------|------------|------------|---------------|
| Canvas system | 600 | 500 | Medium | 2-3 days |
| Barplot | 200 | 180 | Low | 1 day |
| Lineplot | 300 | 250 | Medium | 2 days |
| Histogram | 150 | 130 | Low | 1 day |
| Scatterplot | 100 | 80 | Low | 1 day |
| Box drawing utils | 200 | 150 | Low | 1 day |
| Color/styling | 150 | 120 | Low | 1 day |
| Tests | 800 | 700 | Medium | 3 days |
| **Total** | **2500** | **2110** | - | **12-15 days** |

## API Design for Treeline Integration

### Current Plotext Approach (Being Replaced)
```python
# Tool: execute_python
# Agent writes arbitrary code - too flexible, error-prone
code = """
result = conn.execute("SELECT ...").fetchall()
# ... data munging ...
plt.bar(x, y)
plt.show()
"""
```

### Proposed PyPlot Approach

**Option A: Simple Tool (Recommended)**
```python
# Tool: create_chart
{
    "name": "create_chart",
    "input_schema": {
        "sql": "SELECT week, SUM(amount) FROM transactions GROUP BY week",
        "chart_type": "bar",  # bar, line, scatter, histogram
        "title": "Weekly Spending",
        "x_column": 0,  # Which column is X axis
        "y_column": 1,  # Which column is Y axis
        "xlabel": "Week",
        "ylabel": "Amount ($)"
    }
}

# Implementation
async def _create_chart(self, tool_input: Dict[str, Any]) -> str:
    sql = tool_input["sql"]
    chart_type = tool_input["chart_type"]

    # Execute query
    result = conn.execute(sql).fetchall()

    # Extract columns
    x_col = tool_input.get("x_column", 0)
    y_col = tool_input.get("y_column", 1)

    x_data = [row[x_col] for row in result]
    y_data = [row[y_col] for row in result]

    # Create chart
    if chart_type == "bar":
        chart = barplot(
            labels=x_data,
            values=y_data,
            title=tool_input.get("title", ""),
            xlabel=tool_input.get("xlabel", ""),
            width=70
        )
    elif chart_type == "line":
        chart = lineplot(
            x=x_data,
            y=y_data,
            title=tool_input.get("title", ""),
            xlabel=tool_input.get("xlabel", ""),
            ylabel=tool_input.get("ylabel", "")
        )

    return chart.render()
```

**Option B: Hybrid Approach**
```python
# Keep simple tool for 80% of cases
# Add execute_python for complex visualizations (multiple series, etc.)

# Most queries use simple tool:
create_chart(sql="...", chart_type="bar", ...)

# Complex cases fall back to code:
execute_python("""
from pyplot import lineplot

result = conn.execute("SELECT week, revenue, expenses FROM ...").fetchall()
weeks = [r[0] for r in result]
revenue = [r[1] for r in result]
expenses = [r[2] for r in result]

# Multiple lines on same plot
chart = lineplot(weeks, revenue, title="Cash Flow", color="green")
chart.add_series(weeks, expenses, color="red")
print(chart.render())
""")
```

## Advantages Over Current Approach

### 1. **Better Visual Quality**
- Unicode box drawing (┌─┐│└┘┤├)
- Braille dots for smooth curves (⠀⠁⠂⠃⠄⠅⠆⠇)
- Professional appearance
- Proven rendering in terminals

### 2. **Cleaner Integration**
```python
# Before (plotext + execute_python)
- Agent writes arbitrary Python code
- Need to capture stdout
- Error handling complex
- Security concerns with exec()

# After (pyplot + simple tool)
- Structured tool input
- Direct return value
- Clear error messages
- Type-safe parameters
```

### 3. **Better Error Messages**
```python
# Plotext error
"Date Form should be: %d/%m/%Y"  # Cryptic

# PyPlot error
"Chart Error: X-axis data contains datetime objects.
Please format dates as strings before plotting.
Example: [d.strftime('%Y-%m-%d') for d in dates]"
```

### 4. **Optimized for Our Use Case**
- Designed for DuckDB result sets
- Automatic date/number formatting
- Smart axis labeling
- Treeline color scheme built-in

### 5. **Platform Independence**
```bash
# No external dependencies
pip install pyplot

# vs youplot bundling
- Need Ruby runtime OR
- Bundle 20MB binary per platform OR
- Require system install
```

## Project Structure

```
pyplot/
├── pyplot/
│   ├── __init__.py
│   ├── canvas/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract canvas
│   │   ├── braille.py       # BrailleCanvas (2×4 pixels/char)
│   │   ├── block.py         # BlockCanvas (▀▄█)
│   │   └── ascii.py         # AsciiCanvas (fallback)
│   ├── plots/
│   │   ├── __init__.py
│   │   ├── base.py          # Base plot class
│   │   ├── bar.py           # Barplot
│   │   ├── line.py          # Lineplot
│   │   ├── scatter.py       # Scatterplot
│   │   ├── histogram.py     # Histogram
│   │   └── box.py           # Boxplot
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── colors.py        # ANSI color handling
│   │   ├── unicode.py       # Box drawing characters
│   │   └── scaling.py       # Data scaling utilities
│   └── api.py               # High-level API (barplot, lineplot, etc.)
├── tests/
│   ├── test_canvas.py
│   ├── test_barplot.py
│   ├── test_lineplot.py
│   └── fixtures/
├── examples/
│   ├── basic_bar.py
│   ├── time_series.py
│   └── multi_series.py
├── pyproject.toml
├── README.md
└── LICENSE (MIT)
```

## Next Steps

### Phase 1: Proof of Concept (3-4 days)
1. Implement BrailleCanvas core
2. Create basic barplot
3. Test with DuckDB result sets
4. Compare output quality to youplot

### Phase 2: Core Features (5-6 days)
1. Complete canvas implementations
2. Add lineplot, histogram, scatter
3. Implement styling and colors
4. Write comprehensive tests

### Phase 3: Treeline Integration (2-3 days)
1. Create `create_chart` tool
2. Update AnthropicProvider to use pyplot
3. Update system prompt
4. Test with real queries

### Phase 4: Polish & Release (2-3 days)
1. Documentation
2. Example gallery
3. PyPI package
4. Announce as standalone project

**Total: 12-16 days of focused development**

## Open Questions

1. **Project ownership:** Separate repo under your GitHub or Treeline org?
2. **Naming:** `pyplot`, `termplot`, `uniplot`, `chartplot`?
3. **License:** MIT to match youplot?
4. **Scope:** Start with bar/line only, or implement all plot types?
5. **CLI:** Include CLI tool like youplot, or library-only initially?

## Conclusion

Porting YouPlot to Python as **PyPlot** is a **12-15 day investment** that gives us:

✅ Beautiful terminal charts (proven quality)
✅ Clean Python API (no shell commands)
✅ Perfect DuckDB integration
✅ Platform independent (pure Python)
✅ Reusable open source project
✅ Better error messages and UX
✅ Type safety and IDE support

The core rendering logic is ~2400 LOC of straightforward Ruby that translates cleanly to Python. The YouPlot maintainers have already solved the hard problems (braille rendering, Unicode box drawing, terminal compatibility). We just need to port it and create a better API for our use case.

**Recommendation:** Proceed with Phase 1 proof of concept. If the barplot rendering matches youplot quality, commit to the full port.
