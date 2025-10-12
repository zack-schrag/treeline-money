# Refactor CSV-Specific Methods to Service Layer

## Priority
**CRITICAL** - Breaks abstraction boundary, creates tight coupling

## Violation
The import CSV command calls provider-specific methods (`detect_columns()`, `preview_transactions()`) that are NOT defined in the `DataAggregationProvider` abstraction.

**Location:** `src/treeline/commands/import_csv.py:110, 113, 137`
**Status:** Confirmed present in second review (2025-10-11)

**Current Code:**
```python
# Lines 110-113
csv_provider = container.provider_registry()["csv"]
detect_result = csv_provider.detect_columns(str(csv_path))

# Line 137
preview_result = csv_provider.preview_transactions(
    str(csv_path), column_mapping, date_format="auto", limit=5, flip_signs=flip_signs
)
```

## Why It's Wrong
This is a textbook example of the "BAD abstraction" pattern from `architecture.md`:

The methods `detect_columns()` and `preview_transactions()` exist ONLY on `CSVProvider`, not on the `DataAggregationProvider` abstraction. The CLI is:
1. Reaching past the service layer to get `provider_registry`
2. Casting to a specific provider type (CSV)
3. Calling provider-specific methods

This creates tight coupling to the CSV implementation and violates hexagonal architecture.

## Fix Approach

### Option A: Add methods to ImportService (RECOMMENDED)
CSV import is fundamentally different from data sync. These operations (detect, preview) are import-specific, not general data aggregation.

1. **Add methods to `ImportService`:**
   ```python
   async def detect_csv_columns(
       self, file_path: str
   ) -> Result[Dict[str, Any], Error]:
       # Internally gets CSV provider and calls detect_columns

   async def preview_csv_import(
       self, file_path: str, column_mapping: Dict[str, str],
       date_format: str = "auto", limit: int = 5,
       flip_signs: bool = False
   ) -> Result[List[Transaction], Error]:
       # Internally gets CSV provider and calls preview_transactions
   ```

2. **Update CSV provider abstraction:**
   - Create `CSVImportProvider` abstraction in `abstractions.py` if CSV-specific operations need to be abstracted
   - Or keep CSV-specific logic internal to `ImportService` since it's the only consumer

3. **Update import_csv command:**
   - Remove lines 110-113, 137 (direct provider access)
   - Replace with: `import_service.detect_csv_columns(str(csv_path))`
   - Replace with: `import_service.preview_csv_import(...)`

### Option B: Add to DataAggregationProvider abstraction
If other providers (future Plaid, etc.) will also need detection/preview:

1. Add generic methods to `DataAggregationProvider`:
   ```python
   async def detect_import_schema(self, source: str, settings: Dict[str, Any]) -> Result[Dict[str, Any], Error]
   async def preview_import(self, source: str, settings: Dict[str, Any]) -> Result[List[Transaction], Error]
   ```

2. Implement these in all providers (SimpleFIN returns NotImplemented, CSV implements)

**RECOMMENDATION:** Use Option A. These operations are CSV-import-specific and unlikely to apply to API-based providers.

## Files to Modify
- `src/treeline/app/service.py` - Add detect_csv_columns and preview_csv_import to ImportService
- `src/treeline/commands/import_csv.py` - Replace direct provider calls with service calls
- `tests/unit/app/test_service.py` - Add tests for new service methods
- `tests/unit/commands/test_import_csv.py` - Update to mock service layer

## Success Criteria
- [ ] Import CSV command no longer accesses `container.provider_registry()`
- [ ] All CSV operations go through ImportService
- [ ] Service layer properly encapsulates CSV-specific logic
- [ ] Unit tests pass
- [ ] Command functionality unchanged

## Notes
This is the most complex refactor of the architecture issues. The key insight is that CSV import has unique operations (detect, preview) that don't apply to SimpleFIN sync, so these should be service-layer methods that internally handle CSV-specific provider access.
