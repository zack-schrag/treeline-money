# Tagging Power Mode - Implementation Proposal

## Overview
Implement an interactive tagging interface that allows users to rapidly categorize transactions using keyboard shortcuts and intelligent tag suggestions.

## Requirements Analysis
1. Rapid transaction tagging with suggested tags
2. Free navigation (up/down) through transactions without forced sequential flow
3. Keyboard-driven interface for power users
4. Abstracted tag suggestion system (initially: most frequently used tags)
5. Textual-based UI for rich terminal experience

## Architecture Design

### Service Layer (Hexagonal Architecture)
Following hexagonal architecture, all business logic must be in the service layer, not the CLI.

#### New Service: `TaggingService` (in `src/treeline/app/service.py`)
```python
class TaggingService:
    """Service for managing transaction tagging operations."""

    def __init__(self, repository: Repository, tag_suggester: TagSuggester):
        self.repository = repository
        self.tag_suggester = tag_suggester

    async def get_untagged_transactions(
        self, user_id: UUID, limit: int = 100
    ) -> Result[List[Transaction]]:
        """Get transactions that have no tags or minimal tags."""
        pass

    async def get_transactions_for_tagging(
        self, user_id: UUID, filters: Dict[str, Any] = {}
    ) -> Result[List[Transaction]]:
        """Get transactions matching filters for tagging session."""
        pass

    async def update_transaction_tags(
        self, user_id: UUID, transaction_id: UUID, tags: List[str]
    ) -> Result[Transaction]:
        """Update tags for a single transaction."""
        pass

    async def get_suggested_tags(
        self, user_id: UUID, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """Get suggested tags for a transaction using configured suggester."""
        pass
```

#### New Abstraction: `TagSuggester` (in `src/treeline/abstractions.py`)
```python
class TagSuggester(ABC):
    """Abstract interface for tag suggestion algorithms."""

    @abstractmethod
    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, all_transactions: List[Transaction], limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest tags for a transaction.

        Args:
            user_id: User context
            transaction: Transaction to suggest tags for
            all_transactions: All user transactions for context
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        pass
```

#### Initial Implementation: `FrequencyTagSuggester` (in `src/treeline/infra/tag_suggesters.py`)
```python
class FrequencyTagSuggester(TagSuggester):
    """Suggests tags based on frequency of use."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, all_transactions: List[Transaction], limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest most frequently used tags.

        Algorithm:
        1. Count tag usage across all transactions
        2. Return top N most frequently used tags
        3. Exclude tags already applied to this transaction
        """
        pass
```

Future implementations could include:
- `AITagSuggester` - Uses LLM to suggest tags based on transaction description
- `PatternTagSuggester` - Uses merchant patterns and historical tagging
- `HybridTagSuggester` - Combines multiple strategies

### Repository Extensions
Add methods to `Repository` abstraction (in `src/treeline/abstractions.py`):

```python
@abstractmethod
async def get_transactions(
    self, user_id: UUID, filters: Dict[str, Any] = {}, limit: int = 100
) -> Result[List[Transaction]]:
    """
    Get transactions with optional filters.

    Filters can include:
    - has_tags: bool - filter by tagged/untagged
    - account_id: UUID - filter by account
    - start_date: datetime - transactions after date
    - end_date: datetime - transactions before date
    """
    pass

@abstractmethod
async def update_transaction_tags(
    self, user_id: UUID, transaction_id: UUID, tags: List[str]
) -> Result[Transaction]:
    """Update only the tags field of a transaction."""
    pass

@abstractmethod
async def get_tag_statistics(
    self, user_id: UUID
) -> Result[Dict[str, int]]:
    """Get tag usage frequency statistics."""
    pass
```

### Textual UI Components

#### Main Widget: `TaggingPowerMode` (in `src/treeline/ui/tagging.py`)
Using Textual framework for rich terminal UI:

```python
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import DataTable, Static, Input, Label
from textual.screen import Screen

class TaggingPowerMode(Screen):
    """Interactive tagging interface."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save & Exit"),
        ("up", "prev_transaction", "Previous"),
        ("down", "next_transaction", "Next"),
        ("1-9", "quick_tag", "Quick tag"),
        ("enter", "apply_tag", "Apply tag"),
        ("backspace", "remove_tag", "Remove last tag"),
    ]

    def compose(self) -> ComposeResult:
        """Create UI layout."""
        yield Container(
            Vertical(
                Static("🏷️  Tagging Power Mode", id="header"),
                DataTable(id="transaction-list"),  # Scrollable transaction list
                Horizontal(
                    Static("Current Tags:", id="tags-label"),
                    Static("", id="current-tags"),  # Display current tags
                ),
                Horizontal(
                    Static("Suggested:", id="suggested-label"),
                    Static("", id="suggested-tags"),  # Show suggestions with numbers
                ),
                Input(placeholder="Type tag or press number for suggestion", id="tag-input"),
                Static("", id="status-bar"),
            )
        )
```

Key UI features:
1. **Transaction List** - DataTable showing transactions with:
   - Date
   - Description
   - Amount
   - Current tags
   - Highlight current selection

2. **Current Tags Display** - Shows tags already applied to selected transaction

3. **Suggested Tags** - Shows numbered suggestions (1-9) for quick application

4. **Tag Input** - Allows typing custom tags or using numbers for suggestions

5. **Status Bar** - Shows keyboard shortcuts and progress

### User Experience Flow

1. User enters power mode via `/tag` command
2. Textual screen displays:
   - List of untagged/partially tagged transactions (scrollable)
   - Current transaction highlighted
   - Current tags for selected transaction
   - Suggested tags (numbered 1-5)
   - Input field for custom tags
3. User can:
   - Press `↑`/`↓` to navigate between transactions
   - Press `1`-`9` to instantly apply suggested tag
   - Type custom tag and press `Enter`
   - Press `Backspace` to remove last applied tag
   - Press `Ctrl+S` to save and exit
   - Press `Escape` to cancel without saving

### Data Flow

```
User Input (Textual UI)
    ↓
CLI Handler (thin presentation layer)
    ↓
TaggingService (business logic)
    ↓
Repository (data access)
    ↓
DuckDB (storage)
```

Tag suggestions:
```
TaggingService.get_suggested_tags()
    ↓
TagSuggester.suggest_tags()
    ↓
FrequencyTagSuggester (initial implementation)
```

## Implementation Steps

### Phase 1: Service Layer & Abstractions
1. Add `TagSuggester` abstraction to `src/treeline/abstractions.py`
2. Create `TaggingService` in `src/treeline/app/service.py`
3. Add required methods to `Repository` abstraction
4. Implement repository methods in `DuckDBRepository`
5. Create `FrequencyTagSuggester` in `src/treeline/infra/tag_suggesters.py`
6. Update `Container` to wire up dependencies

### Phase 2: Textual UI
1. Create `src/treeline/ui/` directory
2. Implement `TaggingPowerMode` screen in `src/treeline/ui/tagging.py`
3. Add keyboard bindings and navigation logic
4. Implement tag application UI logic
5. Add progress indicators and status messages

### Phase 3: CLI Integration
1. Update `/tag` command handler in `src/treeline/cli.py`
2. Wire up Textual screen to CLI command
3. Handle screen lifecycle (enter/exit)
4. Display success/error messages

### Phase 4: Testing
1. Unit tests for `TaggingService` (mocked repository)
2. Unit tests for `FrequencyTagSuggester` (mocked data)
3. Smoke tests for `/tag` command flow
4. Test keyboard navigation and tag application

## Technology Choices

### Textual Widgets
- `DataTable` - For transaction list (supports selection, scrolling, styling)
- `Static` - For labels and display-only text
- `Input` - For custom tag entry
- `Container` + `Vertical`/`Horizontal` - For layout
- `Screen` - For full-screen modal experience

### Why Textual?
- Already in tech stack (docs/internal/architecture.md)
- Rich keyboard navigation support
- Highly customizable styling
- Built for terminal power users
- Supports reactive data updates

## Alternatives Considered

### Alternative 1: Simple Rich Table with Prompt Loop
- Pros: Simpler implementation, no new framework
- Cons: Poor UX for rapid tagging, limited keyboard navigation, no real-time updates

### Alternative 2: Inline editing in transaction list
- Pros: Familiar spreadsheet-like feel
- Cons: Complex to implement well, harder to show suggestions clearly

### Conclusion
Textual provides the best balance of power user features and implementation complexity. The `DataTable` widget is purpose-built for this use case.

## Future Enhancements
1. **AI-powered tag suggestions** - Add `AITagSuggester` using LLM to analyze descriptions
2. **Batch operations** - Tag multiple transactions at once with same tags
3. **Tag management** - Rename/merge/delete tags across all transactions
4. **Filters and search** - Filter transaction list by account, date range, amount
5. **Tag autocomplete** - Show existing tags as you type
6. **Undo/redo** - Support undoing tag changes
7. **Tag templates** - Save common tag sets for quick application

## Alignment with Project Vision

### Local-first
All tagging operations happen locally in DuckDB. No server interaction required.

### AI-native
Tag suggester abstraction designed to easily plug in AI-powered suggestions. Initial frequency-based suggester provides value immediately while AI enhancement is planned.

### Hexagonal Architecture
- Business logic in `TaggingService`
- Tag suggestion algorithm abstracted via `TagSuggester`
- CLI is thin presentation layer
- Easy to swap suggestion strategies
- Repository abstraction hides DuckDB details

### Vibes
- **Feels like coding** - Keyboard-driven, powerful shortcuts, no mouse required
- **Feels fun** - Rapid tagging with instant feedback, gamified with numbers
- **Feels obvious** - Arrow keys to navigate, numbers for suggestions, Enter to apply

## Open Questions
1. Should we auto-save tags as user navigates away, or require explicit save?
   - **Recommendation**: Auto-save on tag application for better UX
2. Should we support multi-select for batch tagging in v1?
   - **Recommendation**: No, keep v1 simple. Add in future enhancement
3. How many transactions to load by default?
   - **Recommendation**: 100, with option to load more or apply filters
