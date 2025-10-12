"""CSV import command handler."""

import asyncio
import os
from pathlib import Path
from uuid import UUID

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def is_authenticated():
    """Check if user is authenticated."""
    from treeline.cli import is_authenticated as _is_authenticated
    return _is_authenticated()


def get_current_user_id():
    """Get current user ID."""
    from treeline.cli import get_current_user_id as _get_current_user_id
    return _get_current_user_id()


def handle_import_command() -> None:
    """Handle /import command - import transactions from CSV."""
    import os
    from pathlib import Path

    if not is_authenticated():
        console.print(f"[{theme.error}]Error: You must be logged in to import data.[/{theme.error}]")
        console.print(f"[{theme.muted}]Run /login to authenticate[/{theme.muted}]\n")
        return

    user_id = get_current_user_id()
    if not user_id:
        console.print(f"[{theme.error}]Error: Could not get user ID[/{theme.error}]\n")
        return

    container = get_container()
    import_service = container.import_service()
    account_service = container.account_service()

    # Step 1: Get CSV file path
    console.print(f"\n[{theme.ui_header}]CSV Import[/{theme.ui_header}]\n")

    # Use prompt_toolkit for file path input with autocomplete
    from treeline.cli import prompt_for_file_path
    console.print(f"[{theme.info}]Enter path to CSV file:[/{theme.info}]")
    try:
        file_path = prompt_for_file_path("")
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    if not file_path:
        console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    # Check if file exists - expand ~ manually using os.path
    expanded_path = os.path.expanduser(file_path)
    csv_path = Path(expanded_path)
    if not csv_path.exists():
        console.print(f"[{theme.error}]Error: File not found: {file_path}[/{theme.error}]\n")
        return

    # Step 2: Get or select account to import into
    console.print(f"\n[{theme.muted}]Fetching accounts...[/{theme.muted}]")
    accounts_result = asyncio.run(account_service.get_accounts(UUID(user_id)))

    if not accounts_result.success or not accounts_result.data:
        console.print(f"[{theme.error}]No accounts found. Please sync with SimpleFIN first.[/{theme.error}]\n")
        return

    accounts = accounts_result.data

    # Display accounts for selection
    console.print(f"\n[{theme.info}]Select account to import into:[/{theme.info}]")
    console.print(f"[{theme.muted}](Press Ctrl+C to cancel)[/{theme.muted}]")
    for i, account in enumerate(accounts, 1):
        console.print(f"  [{i}] {account.name}" + (f" - {account.institution_name}" if account.institution_name else ""))

    try:
        account_choice = Prompt.ask(f"\n[{theme.info}]Account number[/{theme.info}]", default="1")
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    try:
        account_idx = int(account_choice) - 1
        if account_idx < 0 or account_idx >= len(accounts):
            console.print(f"[{theme.error}]Invalid account selection[/{theme.error}]\n")
            return
        target_account = accounts[account_idx]
    except ValueError:
        console.print(f"[{theme.error}]Invalid account selection[/{theme.error}]\n")
        return

    # Step 3: Auto-detect columns and show preview
    csv_provider = container.provider_registry()["csv"]

    console.print(f"\n[{theme.muted}]Detecting CSV columns...[/{theme.muted}]")
    detect_result = csv_provider.detect_columns(str(csv_path))

    if not detect_result.success:
        console.print(f"[{theme.error}]Error detecting columns: {detect_result.error}[/{theme.error}]\n")
        return

    column_mapping = detect_result.data
    flip_signs = False

    if not column_mapping.get("date") or not (column_mapping.get("amount") or (column_mapping.get("debit") and column_mapping.get("credit"))):
        console.print(f"[{theme.warning}]Warning: Could not auto-detect all required columns[/{theme.warning}]")
        console.print(f"[{theme.muted}]You'll need to manually specify column mapping[/{theme.muted}]\n")
        # TODO: Fallback to manual mapping
        return

    # Show detected columns
    console.print(f"\n[{theme.success}]✓ Detected columns:[/{theme.success}]")
    for key, value in column_mapping.items():
        if value:
            console.print(f"  {key}: {value}")

    # Preview first 5 transactions
    console.print(f"\n[{theme.muted}]Loading preview...[/{theme.muted}]")

    preview_result = csv_provider.preview_transactions(
        str(csv_path),
        column_mapping,
        date_format="auto",
        limit=5,
        flip_signs=flip_signs
    )

    if not preview_result.success:
        console.print(f"[{theme.error}]Error generating preview: {preview_result.error}[/{theme.error}]\n")
        return

    preview_txs = preview_result.data

    if not preview_txs:
        console.print(f"[{theme.warning}]No transactions found in CSV[/{theme.warning}]\n")
        return

    # Display preview table
    console.print(f"\n[{theme.ui_header}]Preview - First 5 Transactions:[/{theme.ui_header}]\n")

    preview_table = Table(show_header=True, box=None, padding=(0, 1))
    preview_table.add_column("Date", width=12)
    preview_table.add_column("Description", width=40)
    preview_table.add_column("Amount", justify="right", width=15)

    for tx in preview_txs:
        date_str = tx.transaction_date.strftime("%Y-%m-%d")
        desc = (tx.description or "")[:38]

        # Use proper sign placement: -$XX.XX not $-XX.XX
        if tx.amount < 0:
            amount_str = f"-${abs(tx.amount):,.2f}"
        else:
            amount_str = f"${tx.amount:,.2f}"

        # Color code: negative = red, positive = green
        amount_style = theme.negative_amount if tx.amount < 0 else theme.positive_amount
        preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

    console.print(preview_table)

    # Step 4: Validate preview with combined options
    console.print(f"\n[{theme.ui_header}]Preview Check[/{theme.ui_header}]")
    console.print(f"[{theme.muted}]Spending should appear as NEGATIVE ({theme.negative_amount}), income/refunds as POSITIVE ({theme.positive_amount})[/{theme.muted}]\n")

    # Main preview validation loop
    while True:
        console.print(f"[{theme.info}]What would you like to do?[/{theme.info}]")
        console.print("  [1] Proceed with import")
        console.print("  [2] View more transactions (next 10)")
        console.print("  [3] Flip all signs (if spending shows positive)")
        console.print("  [4] Try different column mapping")
        console.print("  [5] Cancel import")
        console.print(f"[{theme.muted}](Press Ctrl+C to cancel)[/{theme.muted}]")

        try:
            choice = Prompt.ask(f"\n[{theme.info}]Choice[/{theme.info}]", choices=["1", "2", "3", "4", "5"], default="1")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
            return

        if choice == "1":
            # Proceed with import
            break

        elif choice == "2":
            # Show more transactions
            console.print(f"\n[{theme.muted}]Loading more transactions...[/{theme.muted}]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=15,  # Show 15 total (5 already shown + 10 more)
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[{theme.error}]Error generating preview: {preview_result.error}[/{theme.error}]\n")
                continue

            preview_txs = preview_result.data

            # Display extended preview
            console.print(f"\n[{theme.ui_header}]Extended Preview - First 15 Transactions:[/{theme.ui_header}]\n")

            preview_table = Table(show_header=True, box=None, padding=(0, 1))
            preview_table.add_column("Date", width=12)
            preview_table.add_column("Description", width=40)
            preview_table.add_column("Amount", justify="right", width=15)

            for tx in preview_txs:
                date_str = tx.transaction_date.strftime("%Y-%m-%d")
                desc = (tx.description or "")[:38]
                # Use proper sign placement
                if tx.amount < 0:
                    amount_str = f"-${abs(tx.amount):,.2f}"
                else:
                    amount_str = f"${tx.amount:,.2f}"
                amount_style = theme.negative_amount if tx.amount < 0 else theme.positive_amount
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "3":
            # Flip signs
            flip_signs = True

            # Show preview with flipped signs
            console.print(f"\n[{theme.muted}]Regenerating preview with flipped signs...[/{theme.muted}]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=5,
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[{theme.error}]Error generating preview: {preview_result.error}[/{theme.error}]\n")
                continue

            preview_txs = preview_result.data

            # Display updated preview
            console.print(f"\n[{theme.ui_header}]Updated Preview - First 5 Transactions:[/{theme.ui_header}]\n")

            preview_table = Table(show_header=True, box=None, padding=(0, 1))
            preview_table.add_column("Date", width=12)
            preview_table.add_column("Description", width=40)
            preview_table.add_column("Amount", justify="right", width=15)

            for tx in preview_txs:
                date_str = tx.transaction_date.strftime("%Y-%m-%d")
                desc = (tx.description or "")[:38]
                # Use proper sign placement
                if tx.amount < 0:
                    amount_str = f"-${abs(tx.amount):,.2f}"
                else:
                    amount_str = f"${tx.amount:,.2f}"
                amount_style = theme.negative_amount if tx.amount < 0 else theme.positive_amount
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "4":
            # Manual column mapping not implemented
            console.print(f"[{theme.warning}]Manual column mapping not yet implemented[/{theme.warning}]\n")
            continue

        else:  # choice == "5"
            # Cancel
            console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
            return

    # Step 4.5: Check for potential duplicates
    console.print(f"\n[{theme.muted}]Checking for potential duplicates...[/{theme.muted}]")

    # First, get the transactions that would be imported (need to map to target account)
    preview_with_account = []
    for tx in preview_txs:
        tx_dict = tx.model_dump()
        tx_dict["account_id"] = target_account.id
        # Remove fingerprint to force recalculation
        ext_ids = dict(tx_dict.get("external_ids", {}))
        ext_ids.pop("fingerprint", None)
        tx_dict["external_ids"] = ext_ids
        from treeline.domain import Transaction
        preview_with_account.append(Transaction(**tx_dict))

    potential_dupes_result = asyncio.run(import_service.find_potential_duplicates(
        user_id=UUID(user_id),
        account_id=target_account.id,
        transactions=preview_with_account
    ))

    if potential_dupes_result.success and potential_dupes_result.data:
        potential_dupes = potential_dupes_result.data

        console.print(f"\n[{theme.warning}]⚠ Found {len(potential_dupes)} potential duplicate(s)[/{theme.warning}]")
        console.print(f"[{theme.muted}]These transactions have the same date and amount but different descriptions.[/{theme.muted}]\n")

        # Show each potential duplicate
        for i, dupe_info in enumerate(potential_dupes, 1):
            csv_tx = dupe_info["csv_transaction"]
            existing_tx = dupe_info["existing_transaction"]

            console.print(f"[{theme.ui_header}]Potential Duplicate {i}/{len(potential_dupes)}:[/{theme.ui_header}]")

            comparison_table = Table(show_header=True, box=None, padding=(0, 2))
            comparison_table.add_column("", style=theme.muted)
            comparison_table.add_column("CSV (New)", style=theme.warning)
            comparison_table.add_column("Existing", style=theme.success)

            comparison_table.add_row(
                "Date",
                csv_tx.transaction_date.strftime("%Y-%m-%d"),
                existing_tx.transaction_date.strftime("%Y-%m-%d")
            )
            comparison_table.add_row(
                "Amount",
                f"${csv_tx.amount:.2f}",
                f"${existing_tx.amount:.2f}"
            )
            comparison_table.add_row(
                "Description",
                csv_tx.description or "",
                existing_tx.description or ""
            )

            console.print(comparison_table)

            # Ask user if they want to import this transaction
            try:
                import_anyway = Confirm.ask(
                    f"\n[{theme.info}]Import this transaction anyway?[/{theme.info}]",
                    default=False
                )
            except (KeyboardInterrupt, EOFError):
                console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
                return

            if not import_anyway:
                # Mark this transaction to skip
                dupe_info["skip"] = True
                console.print(f"[{theme.muted}]Will skip this transaction[/{theme.muted}]\n")
            else:
                dupe_info["skip"] = False
                console.print(f"[{theme.muted}]Will import this transaction[/{theme.muted}]\n")

        # Filter out transactions user chose to skip
        skip_ids = {dupe["csv_transaction"].id for dupe in potential_dupes if dupe.get("skip")}
        if skip_ids:
            console.print(f"\n[{theme.muted}]Skipping {len(skip_ids)} potential duplicate(s) as requested[/{theme.muted}]")
            # Note: We'll need to modify the import flow to respect this
            # For now, we'll just warn the user
            console.print(f"[{theme.warning}]Note: The import will proceed with all transactions.[/{theme.warning}]")
            console.print(f"[{theme.warning}]Manual duplicate skipping will be implemented in a future update.[/{theme.warning}]\n")

    # Step 5: Execute import
    console.print(f"\n[{theme.muted}]Importing transactions...[/{theme.muted}]")

    import_result = asyncio.run(import_service.import_transactions(
        user_id=UUID(user_id),
        source_type="csv",
        account_id=target_account.id,
        source_options={
            "file_path": str(csv_path),
            "column_mapping": column_mapping,
            "date_format": "auto",
            "flip_signs": flip_signs,
        }
    ))

    if import_result.success:
        stats = import_result.data
        console.print(f"\n[{theme.success}]✓ Import complete![/{theme.success}]")
        console.print(f"  Discovered: {stats['discovered']} transactions")
        console.print(f"  Imported: {stats['imported']} new transactions")
        console.print(f"  Skipped: {stats['skipped']} duplicates\n")
    else:
        console.print(f"\n[{theme.error}]Error: {import_result.error}[/{theme.error}]\n")
