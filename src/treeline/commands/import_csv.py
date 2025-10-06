"""CSV import command handler."""

import asyncio
import os
from pathlib import Path
from uuid import UUID

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


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
        console.print("[red]Error: You must be logged in to import data.[/red]")
        console.print("[dim]Run /login to authenticate[/dim]\n")
        return

    user_id = get_current_user_id()
    if not user_id:
        console.print("[red]Error: Could not get user ID[/red]\n")
        return

    container = get_container()
    import_service = container.import_service()
    repository = container.repository()

    # Step 1: Get CSV file path
    console.print("\n[bold cyan]CSV Import[/bold cyan]\n")
    file_path = Prompt.ask("[cyan]Enter path to CSV file[/cyan]")

    if not file_path:
        console.print("[yellow]Import cancelled[/yellow]\n")
        return

    # Check if file exists - expand ~ manually using os.path
    expanded_path = os.path.expanduser(file_path)
    csv_path = Path(expanded_path)
    if not csv_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]\n")
        return

    # Step 2: Get or select account to import into
    console.print("\n[dim]Fetching accounts...[/dim]")
    accounts_result = asyncio.run(repository.get_accounts(UUID(user_id)))

    if not accounts_result.success or not accounts_result.data:
        console.print("[red]No accounts found. Please sync with SimpleFIN first.[/red]\n")
        return

    accounts = accounts_result.data

    # Display accounts for selection
    console.print("\n[cyan]Select account to import into:[/cyan]")
    for i, account in enumerate(accounts, 1):
        console.print(f"  [{i}] {account.name}" + (f" - {account.institution_name}" if account.institution_name else ""))

    account_choice = Prompt.ask("\n[cyan]Account number[/cyan]", default="1")

    try:
        account_idx = int(account_choice) - 1
        if account_idx < 0 or account_idx >= len(accounts):
            console.print("[red]Invalid account selection[/red]\n")
            return
        target_account = accounts[account_idx]
    except ValueError:
        console.print("[red]Invalid account selection[/red]\n")
        return

    # Step 3: Auto-detect columns and show preview
    csv_provider = container.provider_registry()["csv"]

    console.print("\n[dim]Detecting CSV columns...[/dim]")
    detect_result = csv_provider.detect_columns(str(csv_path))

    if not detect_result.success:
        console.print(f"[red]Error detecting columns: {detect_result.error}[/red]\n")
        return

    column_mapping = detect_result.data
    flip_signs = False

    if not column_mapping.get("date") or not (column_mapping.get("amount") or (column_mapping.get("debit") and column_mapping.get("credit"))):
        console.print("[yellow]Warning: Could not auto-detect all required columns[/yellow]")
        console.print("[dim]You'll need to manually specify column mapping[/dim]\n")
        # TODO: Fallback to manual mapping
        return

    # Show detected columns
    console.print("\n[green]✓ Detected columns:[/green]")
    for key, value in column_mapping.items():
        if value:
            console.print(f"  {key}: {value}")

    # Preview first 5 transactions
    console.print("\n[dim]Loading preview...[/dim]")

    preview_result = csv_provider.preview_transactions(
        str(csv_path),
        column_mapping,
        date_format="auto",
        limit=5,
        flip_signs=flip_signs
    )

    if not preview_result.success:
        console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
        return

    preview_txs = preview_result.data

    if not preview_txs:
        console.print("[yellow]No transactions found in CSV[/yellow]\n")
        return

    # Display preview table
    console.print("\n[bold cyan]Preview - First 5 Transactions:[/bold cyan]\n")

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
        amount_style = "red" if tx.amount < 0 else "green"
        preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

    console.print(preview_table)

    # Step 4: Validate preview with combined options
    console.print("\n[bold cyan]Preview Check[/bold cyan]")
    console.print("[dim]Spending should appear as NEGATIVE (red), income/refunds as POSITIVE (green)[/dim]\n")

    # Main preview validation loop
    while True:
        console.print("[cyan]What would you like to do?[/cyan]")
        console.print("  [1] Proceed with import")
        console.print("  [2] View more transactions (next 10)")
        console.print("  [3] Flip all signs (if spending shows positive)")
        console.print("  [4] Try different column mapping")
        console.print("  [5] Cancel import")

        choice = Prompt.ask("\n[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            # Proceed with import
            break

        elif choice == "2":
            # Show more transactions
            console.print("\n[dim]Loading more transactions...[/dim]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=15,  # Show 15 total (5 already shown + 10 more)
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
                continue

            preview_txs = preview_result.data

            # Display extended preview
            console.print("\n[bold cyan]Extended Preview - First 15 Transactions:[/bold cyan]\n")

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
                amount_style = "red" if tx.amount < 0 else "green"
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "3":
            # Flip signs
            flip_signs = True

            # Show preview with flipped signs
            console.print("\n[dim]Regenerating preview with flipped signs...[/dim]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=5,
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
                continue

            preview_txs = preview_result.data

            # Display updated preview
            console.print("\n[bold cyan]Updated Preview - First 5 Transactions:[/bold cyan]\n")

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
                amount_style = "red" if tx.amount < 0 else "green"
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "4":
            # Manual column mapping not implemented
            console.print("[yellow]Manual column mapping not yet implemented[/yellow]\n")
            continue

        else:  # choice == "5"
            # Cancel
            console.print("[yellow]Import cancelled[/yellow]\n")
            return

    # Step 4.5: Check for potential duplicates
    console.print("\n[dim]Checking for potential duplicates...[/dim]")

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

        console.print(f"\n[yellow]⚠ Found {len(potential_dupes)} potential duplicate(s)[/yellow]")
        console.print("[dim]These transactions have the same date and amount but different descriptions.[/dim]\n")

        # Show each potential duplicate
        for i, dupe_info in enumerate(potential_dupes, 1):
            csv_tx = dupe_info["csv_transaction"]
            existing_tx = dupe_info["existing_transaction"]

            console.print(f"[bold cyan]Potential Duplicate {i}/{len(potential_dupes)}:[/bold cyan]")

            comparison_table = Table(show_header=True, box=None, padding=(0, 2))
            comparison_table.add_column("", style="dim")
            comparison_table.add_column("CSV (New)", style="yellow")
            comparison_table.add_column("Existing", style="green")

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
            import_anyway = Confirm.ask(
                f"\n[cyan]Import this transaction anyway?[/cyan]",
                default=False
            )

            if not import_anyway:
                # Mark this transaction to skip
                dupe_info["skip"] = True
                console.print("[dim]Will skip this transaction[/dim]\n")
            else:
                dupe_info["skip"] = False
                console.print("[dim]Will import this transaction[/dim]\n")

        # Filter out transactions user chose to skip
        skip_ids = {dupe["csv_transaction"].id for dupe in potential_dupes if dupe.get("skip")}
        if skip_ids:
            console.print(f"\n[dim]Skipping {len(skip_ids)} potential duplicate(s) as requested[/dim]")
            # Note: We'll need to modify the import flow to respect this
            # For now, we'll just warn the user
            console.print("[yellow]Note: The import will proceed with all transactions.[/yellow]")
            console.print("[yellow]Manual duplicate skipping will be implemented in a future update.[/yellow]\n")

    # Step 5: Execute import
    console.print("\n[dim]Importing transactions...[/dim]")

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
        console.print(f"\n[bold green]✓ Import complete![/bold green]")
        console.print(f"  Discovered: {stats['discovered']} transactions")
        console.print(f"  Imported: {stats['imported']} new transactions")
        console.print(f"  Skipped: {stats['skipped']} duplicates\n")

        # Write debug CSV
        import csv as csv_module
        from datetime import datetime as dt

        debug_file = Path.cwd() / f"import_debug_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(debug_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv_module.writer(f)
                writer.writerow(["Status", "Date", "Description", "Amount", "Fingerprint", "Existing Count"])

                # Write imported transactions
                for tx in stats.get('imported_transactions', []):
                    writer.writerow([
                        "IMPORTED",
                        tx.transaction_date.strftime("%Y-%m-%d"),
                        tx.description or "",
                        f"{tx.amount:.2f}",
                        tx.external_ids.get("fingerprint", ""),
                        "0"
                    ])

                # Write skipped transactions
                for skip_info in stats.get('skipped_transactions', []):
                    tx = skip_info['transaction']
                    writer.writerow([
                        "SKIPPED",
                        tx.transaction_date.strftime("%Y-%m-%d"),
                        tx.description or "",
                        f"{tx.amount:.2f}",
                        skip_info['fingerprint'],
                        str(skip_info['existing_count'])
                    ])

            console.print(f"[dim]Debug report written to: {debug_file}[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not write debug file: {e}[/yellow]\n")
    else:
        console.print(f"\n[red]Error: {import_result.error}[/red]\n")
