"""Shared utilities for loading and applying auto-taggers."""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Callable, Dict, List

from treeline.domain import Transaction
from treeline.utils import get_treeline_dir


def load_taggers() -> List[Callable[..., List[str]]]:
    """Load all tagger functions from ~/.treeline/taggers/

    Auto-discovers all functions that start with "tag_" prefix.

    Returns:
        List of tagger functions
    """
    taggers: List[Callable[..., List[str]]] = []
    taggers_dir = get_treeline_dir() / "taggers"

    if not taggers_dir.exists():
        return taggers

    for tagger_file in taggers_dir.glob("*.py"):
        if tagger_file.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(
                f"user_taggers.{tagger_file.stem}", tagger_file
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"user_taggers.{tagger_file.stem}"] = module
            spec.loader.exec_module(module)

            # Auto-discover: find all functions that start with "tag_"
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # Only include functions that start with "tag_" (like pytest's "test_")
                # Skip imported functions from other modules
                if not name.startswith("tag_") or obj.__module__ != module.__name__:
                    continue
                taggers.append(obj)

        except Exception as e:
            # Log but don't fail - bad user code shouldn't break operations
            print(f"Warning: Failed to load tagger {tagger_file.name}: {e}")

    return taggers


def filter_taggers(
    all_taggers: List[Callable[..., List[str]]],
    tagger_specs: List[str] | None = None,
) -> List[Callable[..., List[str]]]:
    """Filter taggers by specification.

    Args:
        all_taggers: List of all available taggers
        tagger_specs: List of specifications in format:
            - "file_name" - all taggers from that file
            - "file_name.function_name" - specific tagger function

    Returns:
        Filtered list of taggers

    Examples:
        - ["groceries"] -> all taggers from groceries.py
        - ["groceries.tag_qfc"] -> only tag_qfc from groceries.py
        - ["groceries", "merchants.tag_amazon"] -> all groceries + specific merchant tagger
    """
    if not tagger_specs:
        return all_taggers

    filtered: List[Callable[..., List[str]]] = []

    for spec in tagger_specs:
        if "." in spec:
            # Specific function: "file_name.function_name"
            file_name, func_name = spec.split(".", 1)
            for tagger in all_taggers:
                # Check if function name matches AND module name matches
                if (
                    tagger.__name__ == func_name
                    and tagger.__module__ == f"user_taggers.{file_name}"
                ):
                    if tagger not in filtered:
                        filtered.append(tagger)
        else:
            # All taggers from file: "file_name"
            file_name = spec
            for tagger in all_taggers:
                if tagger.__module__ == f"user_taggers.{file_name}":
                    if tagger not in filtered:
                        filtered.append(tagger)

    return filtered


def apply_taggers_to_transaction(
    transaction: Transaction,
    taggers: List[Callable[..., List[str]]],
    verbose: bool = False,
) -> tuple[Transaction, Dict[str, int], List[str]]:
    """Apply taggers to a transaction (additive only).

    Args:
        transaction: Transaction to tag
        taggers: List of tagger functions to apply
        verbose: Whether to collect verbose logging info

    Returns:
        Tuple of (tagged transaction, stats dict with tag counts per tagger, verbose logs)
    """
    if not taggers:
        return transaction, {}, []

    # Collect all tags
    all_tags = list(transaction.tags)  # Start with existing tags
    initial_tag_count = len(all_tags)
    tagger_stats: Dict[str, int] = {}
    verbose_logs: List[str] = []

    # Prepare kwargs for tagger functions
    tx_kwargs = {
        "description": transaction.description,
        "amount": transaction.amount,
        "transaction_date": transaction.transaction_date,
        "account_id": transaction.account_id,
        "posted_date": transaction.posted_date,
        "tags": transaction.tags,
        "id": transaction.id,
        "external_ids": transaction.external_ids,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
    }

    for tagger_func in taggers:
        try:
            new_tags = tagger_func(**tx_kwargs)
            if new_tags:
                # Track stats for this tagger
                tagger_name = tagger_func.__name__
                tagger_stats[tagger_name] = tagger_stats.get(tagger_name, 0) + len(
                    new_tags
                )
                all_tags.extend(new_tags)

                # Verbose logging
                if verbose:
                    desc = (
                        transaction.description[:50] + "..."
                        if transaction.description and len(transaction.description) > 50
                        else transaction.description or "No description"
                    )
                    tags_str = ", ".join(new_tags)
                    verbose_logs.append(f"{tagger_name} → [{desc}] +tags: {tags_str}")
        except Exception as e:
            # Log but don't fail - bad user code shouldn't break operations
            error_msg = f"Tagger {tagger_func.__name__} failed: {e}"
            # Always add to verbose logs so errors are visible
            verbose_logs.append(f"ERROR: {error_msg}")

    # Only create new transaction if tags changed
    if len(all_tags) > initial_tag_count:
        # Use Transaction constructor to ensure validators run (including tag deduplication)
        # Note: model_copy does NOT trigger validators, so we must reconstruct
        return (
            Transaction(
                id=transaction.id,
                account_id=transaction.account_id,
                external_ids=transaction.external_ids,
                amount=transaction.amount,
                description=transaction.description,
                transaction_date=transaction.transaction_date,
                posted_date=transaction.posted_date,
                tags=all_tags,  # Will be deduplicated by validator
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            ),
            tagger_stats,
            verbose_logs,
        )

    return transaction, tagger_stats, verbose_logs
