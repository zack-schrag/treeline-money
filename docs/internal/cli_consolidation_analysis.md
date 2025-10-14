# CLI Tooling Consolidation Analysis

**Date:** 2025-10-12
**Objective:** Evaluate consolidating CLI dependencies from three libraries (Rich, Textual, prompt_toolkit) to one or two

---

## Current State

### Dependencies Installed
```toml
[dependencies]
prompt-toolkit>=3.0.52
rich>=14.1.0
textual>=6.2.1
```

### Actual Usage Analysis

**Rich** - HEAVILY USED (14 files):
- `Console`, `Table`, `Panel`, `Syntax` for formatted output
- `Prompt`, `Confirm` for simple interactive input
- Used across: cli.py, all command files, analysis.py

**prompt_toolkit** - MODERATELY USED (3 files, ~2,199 lines):
1. **cli.py** (~495 lines):
   - PromptSession for REPL with history
   - Custom completers for slash commands and file paths
   - Key bindings for command execution

2. **query.py** (~541 lines):
   - PromptSession for multiline SQL editor
   - Syntax highlighting with PygmentsLexer
   - SavedQueryCompleter for auto-completing saved queries
   - Custom key bindings (F5, Meta+Enter)

3. **analysis.py** (~1,163 lines) - **COMPLEX FULL TUI**:
   - Full-screen split-panel application (HSplit with 4 panels)
   - Multiple buffers (SQL editor, results display)
   - Complex key bindings with conditional filters (40+ bindings)
   - Focus management between panels
   - FormattedTextControl for custom rendering
   - Async query execution support
   - Multiple view modes: results, chart, wizard, save, browse, help
   - Bidirectional scrolling (horizontal columns, vertical rows)
   - Row selection with visual highlighting
   - **This is the crown jewel of the CLI - the most sophisticated feature**

**Textual** - **NEVER USED!**
- Installed as dependency
- Zero imports in codebase
- Pure bloat

---

## Library Capabilities Summary

### Rich (v14.1.0)
**Purpose:** Terminal output formatting and beautification

**Capabilities:**
- Beautiful text styling (colors, bold, italic, underline)
- Tables with flexible formatting and unicode borders
- Syntax highlighting via Pygments
- Progress bars, panels, markdown rendering
- Logging with timestamps
- NOT designed for full interactive TUI applications

**Limitations:**
- No key binding system
- No layout management for complex UIs
- No focus management between components
- Cannot build apps like analysis.py

### Textual (v6.2.1)
**Purpose:** Modern TUI framework (built by Textualize, same team as Rich)

**Capabilities:**
- Full TUI framework built on top of Rich
- CSS-like styling system
- Widget library (buttons, tables, TextArea, etc.)
- Layout engine (Horizontal, Vertical, Grid)
- Event-driven architecture with key bindings
- Async support built-in
- Mouse support
- Can deploy TUI apps to web browsers
- Reactive programming model
- Command palette (Ctrl+P)
- Dev console for debugging

**Key Features:**
- 16.7 million colors, smooth animations
- Modern web-inspired API
- Reusable components
- Cross-platform (macOS, Linux, Windows, SSH)

### prompt_toolkit (v3.0.52)
**Purpose:** Building interactive command-line and full-screen terminal applications

**Capabilities:**
- Advanced input with auto-completion and auto-suggestions
- Multi-line editing with history
- Syntax highlighting while typing
- Full-screen application support
- Layout engine (HSplit, VSplit, Windows, Floats)
- Buffer management
- Key binding system with filters
- Mouse support
- Both Emacs and Vi key bindings
- Works with Unicode double-width characters
- No global state
- Mature and battle-tested (v3.0+)

**Key Features:**
- Very flexible low-level control
- Can build anything from simple prompts to complex TUIs
- Used by IPython, ptpython, and many other tools
- Excellent documentation

---

## Migration Options Analysis

### Option 1: Keep Status Quo (prompt_toolkit + Rich)
**Remove:** Textual (unused bloat)
**Keep:** prompt_toolkit + Rich

**Pros:**
- Zero migration work
- Already working perfectly
- Both libraries serve distinct purposes
- prompt_toolkit handles complex TUI (analysis mode)
- Rich handles formatting and simple prompts

**Cons:**
- Still have two dependencies for CLI
- prompt_toolkit is lower-level, more verbose

**Migration Effort:** Minimal (just remove Textual from dependencies)

**Recommendation Level:** ⭐⭐⭐⭐ **RECOMMENDED**

---

### Option 2: Migrate to Textual + Rich
**Remove:** prompt_toolkit
**Keep:** Textual + Rich
**Add:** Potentially need Rich for output anyway since Textual builds on it

**Pros:**
- Modern, web-inspired API
- CSS styling is elegant
- Great for building complex TUIs
- Same maintainer as Rich
- Growing ecosystem
- Can deploy to web

**Cons:**
- **MAJOR REWRITE REQUIRED** (~1,163 lines in analysis.py alone)
- Would need to rewrite:
  - Entire analysis.py TUI application
  - SQL editor in query.py
  - REPL system in cli.py
- Textual is still maturing (v6.x) vs prompt_toolkit (v3.0, very stable)
- Different mental model (reactive components vs imperative layouts)
- Risk of hitting framework limitations during migration
- Significant testing required for complex features

**Migration Effort:** **VERY HIGH** (2-4 weeks of full-time work)

**Specific Changes Required:**
1. **analysis.py** - Complete rewrite:
   - Convert HSplit layout to Textual containers
   - Replace Buffer system with TextArea widget
   - Rewrite all 40+ key bindings as Textual actions
   - Convert FormattedTextControl to Textual widgets
   - Adapt async query execution to Textual workers
   - Rebuild focus management
   - Reimplement scrolling logic

2. **query.py** - Significant rewrite:
   - Replace PromptSession with Textual TextArea
   - Rebuild syntax highlighting
   - Recreate auto-completion system
   - Key bindings to Textual actions

3. **cli.py** - Moderate rewrite:
   - Replace PromptSession REPL
   - New completion system
   - Textual app wrapper

**Recommendation Level:** ⭐ **NOT RECOMMENDED**

---

### Option 3: Consolidate to prompt_toolkit Only
**Remove:** Textual, Rich
**Keep:** prompt_toolkit only

**Pros:**
- Single dependency for all CLI/TUI needs
- prompt_toolkit CAN do formatted output
- Everything stays consistent

**Cons:**
- Rich is MUCH better for formatted output than prompt_toolkit
- Would lose beautiful tables, panels, syntax displays
- prompt_toolkit's formatting is more verbose
- Would make 14 files worse for minimal gain
- Significant refactoring across entire codebase

**Migration Effort:** HIGH (14 files need Rich output replaced)

**Recommendation Level:** ⭐ **NOT RECOMMENDED**

---

### Option 4: Rich Only
**Remove:** Textual, prompt_toolkit
**Keep:** Rich only

**Pros:**
- Simplest dependency tree
- Rich is beautiful

**Cons:**
- **COMPLETELY IMPOSSIBLE**
- Rich cannot build interactive TUI applications
- No key binding system
- No layout management
- Would lose:
  - Entire analysis mode (1,163 lines)
  - SQL editor
  - REPL system
- This is not a viable option

**Recommendation Level:** ❌ **IMPOSSIBLE**

---

## Detailed Cost-Benefit Analysis

### Current Architecture Works Well
The current split between Rich and prompt_toolkit is actually **architecturally sound**:

1. **Rich handles presentation** (formatting, tables, panels)
   - Used in 14 files
   - Perfect for its job
   - No replacement needed

2. **prompt_toolkit handles interaction** (input, TUI, key bindings)
   - Used in 3 critical files
   - Powers the most complex feature (analysis mode)
   - Mature and stable

### Why Textual Migration Is Risky

1. **The analysis.py TUI is extremely complex:**
   - 1,163 lines of carefully crafted prompt_toolkit code
   - 40+ key bindings with conditional logic
   - Custom scrolling with column windowing
   - Multiple view modes with state management
   - Async integration
   - Focus management between panels

2. **Textual's reactive model is fundamentally different:**
   - Would require rethinking state management
   - Different event model
   - Different layout system
   - Learning curve for maintainers

3. **Testing burden:**
   - All TUI interactions need re-testing
   - Complex workflows (wizard, save, load, browse)
   - High risk of regressions

4. **Maintenance benefits are unclear:**
   - Current code works perfectly
   - prompt_toolkit is mature and stable
   - Would we actually benefit from CSS styling in a terminal app?

---

## Final Recommendation

### ⭐⭐⭐⭐ **RECOMMENDED: Keep prompt_toolkit + Rich, Remove Textual**

**Action Items:**
1. Remove `textual>=6.2.1` from `pyproject.toml`
2. Run `uv sync` to clean up dependencies
3. Document the architectural decision:
   - **Rich** = Output formatting, tables, styling
   - **prompt_toolkit** = Interactive input, REPL, full TUI applications

**Rationale:**
- Current architecture is well-designed and working perfectly
- The split between presentation (Rich) and interaction (prompt_toolkit) is clean
- analysis.py is too complex to rewrite without significant risk
- prompt_toolkit is mature, stable, and battle-tested
- No compelling benefit justifies 2-4 weeks of risky refactoring
- Textual is unused bloat that should be removed

**Future Consideration:**
If starting from scratch, Textual would be an excellent choice. But with a working, complex TUI already built in prompt_toolkit, migration doesn't make business sense.

---

## Alternative: Gradual Migration Strategy (Not Recommended)

If there's strong desire to move to Textual despite the risks, consider:

1. **Phase 1:** Keep analysis.py on prompt_toolkit
2. **Phase 2:** Migrate query.py SQL editor to Textual (lower risk)
3. **Phase 3:** Migrate cli.py REPL to Textual
4. **Phase 4:** Eventually tackle analysis.py (highest risk)

**Estimated Total Effort:** 4-6 weeks

**Risk Level:** HIGH - Two TUI frameworks in parallel is messy

**Verdict:** Still not recommended. Stick with prompt_toolkit + Rich.

---

## Implementation If Proceeding with Recommendation

```bash
# Remove Textual
uv remove textual

# Verify clean state
uv sync

# Run tests
uv run pytest tests/unit
uv run pytest tests/smoke
```

**Documentation Updates:**
- Add to `CLAUDE.md`: "Use Rich for output formatting, prompt_toolkit for interactive input/TUI"
- Note in `architecture.md`: CLI layer uses Rich+prompt_toolkit, no Textual

---

## Conclusion

The current CLI architecture with **Rich for presentation** and **prompt_toolkit for interaction** is sound, mature, and working excellently. Textual should be removed as unused bloat. No migration is recommended unless starting a new project from scratch.
