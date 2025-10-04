# Textual UI Revamp Proposal

## Overview

This proposal outlines a redesign of the Treeline terminal UI using [Textual](https://textual.textualize.io/), transforming the current basic REPL into a rich, dynamic terminal application that better serves power users while maintaining the CLI-first philosophy.

**Scope**: This proposal focuses on **revamping the UI for existing functionality** (Chat, Status, Sync). It provides the foundation for future features like tagging power mode (see `tagging-power-mode-proposal.md`), but does not implement them.

## Vision Alignment

The redesigned UI will embody Treeline's core principles:

- **Local-first**: All data operations remain on the user's machine
- **CLI-centric**: Feels like using professional developer tools (lazygit, k9s, htop)
- **AI-native**: AI chat is a first-class interface, not an afterthought
- **Fun and obvious**: Keyboard-driven, responsive, and intuitive
- **Show your work**: SQL queries and tool usage are transparent
- **Power users first**: Information-dense without clutter, keyboard shortcuts for everything

## Architecture: Persistent Input with Dynamic Mode Panels

### Design Philosophy

The UI uses a **persistent text input** at the bottom that is always accessible, with **dynamic mode-specific panels** above that respond to slash commands and user actions.

**Key Principles**:
1. **Always-available input**: Text input is always present at the bottom - users can always type slash commands or AI queries
2. **Context panels above**: Mode-specific content displays above the input, varying based on the current context
3. **Focus shifting**: Users can shift focus between input and mode panel using `Tab` or `Esc`
4. **Interactive panels**: Mode panels can be interactive (e.g., edit SQL, navigate transactions) or display-only

### Interaction Flow

```
User types /tag → Tag panel appears above input
User presses Tab → Focus shifts to tag panel (keyboard navigation in transactions)
User presses Esc → Focus returns to input
User types /status → Tag panel replaced by status panel
User types AI query → Chat response appears in panel above
```

**Rationale**: This design keeps the familiar text input interface while adding rich interactive panels above. Users maintain a consistent mental model (type commands below, see results above) while gaining power-user interactivity when needed.

## Proposed Textual Widgets

### Global Layout

```
┌─ Treeline ─────────────────────────────────────────────────────────┐
│ 1,247 txns | 3 accts | Last sync: 2m ago                          │ <- Header (minimal)
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                   [Dynamic Context Panel]                          │ <- Changes based on slash commands
│              (Chat history, Status display, Tag UI,                │    and AI responses
│                     SQL editor, etc.)                              │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│ > _                                                                 │ <- Text Input (always present)
├────────────────────────────────────────────────────────────────────┤
│ Tab:Focus Panel  Esc:Focus Input  ^C:Clear  /help:Commands        │ <- Footer (context hints)
└────────────────────────────────────────────────────────────────────┘
```

**Widgets**:
- `Header`: Minimal status bar showing key metrics only
- `DynamicPanel`: Container that swaps content based on context (chat, status, tag, SQL editor)
- `Input`: Persistent text input at bottom (always accepts slash commands and AI queries)
- `Footer`: Context-aware keyboard shortcuts

**Focus Model**:
- **Default focus**: Text input (users can always type)
- **Tab**: Shift focus to dynamic panel (if panel is interactive)
- **Esc**: Return focus to text input (from any panel)
- Panel-specific shortcuts only work when panel has focus

### Panel 1: Chat Panel (Default)

**Trigger**: AI queries (non-slash input) or `/clear` command

**Purpose**: Display conversation history with AI agent

**Layout**:
```
┌─ Dynamic Panel: Chat ──────────────────────────────────────────────┐
│                                                                     │
│ > show my spending trend for the last 3 months                     │
│                                                                     │
│ [dim][Using tool: execute_sql_query][/dim]                         │
│ [cyan]SELECT[/cyan] [white]date_trunc[/white]('month', ...)        │
│ [dim](Tab to edit SQL)[/dim]                                       │
│                                                                     │
│ Here's your spending trend for the last 3 months:                  │
│                                                                     │
│ ┌─ Monthly Spending ──────────────────────┐                        │
│ │     $3,200 ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇             │                        │
│ │     $2,800 ▇▇▇▇▇▇▇▇▇▇▇▇                  │                        │
│ │     $3,100 ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇                │                        │
│ └──────────────────────────────────────────┘                        │
│                                                                     │
│ Your spending increased by 14% in September...                     │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Widgets**:
- `RichLog`: Scrollable conversation history with Rich markup
  - Displays AI responses, SQL queries (syntax highlighted), charts, tool indicators
  - Shows "(Tab to edit SQL)" hint when SQL is displayed
  - Auto-scroll to bottom on new messages

**Interactive Features**:
- **SQL editing**: When AI displays SQL, users can press `Tab` to focus panel
  - Panel switches to SQL editor mode
  - User can edit the query directly
  - Press `Enter` to re-run edited query
  - Press `Esc` to return to input without running
- **History scrolling**: `PgUp/PgDn` when panel has focus

**Focus Behavior**:
- Panel is **non-focusable by default** (just displays content)
- Becomes **focusable** when SQL is shown (to enable editing)
- Footer hint changes: "Tab:Edit SQL" when SQL is present

### Panel 2: Status Panel

**Trigger**: `/status` command

**Purpose**: Display financial data overview

**Layout**:
```
┌─ Dynamic Panel: Status ────────────────────────────────────────────┐
│                                                                     │
│ Financial Data Summary                                             │
│                                                                     │
│   Accounts:              3                                         │
│   Transactions:      1,247                                         │
│   Balance Snapshots:    45                                         │
│   Integrations:          1                                         │
│                                                                     │
│   Date Range:  2024-01-15 to 2024-09-30                           │
│                                                                     │
│ ┌─ Connected Integrations ─────────────────────────────────────┐   │
│ │ • SimpleFIN                                    Last sync: 2m │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─ Accounts ────────────────────────────────────────────────────┐  │
│ │ Name                 Type         Balance      Last Updated   │  │
│ │ Chase Checking       checking     $3,245.67   Sep 30, 2024   │  │
│ │ Ally Savings         savings     $12,890.12   Sep 30, 2024   │  │
│ │ Amex Blue Cash       credit      -$1,234.56   Sep 30, 2024   │  │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Widgets**:
- `Static`: Summary metrics and titles
- `DataTable`: Accounts list
- Custom `MetricCard` widgets for integration status
- `VerticalScroll`: Container for all content

**Interactive Features**:
- **Table navigation**: Press `Tab` to focus panel, then use arrow keys to navigate accounts
- **Row selection**: `Enter` on selected account to see details (future enhancement)

**Focus Behavior**:
- Panel is **focusable** (to enable table navigation)
- When focused, `↑/↓` navigate table rows
- `Esc` returns to input
- Footer hint: "Tab:Navigate Table  Esc:Input"

### Panel 3: Tag Panel (Future - Out of Scope)

**Trigger**: `/tag` command

**Status**: ⏳ Not included in this proposal - see `tagging-power-mode-proposal.md`

**Purpose**: Rapid transaction tagging (future)

**Layout Example**:
```
┌─ Dynamic Panel: Tag ───────────────────────────────────────────────┐
│ Untagged: 47 | Showing: 1-10                                       │
│                                                                     │
│ Sep 28  Whole Foods Market          -$87.43  []                   │
│ Sep 27  Shell Gas Station           -$45.00  []                   │
│ Sep 26  Netflix                      -$15.99  []    ← selected     │
│                                                                     │
│ Suggested: 1:groceries  2:gas  3:subscriptions  4:dining          │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Integration Point**: When implemented, Tag Panel will:
1. Appear when user types `/tag` in persistent input
2. Input loses focus, panel gains focus (user navigates with `j/k` or arrows)
3. User tags transactions with number keys (1-5) or types custom tags
4. Press `Esc` to return focus to input
5. Type new command or query to dismiss tag panel

The dynamic panel architecture makes adding this straightforward - no changes to core layout needed.

### Panel 4: SQL Editor Panel (Inline with Chat)

**Trigger**: Pressing `Tab` when AI displays SQL in chat panel

**Purpose**: Allow users to edit and re-run AI-generated SQL

**Layout**:
```
┌─ Dynamic Panel: SQL Editor ────────────────────────────────────────┐
│ [Previous chat context above...]                                   │
│                                                                     │
│ ┌─ Edit SQL (Enter:Run  Esc:Cancel) ────────────────────────────┐  │
│ │ SELECT                                                         │  │
│ │   date_trunc('month', transaction_date) as month,             │  │
│ │   sum(amount) as total                                        │  │
│ │ FROM transactions                                             │  │
│ │ WHERE tags @> ARRAY['groceries']  ← cursor here               │  │
│ │ GROUP BY month                                                │  │
│ │ ORDER BY month DESC                                           │  │
│ └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Widgets**:
- `TextArea`: Editable SQL with syntax highlighting
- `Static`: Instructions header

**Interactive Features**:
- **Inline editing**: SQL becomes editable in-place when user presses `Tab`
- **Enter**: Execute modified query, append results to chat
- **Esc**: Cancel editing, return to input
- **Syntax highlighting**: Live syntax highlighting as user types

**Flow**:
1. AI generates SQL and shows results in chat panel
2. User presses `Tab` → SQL becomes editable (TextArea appears)
3. User modifies query
4. User presses `Enter` → Query executes, results append to chat
5. Panel returns to chat display mode

This allows users to tweak AI-generated queries without retyping or copying.

## Panel Switching & Focus Management

### Panel Triggers (via Input)

All panel switching happens through the persistent text input:

- **Chat Panel** (default): Any AI query (non-slash input) or `/clear`
- **Status Panel**: `/status` command
- **Tag Panel**: `/tag` command (future)
- **SQL Editor Panel**: Press `Tab` when SQL is displayed in chat

### Focus Management

**Default State**: Input has focus (users can always type)

**Tab Key Behavior** (context-aware):
- From input, when panel is focusable → Shift focus to panel
- From panel → Return focus to input (or cycle within panel if multiple focusable elements)

**Esc Key Behavior**:
- Always returns focus to input (from any panel)
- If already at input, Esc does nothing

**Focus Indicators**:
- Input: Cursor visible, prompt highlighted
- Panel: Border color change, element highlighting (e.g., selected table row)
- Footer: Dynamic hints show available actions based on focus

### Global Shortcuts (work from anywhere)

- `Ctrl+C`: Clear current panel, return to chat panel with input focus
- `Ctrl+Q`: Quit application
- `F1`: Show help overlay (modal)
- `F5`: Trigger sync (shows progress in panel)

## Integration with Existing Commands

### Slash Commands (via Persistent Input)

All commands are entered through the persistent text input at the bottom:

**Panel-changing commands**:
- `/status`: Display status panel ✅ **Phase 1**
- `/clear`: Clear chat history, return to empty chat panel ✅ **Phase 1**
- `/tag`: Display tag panel ⏳ **Future** (see `tagging-power-mode-proposal.md`)

**Modal commands** (open overlay dialogs):
- `/help`: Show help overlay ✅ **Phase 1**
- `/login`: Login dialog ✅ **Phase 1**
- `/simplefin`: SimpleFIN setup dialog ✅ **Phase 1**
- `/sync`: Trigger sync with progress overlay ✅ **Phase 1**
- `/import`: CSV import wizard ⏳ **Future**

**Natural Language** (non-slash input):
- Any text without `/` prefix → Sent to AI agent
- Response appears in chat panel
- SQL queries shown with "(Tab to edit)" hint

## Technical Implementation

### File Structure

```
src/treeline/ui/
    __init__.py
    app.py              # Main Textual App class with persistent input + dynamic panel
    panels/
        __init__.py
        base.py         # BasePanel abstract class (with focus management)
        chat.py         # ChatPanel - conversation history ✅ Phase 1
        status.py       # StatusPanel - financial overview ✅ Phase 1
        sql_editor.py   # SQLEditorPanel - inline SQL editing ✅ Phase 1
        tag.py          # TagPanel - transaction tagging ⏳ Future
    widgets/
        __init__.py
        header.py       # Minimal header with key metrics ✅ Phase 1
        footer.py       # Context-aware footer (dynamic hints) ✅ Phase 1
        metric_card.py  # Status panel metric cards ✅ Phase 1
        persistent_input.py  # Always-visible input widget ✅ Phase 1
```

**Key architectural changes**:
- Renamed `modes/` → `panels/` to reflect new design (dynamic panels, not full-screen modes)
- Added `persistent_input.py` - the always-present input widget
- Removed `chart_viewer.py` - charts render inline in ChatPanel using existing PyPlot
- `sql_editor.py` - new panel for inline SQL editing triggered by Tab

### Textual App Structure

```python
class TreelineApp(App):
    BINDINGS = [
        ("ctrl+c", "clear_panel", "Clear"),
        ("ctrl+q", "quit", "Quit"),
        ("f1", "show_help", "Help"),
        ("f5", "sync", "Sync"),
        ("tab", "toggle_focus", "Toggle Focus"),
        ("escape", "focus_input", "Focus Input"),
    ]

    def __init__(self, container: Container):
        super().__init__()
        self.container = container  # DI container
        self.current_panel: BasePanel | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="dynamic-panel")  # Swappable panel content
        yield PersistentInput(id="main-input")  # Always-present input
        yield Footer()

    def on_mount(self) -> None:
        self.load_panel(ChatPanel())  # Default panel
        self.query_one("#main-input").focus()  # Focus input by default

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle input from persistent input widget."""
        text = message.value.strip()

        if text.startswith("/"):
            # Slash command - load appropriate panel or show modal
            await self.handle_slash_command(text)
        else:
            # AI query - send to agent, display in chat panel
            await self.handle_ai_query(text)

    def load_panel(self, panel: BasePanel) -> None:
        """Swap the current panel."""
        container = self.query_one("#dynamic-panel")
        container.remove_children()  # Clear current panel
        container.mount(panel)
        self.current_panel = panel

    def action_toggle_focus(self) -> None:
        """Tab key: toggle focus between input and panel."""
        input_widget = self.query_one("#main-input")

        if input_widget.has_focus:
            # Move focus to panel (if focusable)
            if self.current_panel and self.current_panel.can_focus:
                self.current_panel.focus()
        else:
            # Return focus to input
            input_widget.focus()

    def action_focus_input(self) -> None:
        """Esc key: always return to input."""
        self.query_one("#main-input").focus()
```

**Key Concepts**:
- **Persistent input**: Always mounted, handles all user commands
- **Dynamic panel**: Container that swaps panel widgets based on commands
- **Focus management**: Tab toggles between input/panel, Esc always returns to input
- **Panel loading**: `load_panel()` swaps entire panel content

### Panel Base Class

```python
class BasePanel(Widget):
    """Base class for all dynamic panels."""

    can_focus: bool = False  # Override in subclasses that need focus

    @abstractmethod
    async def on_load(self) -> None:
        """Called when panel is loaded into view."""
        pass

    def get_footer_hints(self) -> str:
        """Return context-specific footer hints."""
        return "Esc:Input  ^C:Clear  ^Q:Quit"

class ChatPanel(BasePanel):
    can_focus = True  # Focusable when SQL is displayed

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log")

    async def append_message(self, content: str):
        log = self.query_one("#chat-log")
        log.write(content)

    def get_footer_hints(self) -> str:
        if self.has_sql_displayed:
            return "Tab:Edit SQL  PgUp/Dn:Scroll  Esc:Input"
        return "PgUp/Dn:Scroll  Esc:Input"
```

### Service Layer Integration

The UI uses the existing service layer (hexagonal architecture preserved):

```python
# In TreelineApp
async def handle_ai_query(self, query: str):
    # Ensure chat panel is loaded
    if not isinstance(self.current_panel, ChatPanel):
        self.load_panel(ChatPanel())

    # Call existing agent_service.chat()
    result = await self.container.agent_service().chat(user_id, db_path, query)

    # Stream response to chat panel
    async for chunk in result.data["stream"]:
        await self.current_panel.append_message(chunk)
```

**No business logic in UI layer** - all logic remains in `src/treeline/app/service.py`

### Graceful Fallback

If Textual initialization fails:
1. Log error
2. Fall back to current REPL implementation
3. Notify user: "Enhanced UI unavailable, using basic mode"

This ensures backwards compatibility and resilience.

## Benefits of Textual Redesign

### 1. **Enhanced User Experience**
- **Always-available input**: Users never lose access to command line (consistent mental model)
- **Richer visualizations**: Tables, charts, formatted text in dynamic panel above
- **Context-aware shortcuts**: Keyboard shortcuts change based on panel and focus
- **Visual feedback**: Loading indicators, progress overlays, dynamic footer hints
- **Seamless transitions**: Panel content changes without disrupting input availability

### 2. **Better AI Integration**
- **Streaming clarity**: Responses appear progressively in chat panel above input
- **Tool transparency**: Tool usage shown inline without interrupting flow
- **SQL editability**: Users can edit AI-generated SQL inline (Tab to edit, Enter to run)
- **Query refinement**: Modify and re-run queries without leaving the chat flow

### 3. **Foundation for Future Features**
- **Extensible panel system**: Adding new panels (Tag, custom views) is straightforward
- **Service layer integration**: UI calls existing services, no business logic in UI
- **Panel abstraction**: New features isolated in their own panel implementations
- **Focus model scales**: Tab/Esc pattern works for any interactive panel

### 4. **Developer-Friendly**
- **Panel abstraction**: Easy to add new panels (plugins could add custom panels)
- **Widget reusability**: Components shared across panels
- **Testability**: Textual apps are unit-testable with `pilot` API
- **Clear separation**: Panel logic separate from app-level input handling

### 5. **Maintains Philosophy**
- **Terminal-first**: Still runs in terminal, no web browser required
- **Keyboard-driven**: Power users never touch the mouse
- **Local-first**: All data operations remain local
- **Fast**: Textual is lightweight and responsive

## Risks & Mitigations

### Risk 1: Learning Curve for Textual
**Mitigation**:
- Textual has excellent documentation and examples
- Start with Chat Mode (simplest), then iterate
- Community support on Discord

### Risk 2: Complexity Creep
**Mitigation**:
- Follow hexagonal architecture strictly (no business logic in UI)
- Use mode abstraction to keep features isolated
- Regular code reviews for architecture compliance

### Risk 3: Performance with Large Datasets
**Mitigation**:
- Lazy loading for transaction lists (load 50 at a time)
- DataTable widget handles virtualization automatically
- Query result pagination

### Risk 4: Terminal Compatibility
**Mitigation**:
- Textual works on all modern terminals (supports fallback rendering)
- Test on macOS Terminal, iTerm2, Windows Terminal, Linux terminals
- Document minimum terminal requirements

## Implementation Phases

**This proposal covers Phase 1-5 only.** Tag Panel and other panels are separate proposals.

### Phase 1: Foundation (Week 1)
- [ ] Set up Textual project structure under `src/treeline/ui/`
- [ ] Create base `TreelineApp` with dynamic panel container
- [ ] Implement `PersistentInput` widget (always-visible input)
- [ ] Implement Header and Footer widgets
- [ ] Create `BasePanel` abstraction with focus management
- [ ] Implement focus switching (Tab/Esc) logic
- [ ] Set up graceful fallback to REPL if Textual fails

### Phase 2: Chat Panel (Week 2)
- [ ] Implement `ChatPanel` with `RichLog` for conversation history
- [ ] Integrate with existing `AgentService` (no changes to service layer)
- [ ] Add streaming response support
- [ ] Implement slash command routing (`/help`, `/login`, `/status`, `/simplefin`, `/sync`, `/clear`)
- [ ] Add SQL syntax highlighting in chat display
- [ ] Show "(Tab to edit)" hint when SQL is displayed
- [ ] Test chart rendering inline with ANSI codes

### Phase 3: SQL Editor Panel (Week 2-3)
- [ ] Implement `SQLEditorPanel` with `TextArea` for editing
- [ ] Add SQL syntax highlighting in editor
- [ ] Implement Tab-to-edit flow (Chat → SQL Editor → Chat)
- [ ] Execute edited query on Enter (call existing service)
- [ ] Cancel with Esc (return to input, dismiss editor)
- [ ] Append results to chat history

### Phase 4: Status Panel (Week 3)
- [ ] Implement `StatusPanel` with `DataTable` and metric cards
- [ ] Integrate with existing `StatusService` (no changes to service layer)
- [ ] Make panel focusable (Tab to navigate table)
- [ ] Implement table navigation (arrow keys when focused)
- [ ] Test with various data sizes (0 accounts, 1 account, 10+ accounts)
- [ ] Add dynamic footer hints for focused state

### Phase 5: Polish & Testing (Week 4)
- [ ] Add comprehensive help overlay (F1) - shows all commands and shortcuts
- [ ] Implement modal dialogs for `/login`, `/simplefin`
- [ ] Add sync progress overlay (F5 or `/sync`)
- [ ] Unit tests for all panels
- [ ] Integration tests with Textual `pilot` API (focus management, panel switching)
- [ ] Test graceful fallback to REPL
- [ ] Performance testing with various data sizes
- [ ] Update CLI documentation
- [ ] User acceptance testing

### Future Phases (Separate Proposals)
- **Tag Panel**: See `tagging-power-mode-proposal.md` for detailed implementation plan
- **Additional Panels**: Account details, budget views, etc. (TBD)

## Success Metrics (Phase 1-5)

- **Input availability**: Users can always type commands (input never blocked)
- **Response time**: UI remains responsive (<100ms) for all interactions
- **Learning curve**: New users understand input/panel model within 5 minutes
- **Keyboard efficiency**: 95% of operations doable without mouse
- **Feature parity**: All existing REPL commands work in Textual UI
- **SQL editing**: Users can edit AI-generated SQL inline without context switching
- **Focus clarity**: Always obvious where focus is (input vs panel)
- **Stability**: Graceful fallback to REPL if Textual fails (no crashes)
- **User feedback**: Positive sentiment on "feels like a developer tool"

## Conclusion

This Textual UI revamp transforms Treeline from a basic REPL into a richer terminal application with a **persistent input** and **dynamic panels**, while maintaining feature parity with existing functionality.

**Core Design Principle**: Users always have access to the text input (bottom) and can type any command. Panels (above input) respond to commands and can be interactive when needed.

**Phase 1-5 Scope** (this proposal):
1. **Preserves core philosophy**: Terminal-first, keyboard-driven, local-first
2. **Enhances AI integration**: SQL editing inline, streaming responses, tool transparency
3. **Maintains architecture**: Hexagonal principles, no business logic in UI, thin presentation layer
4. **Provides foundation**: Panel system ready for Tag Panel and future interactive features
5. **Always-available input**: Users never lose the command line - consistent with CLI mental model

**Out of Scope** (separate proposals):
- **Tag Panel**: See `tagging-power-mode-proposal.md` - includes service layer changes, tag suggestion abstraction
- **Additional Panels**: Account details, budget views, custom queries (future)

The persistent input + dynamic panel design keeps the familiar CLI interaction while adding power-user interactivity. The phased implementation focuses on revamping existing functionality before adding new features.

**Recommendation**: Proceed with Phase 1-5 implementation to establish the Textual foundation. Once complete, Tag Panel can be implemented as a separate initiative using the panel architecture established here.

## Relationship to Other Proposals

This proposal **complements** `tagging-power-mode-proposal.md`:

- **This proposal**: UI framework revamp (persistent input, dynamic panels, focus management)
- **Tag Mode proposal**: Feature implementation (TaggingService, TagSuggester abstraction, Tag Panel UI)

**Integration point**: Once this Textual UI revamp is complete, Tag Panel implementation will:
1. Create `TagPanel` class inheriting from `BasePanel`
2. Set `can_focus = True` to enable keyboard navigation
3. Add `/tag` command handler to load tag panel
4. Implement tag-specific shortcuts (1-5 for suggestions, j/k for navigation)
5. Use Tab to shift focus from input to tag panel
6. Use Esc to return focus to input
7. Integrate with `TaggingService` from service layer (to be built per tag proposal)

The two proposals work together sequentially:
1. **First**: Implement Textual UI revamp (this proposal) → establishes foundation
2. **Second**: Implement Tag Panel (separate proposal) → adds feature using foundation

**Example Tag Panel Integration**:
```python
# In TreelineApp.handle_slash_command()
if command == "/tag":
    tag_panel = TagPanel(tagging_service=self.container.tagging_service())
    self.load_panel(tag_panel)
    tag_panel.focus()  # Shift focus to panel for navigation
```

The persistent input remains available - user can press Esc to return to input and type new commands anytime.
