# Proposal: Analysis Mode for Fluid Data Exploration

**Status:** Proposed
**Created:** 2025-10-10
**Author:** Human + Claude Code

## Problem Statement

The current chart feature works but creates a rigid, friction-heavy workflow that doesn't match how users naturally analyze data. Key issues:

1. **Too Many Sequential Prompts**: After query execution, users face: "Save query?" → "Create chart?" → "Continue editing?" - death by a thousand clicks
2. **Broken Iterative Flow**: Real analysis is iterative (SQL → results → chart → tweak SQL → new chart → adjust), but current implementation is linear
3. **Disconnected Commands**: `/sql`, `/query`, and `/chart` feel like separate tools rather than parts of an integrated workspace
4. **Missing Intelligence**: Common tasks like histogram bucketing require manual SQL transformation

## Vision Alignment

From PRFAQ.md:
> "Analyzing your personal data is a dynamic and iterative process, much like coding."

From landing_page.md:
> "Treeline feels more like a coding IDE than a traditional finance app"

Just like an IDE provides:
- Focused tools (editor, terminal, debugger)
- Integrated workspace (debug mode, interactive sessions)

Treeline should provide:
- Focused tools (`/sql`, `/chart`, `/schema`)
- Integrated workspace (`/analysis` mode)

## Proposed Solution: `/analysis` Mode

### Core Concept

A dedicated analysis mode that maintains state and allows fluid movement between:
- SQL editing
- Result viewing
- Chart creation/adjustment
- Iteration and refinement

Think: Jupyter notebooks meets terminal, or debug mode in an IDE.

### Command Responsibilities (Refined)

**`/sql`** - Focused SQL Editor
- Clean, single-purpose SQL editing
- Chart creation is available but straightforward (not wizard-heavy)
- For users who want quick SQL → results → optional chart
- Simplified post-execution menu

**`/chart`** - Chart Library Browser
- Browse saved charts
- Run existing charts with fresh data
- Edit chart configs (opens in editor or prompts to use `/sql`)
- "New chart" option points users to `/sql` or `/analysis`
- Like a file browser, not an editor/builder

**`/analysis`** - Integrated Workspace (NEW)
- Stateful session (maintains SQL, results, chart state)
- Fluid navigation between modes (SQL → Results → Chart → SQL)
- Smart helpers (histogram bucketing, column suggestions)
- Primary mode for exploratory analysis
- Modal interface with clear state indicators

### User Experience Flow

#### Scenario 1: Quick Analysis in `/sql`
```bash
> /sql
>: SELECT amount, category FROM transactions WHERE amount > 100

[Results displayed]

Next? [c]hart [s]ave [e]dit [enter] continue
> c

Chart type: bar
X column: category
Y column: amount
Title (optional):
Color [green]:

[Chart displayed]

Save? [y/n]: y
Name: big_expenses
✓ Saved to ~/.treeline/charts/big_expenses.tl
```

**Simple, straightforward, one chart then done.**

#### Scenario 2: Exploratory Analysis in `/analysis`
```bash
> /analysis

╭──────────── Analysis Mode ────────────╮
│ Fluid workspace for data exploration  │
│                                        │
│ Tab - load saved query                 │
│ F5 - execute                           │
│ c - chart results                      │
│ e - edit SQL                           │
│ q - quit                               │
╰────────────────────────────────────────╯

SQL> SELECT amount FROM transactions
     WHERE date > '2024-01-01'
     ORDER BY amount DESC
     LIMIT 100

[F5]

╭───────── Results ─────────╮
│ 100 rows                  │
╰───────────────────────────╯

Results> [c]hart [e]dit [s]ave [q]uit
> c

Chart> histogram

Column: amount
✓ Detected range: $45.67 - $892.50

Buckets: [a]uto [c]ustom [m]anual
> c

Ranges: 0-100, 100-200, 200-300, 300-500, 500+

✓ Transforming query...

[Histogram displayed]

Chart> [a]djust [s]ave [e]dit SQL [b]ack [q]uit
> a

Adjust> [b]uckets [c]olor [t]itle
> b

Ranges: 0-50, 50-100, 100-200, 200-500, 500+

[Updated histogram displayed]

Chart> [s]ave [a]djust [e]dit SQL [q]uit
> e

SQL> [back to SQL editor with context preserved, can tweak query]
```

**Fluid, iterative, maintains state throughout.**

#### Scenario 3: Using `/chart` to Browse
```bash
> /chart

╭────── Saved Charts ──────╮
│                          │
│ • monthly_spending       │
│ • big_expenses           │
│ • category_breakdown     │
│                          │
╰──────────────────────────╯

Chart name (or Tab to browse): big_expenses

[Executes query, displays chart]

[r]un again [e]dit [d]elete [n]ew [q]uit
> e

Opening chart config:
  ~/.treeline/charts/big_expenses.tl

💡 To modify the chart, use /sql or /analysis mode

Press enter to continue...
```

**Chart browsing and management, clear path to editing.**

### Technical Architecture

#### State Management
```python
class AnalysisSession:
    """Maintains state for an analysis session."""

    sql: str | None = None
    results: QueryResult | None = None
    chart_config: ChartWizardConfig | None = None
    mode: Literal["sql", "results", "chart"] = "sql"
```

#### Modal Navigation
- **SQL Mode**: Editing SQL, Tab for saved queries, F5 to execute
- **Results Mode**: Viewing results, can move to chart or back to edit
- **Chart Mode**: Configuring chart, can adjust or save, can loop back to SQL

#### Smart Helpers

**Histogram Bucketing:**
```python
class HistogramHelper:
    """Helps users bucket numeric data for histograms."""

    def suggest_buckets(self, values: list[float]) -> list[tuple[float, float]]:
        """Auto-generate sensible bucket ranges."""

    def parse_custom_buckets(self, input: str) -> list[tuple[float, float]]:
        """Parse user input like '0-100, 100-200, 200+'"""

    def generate_bucketing_sql(self,
        original_sql: str,
        column: str,
        buckets: list[tuple[float, float]]
    ) -> str:
        """Transform SQL to bucket data."""
```

### Implementation Phases

**Phase 1: Simplify `/sql` Chart Integration**
- Replace multi-step prompts with single action menu
- Keep chart creation available but streamlined
- Remove "continue editing?" prompt (always loop back by default)

**Phase 2: Enhance `/chart` Command**
- Make it purely a browser/runner for saved charts
- Add "new chart" option that points to `/sql` or `/analysis`
- Clear messaging about where to edit/create

**Phase 3: Build `/analysis` Mode**
- Implement stateful session management
- Build modal navigation (SQL → Results → Chart)
- Create smart histogram bucketing helper
- Add autocomplete for queries/charts within mode

**Phase 4: Polish & Documentation**
- Visual state indicators
- Keyboard shortcut help
- Update landing page to showcase `/analysis`
- Migration guide for existing users

## Success Metrics

1. **Reduced Friction**: Number of prompts to create chart: 3+ → 1
2. **Fluid Iteration**: Can adjust chart without re-running full wizard
3. **Clear Responsibilities**: Users understand when to use `/sql` vs `/analysis` vs `/chart`
4. **Smart Assistance**: Histogram bucketing doesn't require manual SQL

## Open Questions

1. Should `/analysis` mode auto-save session state between invocations?
2. How do we handle very large result sets in memory during analysis session?
3. Should chart preview happen before full chart generation?
4. What's the escape hatch if user gets stuck in a mode?

## Risks & Mitigations

**Risk:** Users confused by yet another command
**Mitigation:** Clear documentation, landing page examples, helpful hints

**Risk:** Analysis mode becomes too complex
**Mitigation:** Start minimal, add features incrementally based on feedback

**Risk:** State management bugs
**Mitigation:** Simple state model, comprehensive tests, clear reset mechanism

## Alternatives Considered

### Alternative 1: Enhance `/sql` with all features
**Rejected:** Violates single responsibility, bloats `/sql` for purists

### Alternative 2: Make `/chart` do everything
**Rejected:** Doesn't match mental model of "chart library browser"

### Alternative 3: Status quo with minor tweaks
**Rejected:** Doesn't solve core flow problem, still rigid

## Recommendation

Proceed with `/analysis` mode implementation in phases:
1. Fix immediate friction in `/sql` (Phase 1)
2. Clarify `/chart` as browser (Phase 2)
3. Build `/analysis` as primary exploratory workspace (Phase 3)

This aligns with "IDE for personal finances" vision and enables the fluid, iterative workflow users need for real data analysis.
