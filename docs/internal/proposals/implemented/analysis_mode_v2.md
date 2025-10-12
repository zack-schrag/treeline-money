# Proposal: Analysis Mode - Modal View Approach (v2)

**Status:** Proposed (Revised)
**Created:** 2025-10-11
**Author:** Human + Claude Code
**Replaces:** analysis_mode.md

## Revision Summary

**Original approach:** REPL-based with state machine navigation between SQL/Results/Chart modes
**New approach:** Full-screen modal view (similar to `/tag` mode) with integrated workspace

**Why the pivot:** The REPL approach was creating visibility problems and added complexity. A dedicated full-screen modal view provides:
- Visual continuity (all context visible at once)
- Proven UX pattern (like `/tag` mode)
- Simpler implementation (less state management)
- Better alignment with "IDE-like" vision

## Problem Statement

The current chart feature works but creates a rigid, friction-heavy workflow that doesn't match how users naturally analyze data. Key issues:

1. **Too Many Sequential Prompts**: After query execution, users face: "Save query?" → "Create chart?" → "Continue editing?" - death by a thousand clicks
2. **Broken Iterative Flow**: Real analysis is iterative (SQL → results → chart → tweak SQL → new chart → adjust), but current implementation is linear
3. **Disconnected Context**: Results disappear when you move to charting, SQL disappears when viewing results
4. **Missing Intelligence**: Common tasks like histogram bucketing require manual SQL transformation

## Vision Alignment

From PRFAQ.md:
> "Analyzing your personal data is a dynamic and iterative process, much like coding."

From landing_page.md:
> "Treeline feels more like a coding IDE than a traditional finance app"

Just like an IDE provides:
- Dedicated views (debug mode, interactive notebooks, REPL windows)
- Visual workspace with clear sections
- Context always visible

Treeline should provide:
- Focused tools (`/sql`, `/chart`, `/schema`) for quick tasks
- Integrated workspace (`/analysis` mode) for deep exploration

## Proposed Solution: `/analysis` Modal View

### Core Concept

A full-screen modal view (like `/tag` mode) that provides an integrated workspace with:
- **SQL editor** (bottom panel) - always visible, multiline input
- **Results table** (middle panel) - scrollable, always visible after execution
- **Chart display** (top panel) - appears when chart is created
- **Keyboard shortcuts** (header) - always visible, context-aware

### Modal View Layout

**Two-panel layout: Data view (top) + SQL editor (bottom)**

The data panel toggles between Results view and Chart view using Tab key.

#### Results View
```
┌────────────────────────────────────────────────────────────────┐
│ Analysis Mode    [F5] execute [c]hart [s]ave [r]eset [q]uit   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ Results (100 rows) ───────────────────── [↑↓] scroll ─────┐│
│ │ month      amount      category                            ││
│ │ ─────────────────────────────────────────────────────      ││
│ │ Jan        $456.78     dining                              ││
│ │ Jan        $892.50     rent                                ││
│ │ Feb        $423.45     dining                              ││
│ │ Feb        $892.50     rent                                ││
│ │ Mar        $398.23     dining                              ││
│ │ ...                                                         ││
│ │                                                             ││
│ │                 [Tab] view chart                           ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─ SQL ─────────────────────────────────────── [F5] execute ─┐│
│ │ SELECT                                                      ││
│ │   DATE_TRUNC('month', date) as month,                      ││
│ │   SUM(amount) as amount,                                   ││
│ │   category                                                 ││
│ │ FROM transactions                                          ││
│ │ WHERE date > '2024-01-01'                                  ││
│ │ GROUP BY month, category                                   ││
│ │ ORDER BY month█                                            ││
│ └─────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

#### Chart View (after pressing Tab)
```
┌────────────────────────────────────────────────────────────────┐
│ Analysis Mode    [F5] execute [s]ave chart [r]eset [q]uit     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ Chart: Monthly Spending Trend ────────────────────────────┐│
│ │                                                             ││
│ │    $500 │     ╭─╮                                          ││
│ │    $400 │   ╭─╯ ╰─╮                                        ││
│ │    $300 │ ╭─╯     ╰─╮                                      ││
│ │         └─────────────                                      ││
│ │          Jan Feb Mar                                        ││
│ │                                                             ││
│ │                                                             ││
│ │                 [Tab] view results                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─ SQL ─────────────────────────────────────── [F5] execute ─┐│
│ │ SELECT                                                      ││
│ │   DATE_TRUNC('month', date) as month,                      ││
│ │   SUM(amount) as amount,                                   ││
│ │   category                                                 ││
│ │ FROM transactions                                          ││
│ │ WHERE date > '2024-01-01'                                  ││
│ │ GROUP BY month, category                                   ││
│ │ ORDER BY month█                                            ││
│ └─────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### Key Features

**1. Always-Visible SQL**
- SQL editor always at bottom (edit anytime)
- Data panel at top toggles between results and chart
- Clean, uncluttered view - no overlapping panels

**2. Keyboard-Driven Navigation**
- `F5` - Execute SQL query
- `c` - Create chart from results
- `Tab` - Toggle between results view and chart view
- `s` - Save current query (or save chart when viewing chart)
- `r` - Reset (clear results and chart)
- `q` - Quit analysis mode
- `↑↓` - Scroll through results (when in results view)

**3. State Persistence**
- Query text persists until reset
- Results persist until new query or reset
- Chart persists until reset
- Both results and chart stay in memory - just toggle view with Tab

**4. Iterative Workflow**
```
1. User types SQL → F5 to execute
2. Results appear in data panel
3. User reviews, decides to chart → press 'c'
4. Chart wizard prompts for config (inline)
5. Chart replaces results in data panel
6. User can Tab back to see results data
7. User edits SQL → F5 → chart auto-updates with new data
8. Iterate: tweak SQL → F5 → Tab to chart → repeat
9. Satisfied → 's' to save query or chart
```

### Command Responsibilities (Refined)

**`/sql`** - Quick SQL Execution
- Focused, single-purpose
- Execute → View results → Optional chart → Done
- For users who want quick answers
- Simplified post-execution menu (already implemented in Task 01)

**`/chart`** - Chart Library Browser
- Browse/run saved charts
- View chart configs
- Quick chart execution
- Not a builder/editor

**`/analysis`** - Integrated Workspace (NEW)
- Full-screen modal view
- Persistent SQL/Results/Chart context
- For exploratory, iterative analysis
- Primary tool for "building up" insights

### User Experience Flow

#### Scenario: Exploratory Analysis Session

```bash
> /analysis

[Full-screen modal view opens]

┌─────────────────────────────────────────────────────────┐
│ Analysis Mode    [F5] execute [c]hart [s]ave [q]uit    │
├─────────────────────────────────────────────────────────┤
│ ┌─ SQL ─────────────────────────────────────────────┐  │
│ │ █                                                  │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

User types:
SELECT amount, category
FROM transactions
WHERE date > '2024-01-01'
LIMIT 100

[F5]

┌─────────────────────────────────────────────────────────┐
│ Analysis Mode    [F5] execute [c]hart [s]ave [q]uit    │
├─────────────────────────────────────────────────────────┤
│ ┌─ Results (100 rows) ──────────────────────────────┐  │
│ │ amount     category                               │  │
│ │ $456.78    dining                                 │  │
│ │ $892.50    rent                                   │  │
│ │ ...                                               │  │
│ └───────────────────────────────────────────────────┘  │
│ ┌─ SQL ─────────────────────────────────────────────┐  │
│ │ SELECT amount, category                           │  │
│ │ FROM transactions                                 │  │
│ │ WHERE date > '2024-01-01'                         │  │
│ │ LIMIT 100█                                        │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

User presses 'c' for chart:

[Inline chart config appears - not full screen]
Chart type: [b]ar [l]ine [s]catter [h]istogram
> b

X column: category
Y column: amount
...

[Chart appears in top panel]

┌─────────────────────────────────────────────────────────┐
│ Analysis Mode    [F5] execute [r]eset [q]uit           │
├─────────────────────────────────────────────────────────┤
│ ┌─ Chart ──────────────── [a]djust [s]ave [x] close ┐  │
│ │ [Bar chart visualization]                          │  │
│ └────────────────────────────────────────────────────┘  │
│ ┌─ Results (100 rows) ──────────────────────────────┐  │
│ │ amount     category                               │  │
│ │ ...                                               │  │
│ └───────────────────────────────────────────────────┘  │
│ ┌─ SQL ─────────────────────────────────────────────┐  │
│ │ SELECT amount, category                           │  │
│ │ FROM transactions                                 │  │
│ │ WHERE date > '2024-01-01'                         │  │
│ │ LIMIT 100█                                        │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

User notices issue, edits SQL, presses F5 → new results + chart updates
User satisfied → 's' to save query
```

**Fluid, visual, iterative - everything visible at once.**

## Technical Architecture

### UI Implementation

**Leverage `/tag` mode patterns:**
```python
from rich.layout import Layout
from rich.panel import Panel

def render_analysis_view(session: AnalysisSession) -> Layout:
    """Render the full analysis modal view."""
    layout = Layout()

    # Split into sections
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="chart", size=0 if not session.chart else 15),
        Layout(name="results", ratio=2),
        Layout(name="sql", size=10),
    )

    layout["header"].update(Panel(_render_shortcuts(session)))

    if session.chart:
        layout["chart"].update(Panel(session.chart.display))

    if session.results:
        layout["results"].update(Panel(_render_results_table(session.results)))

    layout["sql"].update(Panel(_render_sql_editor(session.sql)))

    return layout
```

### State Management

**Simple dataclass (no complex state machine):**
```python
@dataclass
class AnalysisSession:
    """State for analysis mode session."""

    sql: str = ""
    results: QueryResult | None = None
    chart: ChartDisplay | None = None

    # Simple flags, no mode enum needed
    is_editing_chart: bool = False
```

### Event Handling

**Single event loop (like `/tag` mode):**
```python
def handle_analysis_mode():
    """Main analysis mode loop."""
    session = AnalysisSession()

    while True:
        # Render current state
        console.clear()
        console.print(render_analysis_view(session))

        # Get keypress
        key = readkey()

        # Handle based on context
        if key == "F5":
            session.results = execute_query(session.sql)
        elif key == "c" and session.results:
            session.chart = create_chart_wizard(session.results)
        elif key == "s":
            save_query(session.sql)
        elif key == "r":
            session = AnalysisSession()  # Reset
        elif key == "q":
            break
        # ... etc
```

## Implementation Phases

### Phase 1: Core Modal View ✅ (Partially Done)
- ✅ Task 01: Simplified `/sql` prompts (done, still valuable)
- Build analysis mode modal view layout
- SQL editor panel (multiline, always visible)
- Results panel (table display, scrollable)
- Basic keyboard shortcuts (F5, q)

### Phase 2: Chart Integration
- Chart panel (appears when created)
- Inline chart wizard (not full-screen)
- Chart adjustment controls
- Save chart functionality

### Phase 3: Smart Helpers
- Histogram bucketing helper
- Column type detection
- Auto-suggest chart types based on data

### Phase 4: Polish
- Saved query Tab completion within mode
- Better scrolling for large results
- Chart preview before full render
- Help overlay (press '?' for shortcuts)
- Documentation updates

## Success Metrics

1. **Visual Continuity**: All context (SQL, results, chart) visible simultaneously
2. **Reduced Friction**: No more "where did my results go?"
3. **Intuitive Flow**: Users understand the workspace without reading docs
4. **Leverages Existing Patterns**: Similar to `/tag` mode = less learning curve

## Advantages Over REPL Approach

| Aspect | REPL Approach | Modal View Approach |
|--------|---------------|---------------------|
| **Context visibility** | Results disappear between modes | Everything always visible |
| **State management** | Complex mode state machine | Simple dataclass |
| **User orientation** | "Where am I?" confusion | Clear visual sections |
| **Implementation** | New patterns to build | Leverage existing `/tag` code |
| **Learning curve** | New interaction model | Familiar pattern |
| **Debugging** | Prompt color issues, terminal quirks | Robust panel rendering |

## Decisions Made

1. ✅ **Chart auto-update**: When SQL is re-executed, chart automatically updates with new data (no prompt)
2. ✅ **Result set size**: No artificial limit - user can load as many rows as they want
3. ✅ **Session auto-save**: Not implementing for v1 - keep it simple, avoid unnecessary complexity

## Future Enhancements (Not in v1)

- Session auto-save/resume
- Chart adjustment controls (change colors, titles without recreating)
- Multiple charts from same query
- Export results to CSV
- Query history within analysis mode

## Risks & Mitigations

**Risk:** Full-screen view doesn't work well on small terminals
**Mitigation:** Min terminal size check, graceful degradation, fallback to `/sql`

**Risk:** Chart rendering in panel looks bad
**Mitigation:** Test chart libraries for ASCII/Rich compatibility, possibly external display

**Risk:** Users still confused about `/sql` vs `/analysis`
**Mitigation:** Clear documentation, landing page examples, helpful hints in both commands

## Recommendation

✅ **Proceed with modal view approach**

This is a better fit because:
1. ✅ Proven pattern (tag mode works well)
2. ✅ Simpler implementation (less state management)
3. ✅ Better UX (visual continuity)
4. ✅ Aligns with vision (IDE-like workspace)

Next steps:
1. Archive REPL-based task breakdown
2. Create new task breakdown for modal view approach
3. Start with Phase 1: Core modal view layout
