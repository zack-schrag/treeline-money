"""CSV import command handler - Interactive mode."""

import asyncio
import os
from pathlib import Path
from uuid import UUID
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from treeline.app.service import AccountService, ImportService
from treeline.theme import get_theme
from treeline.domain import Transaction, Account

console = Console()
theme = get_theme()


def prompt_for_file_path(prompt_text: str = "") -> str:
    """Prompt user for a file path with autocomplete.

    Args:
        prompt_text: The prompt text to display (plain text, no Rich markup)

    Returns:
        The file path entered by the user
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import completion_is_selected
    import os

    # PathCompleter with expanduser=True handles ~ expansion
    completer = PathCompleter(expanduser=True, only_directories=False)

    # Create custom key bindings to handle Enter on directory selections
    kb = KeyBindings()

    @kb.add("enter", filter=completion_is_selected)
    def _(event):
        """When Enter is pressed on a selected completion, insert it and continue editing."""
        # Get the current completion
        completion = event.current_buffer.complete_state.current_completion
        if completion:
            # Insert the completion text
            event.current_buffer.apply_completion(completion)

            # If it's a directory and doesn't end with /, add one
            current_text = event.current_buffer.text
            expanded_path = os.path.expanduser(current_text)
            if os.path.isdir(expanded_path) and not current_text.endswith("/"):
                event.current_buffer.insert_text("/")
        # Don't accept the input - let user continue typing

    session = PromptSession(completer=completer, key_bindings=kb)

    if prompt_text:
        return session.prompt(f"{prompt_text}: ")
    else:
        return session.prompt(">: ")


def handle_import_command(
    import_service: ImportService, account_service: AccountService
) -> None:
    """
    Handle interactive CSV import.

    This is CLI-specific presentation logic:
    - Prompts for user input
    - Displays previews and results
    - Handles interactive workflow (preview → confirm → import)

    All business logic is delegated to ImportService.
    """
    # STEP 1: Collect parameters (CLI presentation logic)

    # 1a. Get file path
    console.print(f"\n[{theme.ui_header}]CSV Import[/{theme.ui_header}]\n")
    console.print(f"[{theme.info}]Enter path to CSV file:[/{theme.info}]")

    try:
        file_path = prompt_for_file_path("")
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    if not file_path:
        console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    # Validate file exists
    expanded_path = os.path.expanduser(file_path)
    csv_path = Path(expanded_path)
    if not csv_path.exists():
        console.print(
            f"[{theme.error}]Error: File not found: {file_path}[/{theme.error}]\n"
        )
        return

    # 1b. Get account selection
    console.print(f"\n[{theme.muted}]Fetching accounts...[/{theme.muted}]")
    accounts_result = asyncio.run(account_service.get_accounts())

    if not accounts_result.success:
        console.print(
            f"[{theme.error}]Error fetching accounts: {accounts_result.error}[/{theme.error}]\n"
        )
        return

    existing_accounts = accounts_result.data or []

    # Prompt for account selection (allows creating new account)
    account_id = prompt_account_selection(existing_accounts)

    if not account_id:
        console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
        return

    # Handle account creation
    if account_id == "CREATE_NEW":
        account_details = prompt_create_account()
        if not account_details:
            console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
            return

        # Create account via service
        console.print(f"\n[{theme.muted}]Creating account...[/{theme.muted}]")
        create_result = asyncio.run(
            account_service.create_account(
                name=account_details["name"],
                account_type=account_details["account_type"],
                institution=account_details.get("institution"),
                currency=account_details["currency"],
            )
        )

        if not create_result.success:
            console.print(
                f"[{theme.error}]Error creating account: {create_result.error}[/{theme.error}]\n"
            )
            return

        account_id = create_result.data.id
        console.print(
            f"[{theme.success}]✓ Created account '{account_details['name']}' ({account_details['account_type']})[/{theme.success}]"
        )

    # 1c. Column mapping - auto-detect (CLI responsibility to collect params)
    console.print(f"\n[{theme.muted}]Detecting CSV columns...[/{theme.muted}]")
    detect_result = asyncio.run(
        import_service.detect_columns(source_type="csv", file_path=str(csv_path))
    )

    if not detect_result.success:
        console.print(
            f"[{theme.error}]Error detecting columns: {detect_result.error}[/{theme.error}]\n"
        )
        return

    column_mapping = detect_result.data

    # Show detected columns
    console.print(f"\n[{theme.success}]Detected columns:[/{theme.success}]")
    for field, column in column_mapping.items():
        console.print(f"  {field}: {column}")

    if not column_mapping.get("date") or (
        not column_mapping.get("amount") and not column_mapping.get("debit")
    ):
        console.print(
            f"\n[{theme.warning}]Warning: Required columns not detected![/{theme.warning}]"
        )
        console.print(
            f"[{theme.muted}]For manual column mapping, use scriptable mode:[/{theme.muted}]"
        )
        console.print(
            f'[{theme.muted}]  tl import {csv_path.name} --date-column "YourDateColumn" --amount-column "YourAmountColumn"[/{theme.muted}]\n'
        )
        return

    # 1d. Sign flipping (start with default, allow changing in preview loop)
    flip_signs = False
    debit_negative = False

    # STEP 2: Interactive preview loop (CLI workflow)

    show_initial_preview = True  # Track whether to show initial 5 or not
    while True:
        # Get preview from service
        console.print(f"\n[{theme.muted}]Generating preview...[/{theme.muted}]")

        preview_result = asyncio.run(
            import_service.preview_csv_import(
                file_path=str(csv_path),
                column_mapping=column_mapping,
                date_format="auto",
                limit=15,  # Get more for better preview
                flip_signs=flip_signs,
                debit_negative=debit_negative,
            )
        )

        if not preview_result.success:
            console.print(
                f"[{theme.error}]Error: {preview_result.error}[/{theme.error}]\n"
            )
            return

        preview_txs = preview_result.data

        # Check if we got any transactions
        if len(preview_txs) == 0:
            console.print(
                f"\n[{theme.error}]No transactions found in CSV![/{theme.error}]"
            )
            console.print(f"[{theme.muted}]This could mean:[/{theme.muted}]")
            console.print(f"  - The CSV has no data rows")
            console.print(f"  - Date or amount parsing failed")
            console.print(
                f"\n[{theme.muted}]Try scriptable mode with explicit columns:[/{theme.muted}]"
            )
            console.print(
                f'[{theme.muted}]  tl import {csv_path.name} --preview --date-column "YourDateColumn" --amount-column "YourAmountColumn"[/{theme.muted}]\n'
            )
            return

        # Display preview (CLI presentation) - only show initial 5 on first iteration
        if show_initial_preview:
            console.print(
                f"\n[{theme.ui_header}]Preview - First 5 Transactions:[/{theme.ui_header}]\n"
            )
            display_preview_table(preview_txs[:5])
            console.print(
                f"\n[{theme.muted}]({len(preview_txs)} total transactions in file)[/{theme.muted}]"
            )
            console.print(f"[{theme.ui_header}]Preview Check[/{theme.ui_header}]")
            console.print(
                f"[{theme.muted}]Spending should appear as NEGATIVE ({theme.negative_amount}), income/refunds as POSITIVE ({theme.positive_amount})[/{theme.muted}]\n"
            )

        # Interactive menu (CLI workflow)
        console.print(f"[{theme.info}]What would you like to do?[/{theme.info}]")
        console.print("  [1] Proceed with import")
        console.print("  [2] View more transactions (next 10)")
        console.print("  [3] Flip all signs (if spending shows positive)")
        console.print("  [4] Negate debits (for unsigned debit/credit CSVs)")
        console.print("  [5] Cancel import")
        console.print(f"[{theme.muted}](Press Ctrl+C to cancel)[/{theme.muted}]")

        try:
            choice = Prompt.ask(
                f"\n[{theme.info}]Choice[/{theme.info}]",
                choices=["1", "2", "3", "4", "5"],
                default="1",
            )
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{theme.warning}]Import cancelled[/{theme.warning}]\n")
            return

        if choice == "1":
            break  # Proceed to import
        elif choice == "2":
            # Show more transactions
            console.print(
                f"\n[{theme.ui_header}]Extended Preview - First 15 Transactions:[/{theme.ui_header}]\n"
            )
            display_preview_table(preview_txs[:15])
            console.print()
            # Don't show initial preview again - user just saw extended preview
            show_initial_preview = False
        elif choice == "3":
            # Flip signs and loop will re-preview
            flip_signs = not flip_signs
            console.print(
                f"[{theme.muted}]Signs flipped, regenerating preview...[/{theme.muted}]"
            )
            # Show initial preview after flipping signs
            show_initial_preview = True
        elif choice == "4":
            # Toggle debit negation
            debit_negative = not debit_negative
            console.print(
                f"[{theme.muted}]Debit negation {'enabled' if debit_negative else 'disabled'}, regenerating preview...[/{theme.muted}]"
            )
            # Show initial preview after toggling
            show_initial_preview = True
        else:  # choice == "5"
            console.print(f"[{theme.warning}]Import cancelled[/{theme.warning}]\n")
            return

    # STEP 3: Execute import (business logic in service)

    console.print(f"\n[{theme.muted}]Importing transactions...[/{theme.muted}]")

    source_options = {
        "file_path": str(csv_path),
        "column_mapping": column_mapping,  # Already detected
        "date_format": "auto",
        "flip_signs": flip_signs,
        "debit_negative": debit_negative,
    }

    import_result = asyncio.run(
        import_service.import_transactions(
            source_type="csv",
            account_id=account_id,
            source_options=source_options,
        )
    )

    # STEP 4: Display result (CLI presentation)

    if not import_result.success:
        console.print(
            f"\n[{theme.error}]Error: {import_result.error}[/{theme.error}]\n"
        )
        return

    stats = import_result.data

    console.print(f"\n[{theme.success}]✓ Import complete![/{theme.success}]")
    console.print(f"  Discovered: {stats['discovered']} transactions")
    console.print(f"  Imported: {stats['imported']} new transactions")
    console.print(f"  Skipped: {stats['skipped']} duplicates\n")


# Helper functions (CLI presentation logic)


ACCOUNT_TYPES = ["depository", "credit", "investment", "loan", "other"]


def prompt_create_account() -> Optional[Dict[str, Any]]:
    """Prompt user to create a new account.

    Returns:
        Dict with account details, or None if cancelled
    """
    console.print(f"\n[{theme.info}]Create new account:[/{theme.info}]")

    try:
        # Account name (required)
        account_name = Prompt.ask(f"[{theme.info}]Account name[/{theme.info}]")
        if not account_name.strip():
            console.print(
                f"[{theme.error}]Account name cannot be empty[/{theme.error}]"
            )
            return None

        # Institution (optional)
        institution = Prompt.ask(
            f"[{theme.info}]Institution (optional, press Enter to skip)[/{theme.info}]",
            default="",
        )

        # Account type (guided selection)
        console.print(f"\n[{theme.info}]Account type:[/{theme.info}]")
        for i, acc_type in enumerate(ACCOUNT_TYPES, 1):
            console.print(f"  [{i}] {acc_type}")

        type_choice = Prompt.ask(
            f"[{theme.info}]Choose account type (1-{len(ACCOUNT_TYPES)})[/{theme.info}]",
            default="1",
        )

        try:
            type_idx = int(type_choice) - 1
            if 0 <= type_idx < len(ACCOUNT_TYPES):
                account_type = ACCOUNT_TYPES[type_idx]
            else:
                console.print(f"[{theme.error}]Invalid account type[/{theme.error}]")
                return None
        except ValueError:
            console.print(f"[{theme.error}]Invalid account type[/{theme.error}]")
            return None

        # Currency (default USD)
        currency = Prompt.ask(
            f"[{theme.info}]Currency[/{theme.info}]", default="USD"
        ).upper()

        return {
            "name": account_name.strip(),
            "institution": institution.strip() if institution.strip() else None,
            "account_type": account_type,
            "currency": currency,
        }

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]")
        return None


def prompt_account_selection(accounts: List[Account]) -> Optional[UUID]:
    """Display accounts and get user selection.

    Returns:
        Account UUID if selected, None if cancelled, or "CREATE_NEW" sentinel if user wants to create new account
    """
    console.print(f"\n[{theme.info}]Select account to import into:[/{theme.info}]")
    console.print(f"[{theme.muted}](Press Ctrl+C to cancel)[/{theme.muted}]\n")

    # If no accounts exist, skip straight to creating one
    if not accounts:
        console.print(
            f"[{theme.muted}]No accounts found. Let's create one.[/{theme.muted}]"
        )
        try:
            Prompt.ask(
                f"\n[{theme.info}]Press Enter to continue[/{theme.info}]", default=""
            )
            return "CREATE_NEW"
        except (KeyboardInterrupt, EOFError):
            return None

    # Show existing accounts with numbers
    for i, account in enumerate(accounts, 1):
        institution = (
            f" - {account.institution_name}" if account.institution_name else ""
        )
        account_type_display = (
            f" ({account.account_type})" if account.account_type else ""
        )
        console.print(f"  [{i}] {account.name}{institution}{account_type_display}")

    # Add "create new" option at the bottom
    console.print(f"  [c] Create new account")

    try:
        account_choice = Prompt.ask(
            f"\n[{theme.info}]Choose account (1-{len(accounts)} or 'c' to create)[/{theme.info}]",
            default="1",
        )
    except (KeyboardInterrupt, EOFError):
        return None

    # Check if user wants to create new account
    if account_choice.lower() == "c":
        return "CREATE_NEW"  # Sentinel value

    try:
        account_idx = int(account_choice) - 1
        if 0 <= account_idx < len(accounts):
            return accounts[account_idx].id
    except ValueError:
        pass

    console.print(f"[{theme.error}]Invalid account selection[/{theme.error}]")
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

        # Use proper sign placement: -$XX.XX not $-XX.XX
        if tx.amount < 0:
            amount_str = f"-${abs(tx.amount):,.2f}"
            amount_style = theme.negative_amount
        else:
            amount_str = f"${tx.amount:,.2f}"
            amount_style = theme.positive_amount

        table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

    console.print(table)
