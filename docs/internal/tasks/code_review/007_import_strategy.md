# Import Command Refactor Strategy

## Current State Analysis

### Files Involved
1. **cli.py** (lines 1332-1500) - Command definition + scriptable mode
2. **commands/import_csv.py** (400 lines) - Interactive mode implementation
3. **app/service.py** - ImportService with helper methods

### Current Flow - Scriptable Mode (cli.py)

```python
@app.command(name="import")
def import_command(file_path, account_id, date_column, ...):
    # Line 1368: Validate user
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

    # Line 1372: Route to interactive if no file_path
    if file_path is None:
        handle_import_command()  # Delegate to commands/
        return

    # Lines 1378-1383: Validate file exists
    csv_path = Path(file_path).expanduser()
    if not csv_path.exists():
        display_error(...)

    # Lines 1385-1387: Get services
    container = get_container()
    import_service = container.import_service()
    account_service = container.account_service()

    # Lines 1389-1415: Column mapping orchestration ❌
    if date_column or amount_column:
        column_mapping = {...}  # Manual
    else:
        detect_result = import_service.detect_csv_columns()  # Service call 1
        column_mapping = detect_result.data

    # Lines 1417-1430+: Account lookup orchestration ❌
    accounts_result = account_service.get_accounts(user_id)  # Service call 2
    target_account = find_by_id(account_id, accounts)

    # Later: Import call ❌
    import_service.import_transactions(...)  # Service call 3
```

**Problems**:
- 3+ service calls
- Orchestration logic (column detection, account lookup)
- Business logic in presentation layer

### Current Flow - Interactive Mode (commands/import_csv.py)

```python
def handle_import_command():
    # Lines 40-48: Auth check
    if not is_authenticated():
        display_error(...)
    user_id = get_current_user_id()

    # Lines 50-52: Get services
    import_service = container.import_service()
    account_service = container.account_service()

    # Lines 54-75: Get file path (presentation ✅)
    file_path = prompt_for_file_path()

    # Lines 77-84: Get accounts (orchestration ❌)
    accounts_result = account_service.get_accounts(user_id)  # Service call 1

    # Lines 87-107: Display accounts + get selection (presentation ✅)
    display_accounts(accounts)
    account_id = prompt_account_selection()

    # Lines 109-124: Detect columns (orchestration ❌)
    detect_result = import_service.detect_csv_columns(csv_path)  # Service call 2
    column_mapping = detect_result.data

    # Lines 132-175: Preview + display (orchestration ❌)
    preview_result = import_service.preview_csv_import(...)  # Service call 3
    display_preview(preview_result.data)

    # Lines 177-292: Interactive preview loop (presentation ✅)
    while True:
        choice = prompt_menu()
        if choice == "flip signs":
            flip_signs = True
            # Re-preview with flipped signs (orchestration ❌)
            preview_result = import_service.preview_csv_import(...)  # Service call 4

    # Lines 294-377: Check duplicates (orchestration ❌)
    potential_dupes = import_service.find_potential_duplicates(...)  # Service call 5
    display_duplicates(potential_dupes)
    skip_ids = prompt_duplicate_decisions()

    # Lines 378-401: Import (orchestration ❌)
    import_result = import_service.import_transactions(...)  # Service call 6
    display_results(import_result)
```

**Problems**:
- 6+ service calls
- Heavy orchestration (preview → confirm → duplicates → import)
- Business workflow logic in presentation layer

## Target Architecture

### New Service Method

```python
class ImportService:
    async def import_csv(
        self,
        user_id: UUID,
        file_path: str,
        account_id: UUID,
        column_mapping: Optional[Dict[str, str]] = None,
        flip_signs: bool = False,
        skip_transaction_ids: Optional[Set[UUID]] = None,
    ) -> Result[ImportResult]:
        """
        Import CSV transactions with auto-detection and validation.

        This is a complete business logic method - no UI concerns.
        Handles: validation, column detection, duplicate detection, import.

        Args:
            user_id: User performing import
            file_path: Path to CSV file
            account_id: Target account ID
            column_mapping: Optional manual column mapping (auto-detect if None)
            flip_signs: Whether to flip transaction signs
            skip_transaction_ids: Transaction IDs to skip (for duplicate handling)

        Returns:
            Result containing ImportResult with:
            - discovered: int (total transactions in CSV)
            - imported: int (new transactions imported)
            - skipped: int (duplicates skipped)
            - potential_duplicates: List[DuplicateInfo] (for UI to handle)
        """
        # 1. Validate account exists
        account_result = await self.repository.get_account(user_id, account_id)
        if not account_result.success:
            return Result(success=False, error=f"Account not found: {account_id}")

        # 2. Auto-detect columns if not provided
        if column_mapping is None:
            detect_result = await self.detect_csv_columns(file_path)
            if not detect_result.success:
                return detect_result
            column_mapping = detect_result.data

        # 3. Validate column mapping has required fields
        if not column_mapping.get("date"):
            return Result(success=False, error="Missing date column")
        if not (column_mapping.get("amount") or
                (column_mapping.get("debit") and column_mapping.get("credit"))):
            return Result(success=False, error="Missing amount/debit/credit columns")

        # 4. Parse and preview all transactions (business logic)
        preview_result = await self.preview_csv_import(
            file_path=file_path,
            column_mapping=column_mapping,
            date_format="auto",
            limit=None,  # All transactions
            flip_signs=flip_signs
        )
        if not preview_result.success:
            return preview_result

        all_transactions = preview_result.data

        # 5. Map transactions to target account
        mapped_transactions = []
        for tx in all_transactions:
            tx_dict = tx.model_dump()
            tx_dict["account_id"] = account_id
            # Remove fingerprint to force recalculation
            ext_ids = dict(tx_dict.get("external_ids", {}))
            ext_ids.pop("fingerprint", None)
            tx_dict["external_ids"] = ext_ids
            mapped_transactions.append(Transaction(**tx_dict))

        # 6. Check for potential duplicates (business logic)
        duplicates_result = await self.find_potential_duplicates(
            user_id=user_id,
            account_id=account_id,
            transactions=mapped_transactions
        )
        if not duplicates_result.success:
            return duplicates_result

        potential_duplicates = duplicates_result.data or []

        # 7. Filter out transactions user wants to skip
        if skip_transaction_ids:
            mapped_transactions = [
                tx for tx in mapped_transactions
                if tx.id not in skip_transaction_ids
            ]

        # 8. Import transactions (business logic)
        import_result = await self.import_transactions(
            user_id=user_id,
            source_type="csv",
            account_id=account_id,
            source_options={
                "file_path": file_path,
                "column_mapping": column_mapping,
                "date_format": "auto",
                "flip_signs": flip_signs,
            }
        )

        if not import_result.success:
            return import_result

        # 9. Return comprehensive result
        return Result(success=True, data={
            **import_result.data,
            "potential_duplicates": potential_duplicates,
        })
```

### New CLI Command (Scriptable Mode)

```python
@app.command(name="import")
def import_command(
    file_path: str = typer.Argument(None, help="Path to CSV file"),
    account_id: str = typer.Option(None, "--account-id", help="Account ID"),
    date_column: str = typer.Option(None, "--date-column", help="Date column"),
    amount_column: str = typer.Option(None, "--amount-column", help="Amount column"),
    description_column: str = typer.Option(None, "--description-column", help="Description column"),
    debit_column: str = typer.Option(None, "--debit-column", help="Debit column"),
    credit_column: str = typer.Option(None, "--credit-column", help="Credit column"),
    flip_signs: bool = typer.Option(False, "--flip-signs", help="Flip signs"),
    preview: bool = typer.Option(False, "--preview", help="Preview only"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Import transactions from CSV file."""
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

    # INTERACTIVE MODE: Route to interactive handler
    if file_path is None:
        from treeline.commands.import_csv import handle_import_command
        handle_import_command()
        return

    # SCRIPTABLE MODE: Collect parameters and call service

    # Validate file exists
    csv_path = Path(file_path).expanduser()
    if not csv_path.exists():
        display_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    # Build column mapping (if provided)
    column_mapping = None
    if date_column or amount_column or debit_column or credit_column:
        column_mapping = {}
        if date_column:
            column_mapping["date"] = date_column
        if amount_column:
            column_mapping["amount"] = amount_column
        if description_column:
            column_mapping["description"] = description_column
        if debit_column:
            column_mapping["debit"] = debit_column
        if credit_column:
            column_mapping["credit"] = credit_column

    # If account_id not provided, error in scriptable mode
    if not account_id:
        display_error("--account-id is required in scriptable mode")
        raise typer.Exit(1)

    # SINGLE service call
    container = get_container()
    import_service = container.import_service()

    result = asyncio.run(import_service.import_csv(
        user_id=UUID(user_id),
        file_path=str(csv_path),
        account_id=UUID(account_id),
        column_mapping=column_mapping,
        flip_signs=flip_signs,
        preview_only=preview,
    ))

    # Display result
    if json_output:
        display_json(result.data)
    elif result.success:
        if preview:
            display_preview_table(result.data["preview"])
        else:
            display_import_success(result.data)
    else:
        display_error(result.error)
        raise typer.Exit(1)
```

### New Interactive Mode (commands/import_csv.py)

**Goal**: Preserve exact current UX, just reorganize the code

```python
def handle_import_command() -> None:
    """
    Handle interactive CSV import.

    This is CLI-specific presentation logic:
    - Prompts for user input
    - Displays previews and results
    - Handles interactive workflow (preview → confirm → import)

    All business logic is delegated to ImportService.
    """
    # Auth check (CLI concern)
    if not is_authenticated():
        console.print("[red]Error: Not authenticated[/red]")
        console.print("Run 'treeline login' first")
        return

    user_id = get_current_user_id()
    container = get_container()
    import_service = container.import_service()
    account_service = container.account_service()

    # STEP 1: Collect parameters (CLI presentation logic)

    # 1a. Get file path
    console.print("\n[bold]CSV Import[/bold]\n")
    file_path = prompt_for_file_path("Enter path to CSV file:")
    if not file_path:
        console.print("[yellow]Import cancelled[/yellow]")
        return

    csv_path = Path(os.path.expanduser(file_path))
    if not csv_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        return

    # 1b. Get account selection
    accounts_result = asyncio.run(account_service.get_accounts(UUID(user_id)))
    if not accounts_result.success or not accounts_result.data:
        console.print("[red]No accounts found. Please sync first.[/red]")
        return

    account_id = prompt_account_selection(accounts_result.data)
    if not account_id:
        return

    # 1c. Column mapping (let service auto-detect for now)
    column_mapping = None
    # TODO: Could add interactive column mapping UI here

    # 1d. Sign flipping (start with default)
    flip_signs = False

    # STEP 2: Interactive preview loop (CLI workflow)

    while True:
        # Get preview from service (business logic in service)
        console.print("\nDetecting columns and generating preview...")

        preview_result = asyncio.run(import_service.preview_csv_import(
            file_path=str(csv_path),
            column_mapping=column_mapping,
            date_format="auto",
            limit=15,  # Show more for better preview
            flip_signs=flip_signs
        ))

        if not preview_result.success:
            console.print(f"[red]Error: {preview_result.error}[/red]")
            return

        preview_txs = preview_result.data

        # Display preview (CLI presentation)
        display_preview_table(preview_txs[:5])
        console.print(f"\n[dim]({len(preview_txs)} total transactions in file)[/dim]")
        console.print("[yellow]Spending should be NEGATIVE, income POSITIVE[/yellow]\n")

        # Interactive menu (CLI workflow)
        console.print("What would you like to do?")
        console.print("  [1] Proceed with import")
        console.print("  [2] View more transactions (15)")
        console.print("  [3] Flip all signs")
        console.print("  [4] Cancel")

        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            break  # Proceed to import
        elif choice == "2":
            display_preview_table(preview_txs[:15])
        elif choice == "3":
            flip_signs = not flip_signs
            console.print(f"[dim]Signs flipped, regenerating preview...[/dim]")
            # Loop will re-preview
        else:
            console.print("[yellow]Import cancelled[/yellow]")
            return

    # STEP 3: Execute import (business logic in service)

    console.print("\nImporting transactions...")

    import_result = asyncio.run(import_service.import_csv(
        user_id=UUID(user_id),
        file_path=str(csv_path),
        account_id=account_id,
        column_mapping=column_mapping,
        flip_signs=flip_signs,
        skip_transaction_ids=None,  # No duplicate handling for now
    ))

    # STEP 4: Handle duplicates (CLI presentation + user decision)

    if import_result.success:
        stats = import_result.data
        potential_dupes = stats.get("potential_duplicates", [])

        if potential_dupes:
            console.print(f"\n[yellow]Found {len(potential_dupes)} potential duplicates[/yellow]")
            # TODO: Show duplicates and prompt user
            # For now, just warn
            console.print("[dim]Duplicates were automatically skipped[/dim]")

        # STEP 5: Display final result (CLI presentation)
        console.print(f"\n[green]✓ Import complete![/green]")
        console.print(f"  Discovered: {stats['discovered']} transactions")
        console.print(f"  Imported: {stats['imported']} new transactions")
        console.print(f"  Skipped: {stats['skipped']} duplicates\n")
    else:
        console.print(f"\n[red]Error: {import_result.error}[/red]\n")


# Helper functions (CLI presentation logic)

def prompt_account_selection(accounts: List[Account]) -> Optional[UUID]:
    """Display accounts and get user selection."""
    console.print("\nSelect account to import into:")
    for i, account in enumerate(accounts, 1):
        console.print(f"  [{i}] {account.name}" +
                     (f" - {account.institution_name}" if account.institution_name else ""))

    choice = Prompt.ask("\nAccount number", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(accounts):
            return accounts[idx].id
    except ValueError:
        pass

    console.print("[red]Invalid selection[/red]")
    return None


def display_preview_table(transactions: List[Transaction]) -> None:
    """Display transaction preview table."""
    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("Date", width=12)
    table.add_column("Description", width=40)
    table.add_column("Amount", justify="right", width=15)

    for tx in transactions:
        date_str = tx.transaction_date.strftime("%Y-%m-%d")
        desc = (tx.description or "")[:38]

        if tx.amount < 0:
            amount_str = f"-${abs(tx.amount):,.2f}"
            amount_color = "red"
        else:
            amount_str = f"${tx.amount:,.2f}"
            amount_color = "green"

        table.add_row(date_str, desc, f"[{amount_color}]{amount_str}[/{amount_color}]")

    console.print(table)
```

## Implementation Plan

### Step 1: Add new service method
- File: `src/treeline/app/service.py`
- Add `ImportService.import_csv()` method
- Keep existing helper methods (detect_columns, preview, etc)
- Test the service method in isolation

### Step 2: Refactor scriptable mode
- File: `src/treeline/cli.py`
- Simplify `import_command()` to ~50 lines
- Remove orchestration logic
- Single service call

### Step 3: Refactor interactive mode
- File: `src/treeline/commands/import_csv.py`
- Simplify `handle_import_command()` to ~100 lines
- Remove orchestration logic
- Two service calls: one for preview, one for import

### Step 4: Test
- Test scriptable: `tl import file.csv --account-id X`
- Test interactive: `tl import`
- Test preview: `tl import file.csv --preview`
- Run unit tests
- Run smoke tests

## Architecture Decisions (Based on "Business Logic vs CLI Logic" Test)

### 1. Preview in interactive mode
**Question**: Service call pattern?
**Answer**: Call service multiple times as needed (preview, re-preview with flipped signs, import)
**Reason**: Preview is a CLI concern (showing user what will happen). Business logic doesn't care about previews.

### 2. Duplicate handling
**Question**: Where does duplicate detection + user prompting belong?
**Analysis**:
- **Duplicate DETECTION** = Business logic (belongs in service)
  - Finding potential duplicates is core business logic
  - An API would need this too
- **Duplicate PROMPTING** = CLI logic (belongs in command)
  - Asking user "import this duplicate?" is CLI-specific
  - An API would just return the duplicates, let client decide

**Decision**:
- Service: Returns duplicates as part of preview/import result
- Command: Displays duplicates and prompts user for decisions
- Service: Accepts "skip_transaction_ids" parameter for final import

### 3. Column mapping
**Question**: Should interactive mode prompt for manual column mapping?
**Answer**: Yes, preserve current UX - auto-detect with option to manually specify
**Reason**: Current UX is good, just move the orchestration to service

### 4. Sign flipping re-preview
**Question**: How to handle preview → flip → re-preview workflow?
**Answer**: Keep current UX - allow re-previewing with different options
**Reason**: This is CLI-specific workflow, not business logic

### The Litmus Test Applied:

**"Could we build a web API or GUI with the same service?"**
- ✅ API endpoint: `POST /import/csv` with params → returns result
- ✅ GUI: Upload CSV → show preview → click import → done
- ✅ CLI: Interactive prompts → show preview → confirm → done

All three interfaces use the **same service methods**, just different presentation layers.

## Success Criteria

- [ ] New `ImportService.import_csv()` method contains ALL business logic
- [ ] Service method is interface-agnostic (could be used by API/GUI/CLI)
- [ ] Scriptable mode: Collect params → 1 service call → display
- [ ] Interactive mode: Present UI → service calls as needed → display
- [ ] CLI layer only contains presentation logic (prompts, display)
- [ ] Existing user experience is preserved (no UX changes)
- [ ] All tests pass
- [ ] Can answer "yes" to: "Could we build an API with this service layer?"
