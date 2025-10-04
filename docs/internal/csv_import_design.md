# CSV Import Design Proposal

## Overview
This document outlines the design for implementing CSV transaction imports in Treeline. The implementation must support deduplication across different providers (CSV and SimpleFIN) while adhering to hexagonal architecture principles.

## Problem Statement
Users need to import transactions from CSV files, which could come from various financial institutions. The challenge is:
1. CSV files don't have consistent external IDs like SimpleFIN
2. Deduplication must work across different import sources (CSV file A, CSV file B, SimpleFIN)
3. The same transaction might be imported multiple times from different sources
4. The architecture must remain provider-agnostic

## Current State Analysis

### Existing Deduplication Logic
SimpleFIN currently uses `external_ids` for deduplication:
- Transactions have `external_ids: Mapping[str, str]` field
- SimpleFIN stores: `{"simplefin": "tx_123", "simplefin_account": "acc_456"}`
- Deduplication queries by `external_ids.simplefin` to find existing transactions
- **Limitation**: This only works when providers supply stable external IDs

### Architecture Pattern
The codebase follows hexagonal architecture:
- **Abstraction**: `DataAggregationProvider` defines provider interface
- **Service Layer**: `SyncService` contains deduplication logic
- **Adapter**: `SimpleFINProvider` implements the abstraction

## Proposed Solution

### 1. Multi-Strategy Deduplication Service

Create a dedicated deduplication abstraction and service that supports multiple strategies:

```python
# src/treeline/abstractions.py
class DeduplicationStrategy(ABC):
    @abstractmethod
    def generate_dedup_key(self, transaction: Transaction) -> str:
        """Generate a deduplication key for a transaction."""
        pass

    @abstractmethod
    def find_duplicates(
        self,
        user_id: UUID,
        transactions: List[Transaction],
        repository: Repository
    ) -> Result[Dict[str, Transaction]]:
        """Find existing transactions that match the given transactions.

        Returns a map of dedup_key -> existing_transaction
        """
        pass
```

### 2. Deduplication Strategies

#### Strategy 1: External ID (for SimpleFIN)
- Uses provider-supplied external IDs
- Current implementation, no changes needed
- Key format: `"external_id:{provider}:{id}"`

#### Strategy 2: Fingerprint (for CSV and cross-provider)
- Generate fingerprint from transaction attributes
- Key format: `"fingerprint:{hash}"`
- Hash components:
  - Account external ID (from CSV account mapping)
  - Transaction date (normalized to date only, not time)
  - Amount (normalized to 2 decimal places)
  - Description (normalized: lowercase, trimmed, special chars removed)

```python
def generate_fingerprint(tx: Transaction, integration_name: str) -> str:
    """Generate a stable fingerprint for deduplication."""
    # Get account's external ID for this provider
    account_ext_id = tx.external_ids.get(f"{integration_name}_account", "")

    # Normalize components
    tx_date = tx.transaction_date.date().isoformat()
    amount_normalized = f"{tx.amount:.2f}"
    desc_normalized = re.sub(r'[^a-z0-9]', '', (tx.description or "").lower())

    # Create fingerprint
    fingerprint_str = f"{account_ext_id}|{tx_date}|{amount_normalized}|{desc_normalized}"
    fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

    return f"fingerprint:{fingerprint_hash}"
```

#### Strategy 3: Composite (Use both)
- Try external ID first, fall back to fingerprint
- Prevents duplicates even when CSV re-imports overlap with SimpleFIN

### 3. Enhanced Transaction Model

Add a `dedup_key` field to store the deduplication key:

```python
# src/treeline/domain.py
class Transaction(BaseModel):
    # ... existing fields ...
    dedup_key: str | None = None  # Store computed deduplication key
```

Update database schema:
```sql
ALTER TABLE transactions ADD COLUMN dedup_key VARCHAR;
CREATE INDEX IF NOT EXISTS idx_transactions_dedup_key ON transactions(dedup_key);
```

### 4. CSV Provider Implementation

```python
# src/treeline/infra/csv_provider.py
class CSVProvider(DataAggregationProvider):
    """CSV file implementation for data aggregation."""

    @property
    def can_get_accounts(self) -> bool:
        return False  # Accounts must be manually mapped

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return False

    async def get_transactions(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[Transaction]]:
        """Parse CSV file and return transactions."""
        csv_path = provider_settings.get("csvPath")
        account_mapping = provider_settings.get("accountMapping", {})

        # Parse CSV with flexible column mapping
        # Generate fingerprint-based dedup keys
        # Return Transaction objects
```

### 5. Updated Sync Service Logic

```python
# src/treeline/app/service.py
class SyncService:
    def __init__(
        self,
        provider_registry: Dict[str, DataAggregationProvider],
        repository: Repository,
        dedup_strategy: DeduplicationStrategy,  # NEW
    ):
        self.provider_registry = provider_registry
        self.repository = repository
        self.dedup_strategy = dedup_strategy

    async def sync_transactions(
        self,
        user_id: UUID,
        integration_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        provider_options: Dict[str, Any] | None = None,
    ) -> Result[Dict[str, Any]]:
        # ... get provider and discovered transactions ...

        # NEW: Generate dedup keys for discovered transactions
        for tx in discovered_transactions:
            tx.dedup_key = self.dedup_strategy.generate_dedup_key(tx)

        # NEW: Find duplicates using strategy
        duplicates_result = await self.dedup_strategy.find_duplicates(
            user_id, discovered_transactions, self.repository
        )
        if not duplicates_result.success:
            return duplicates_result

        existing_by_dedup_key = duplicates_result.data

        # Separate new vs updated transactions
        transactions_to_upsert = []
        for discovered_tx in discovered_transactions:
            if discovered_tx.dedup_key in existing_by_dedup_key:
                # Update: preserve existing transaction ID
                existing_tx = existing_by_dedup_key[discovered_tx.dedup_key]
                updated_tx = discovered_tx.model_copy(update={"id": existing_tx.id})
                transactions_to_upsert.append(updated_tx)
            else:
                # New transaction
                transactions_to_upsert.append(discovered_tx)

        # Bulk upsert
        # ...
```

### 6. CSV Import User Flow

1. **File Selection**
   ```bash
   tl import csv /path/to/transactions.csv
   ```

2. **Column Mapping** (interactive)
   - Detect columns automatically where possible
   - Prompt user to map: date, amount, description, account
   - Save mapping template for reuse

3. **Account Mapping** (interactive)
   - Show unique account identifiers found in CSV
   - Let user map to existing Treeline accounts
   - Option to create new accounts if needed

4. **Preview & Confirm**
   - Show first 5 transactions to be imported
   - Show deduplication stats (X new, Y duplicates)
   - Confirm before importing

5. **Import & Deduplicate**
   - Use fingerprint-based deduplication
   - Store dedup_key with each transaction
   - Report results

### 7. Storage of CSV Import Settings

Store CSV import configuration in integrations table:
```json
{
  "integrationName": "csv",
  "integrationOptions": {
    "imports": [
      {
        "id": "uuid",
        "name": "Chase Checking",
        "columnMapping": {
          "date": "Transaction Date",
          "amount": "Amount",
          "description": "Description"
        },
        "accountMapping": {
          "csv_account_id": "treeline_account_uuid"
        },
        "lastImportedAt": "2025-10-01T00:00:00Z"
      }
    ]
  }
}
```

## Implementation Plan

### Phase 1: Core Deduplication Infrastructure
1. Add `DeduplicationStrategy` abstraction
2. Implement `FingerprintDeduplicationStrategy`
3. Add `dedup_key` field to Transaction model and DB schema
4. Update `SyncService` to use deduplication strategy

### Phase 2: CSV Provider
1. Implement `CSVProvider` class
2. Add CSV parsing with flexible column detection
3. Implement account mapping logic
4. Generate fingerprint-based dedup keys

### Phase 3: CLI Integration
1. Add `tl import csv` command
2. Implement interactive column mapping
3. Implement interactive account mapping
4. Add preview and confirmation steps

### Phase 4: Testing
1. Unit tests for fingerprint generation
2. Unit tests for deduplication logic
3. Smoke tests for CSV import flow
4. Test cross-provider deduplication (CSV + SimpleFIN)

## Edge Cases & Considerations

### 1. Same Transaction, Different Sources
- SimpleFIN transaction with external_id
- Same transaction in CSV file
- **Solution**: Composite strategy checks both external_id and fingerprint

### 2. CSV Re-imports
- User imports same CSV file twice
- **Solution**: Fingerprint deduplication prevents duplicates

### 3. Pending vs Posted Transactions
- CSV might have pending transactions that later post with different amounts
- **Solution**: Include transaction date in fingerprint; pending transactions will have different dates when they post

### 4. Date Format Variations
- Different CSV date formats
- **Solution**: Support common formats, let user specify if auto-detection fails

### 5. Account Identification
- CSV files may not have consistent account identifiers
- **Solution**: Interactive mapping, save templates for reuse

### 6. Currency Handling
- CSV files may have different currencies
- **Solution**: Default to USD, allow user override during account mapping

## Migration Strategy

### Backward Compatibility
- Existing SimpleFIN integrations continue to work
- `external_ids` field remains unchanged
- `dedup_key` is optional (nullable field)

### Data Migration
- No migration needed for existing data
- New imports will populate `dedup_key`
- Old transactions without `dedup_key` will use legacy external_ids logic

### Gradual Rollout
1. Deploy deduplication infrastructure (no user impact)
2. Deploy CSV provider (opt-in feature)
3. Migrate existing SimpleFIN to use dedup_key (background job)

## Alternative Approaches Considered

### Alternative 1: Fuzzy Matching
- Use similarity scoring for descriptions
- **Rejected**: Too complex, high false positive rate

### Alternative 2: Rule-Based System
- Users define custom deduplication rules
- **Rejected**: Too complex for initial implementation, could be added later

### Alternative 3: Store Raw CSV
- Import CSV as-is, deduplicate in query layer
- **Rejected**: Violates single source of truth principle, complicates queries

## Success Criteria

1. ✅ Users can import CSV files from any financial institution
2. ✅ No duplicate transactions when re-importing same CSV
3. ✅ No duplicate transactions across CSV and SimpleFIN
4. ✅ Hexagonal architecture maintained (no CSV-specific logic in service layer)
5. ✅ Column and account mapping is user-friendly
6. ✅ Import settings are saved and reusable

## Open Questions

1. Should we support scheduled CSV imports (e.g., watch a folder)?
   - **Decision needed**: Defer to future iteration

2. Should we support CSV export as well?
   - **Decision needed**: Not in scope for this task

3. How to handle CSV files with multiple accounts?
   - **Decision needed**: Require account column in CSV or manual mapping per import

4. Should dedup_key be user-visible or internal?
   - **Decision needed**: Internal only, expose as "fingerprint" in debug mode
