# Remove Infrastructure Imports from Tag Command

## Priority
**CRITICAL** - Direct CLI-to-Infrastructure dependency

## Violation
The tag command directly imports and instantiates infrastructure implementations (`FrequencyTagSuggester`, `CommonTagSuggester`, `CombinedTagSuggester`).

**Location:** `src/treeline/commands/tag.py:38, 54-57`

**Current Code:**
```python
# Line 38
from treeline.infra.tag_suggesters import FrequencyTagSuggester, CommonTagSuggester, CombinedTagSuggester

# Lines 54-57
frequency_suggester = FrequencyTagSuggester(repository)
common_suggester = CommonTagSuggester()
tag_suggester = CombinedTagSuggester(frequency_suggester, common_suggester)
tagging_service = container.tagging_service(tag_suggester)
```

## Why It's Wrong
The CLI layer should NEVER import from `treeline.infra`. The dependency flow must be: CLI → Services → Abstractions ← Infra. By importing infrastructure classes directly, the CLI is tightly coupled to specific implementations.

This violates hexagonal architecture's core principle of the CLI being a thin presentation layer.

## Fix Approach

1. **Move tag suggester construction to Container:**
   - Add `default_tag_suggester()` private method to `Container` class
   - This method constructs: `CombinedTagSuggester(FrequencyTagSuggester(repository), CommonTagSuggester())`

2. **Update `tagging_service()` method in Container:**
   - Change signature from: `tagging_service(tag_suggester: TagSuggester)`
   - To: `tagging_service(tag_suggester: Optional[TagSuggester] = None)`
   - If `tag_suggester` is None, use `self.default_tag_suggester()`

3. **Update tag command:**
   - Remove line 38 (infrastructure imports)
   - Remove lines 51-57 (repository access and suggester construction)
   - Replace with simple: `tagging_service = container.tagging_service()`

4. **Update tests:**
   - Mock `container.tagging_service()` to return a mocked service

## Files to Modify
- `src/treeline/commands/tag.py` - Remove infra imports and construction
- `src/treeline/app/container.py` - Add default suggester construction
- `tests/unit/commands/test_tag.py` - Update test mocks

## Success Criteria
- [ ] Tag command has no imports from `treeline.infra`
- [ ] Tag command only calls `container.tagging_service()` with no parameters
- [ ] Container handles all dependency construction
- [ ] Unit tests pass
- [ ] Command functionality unchanged

## Notes
This fix depends on task 01 being completed (removing repository access), since the current code passes repository to the suggester constructor. The container will handle this internally.
