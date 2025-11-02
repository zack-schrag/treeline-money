"""Registry for user-defined taggers.

Note: The @tagger decorator is now optional. Any function defined in a tagger file
will be auto-discovered and registered.
"""

from typing import Callable, List, Any

# Global registry of tagger functions
_TAGGERS: List[Callable[..., List[str]]] = []


def tagger(func: Callable[..., List[str]]) -> Callable[..., List[str]]:
    """
    Optional decorator to explicitly register a function as a tagger.

    Note: This decorator is optional - functions are auto-discovered from tagger files.
    Use it only if you want to be explicit or have multiple functions in one file.

    Args:
        func: Function that takes transaction fields as kwargs and returns a list of tags

    Returns:
        The original function (unchanged)

    Example:
        @tagger
        def tag_groceries(description, amount, **kwargs):
            if description and 'WHOLE FOODS' in description.upper():
                return ['groceries', 'food']
            return []
    """
    _TAGGERS.append(func)
    return func


def register_tagger(func: Callable[..., List[str]]) -> None:
    """
    Register a tagger function.

    Args:
        func: Tagger function to register
    """
    if func not in _TAGGERS:
        _TAGGERS.append(func)


def get_taggers() -> List[Callable[..., List[str]]]:
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
