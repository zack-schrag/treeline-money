"""Decorators for user-defined taggers."""

from typing import Callable, List
from treeline.domain import Transaction

# Global registry of tagger functions
_TAGGERS: List[Callable[[Transaction], List[str]]] = []


def tagger(
    func: Callable[[Transaction], List[str]],
) -> Callable[[Transaction], List[str]]:
    """
    Decorator to register a function as an auto-tagger.

    Auto-taggers are called during transaction sync to automatically apply tags
    based on custom rules. Multiple taggers can be registered and will all run
    in sequence.

    Args:
        func: Function that takes a Transaction and returns a list of tags

    Returns:
        The original function (unchanged)

    Example:
        @tagger
        def tag_groceries(transaction: Transaction) -> List[str]:
            if 'WHOLE FOODS' in transaction.description.upper():
                return ['groceries', 'food']
            return []
    """
    _TAGGERS.append(func)
    return func


def get_taggers() -> List[Callable[[Transaction], List[str]]]:
    """
    Return all registered tagger functions.

    Returns:
        List of tagger functions
    """
    return _TAGGERS.copy()


def clear_taggers() -> None:
    """
    Clear all registered taggers.

    This is primarily useful for testing to ensure a clean state.
    """
    _TAGGERS.clear()
