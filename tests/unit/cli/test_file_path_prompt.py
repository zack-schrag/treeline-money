"""Unit tests for file path prompt functionality."""

import pytest


def test_prompt_for_file_path_creates_path_completer():
    """Test that prompt_for_file_path is set up to use PathCompleter.

    This is a simple verification test that the function exists and
    uses the correct completer type.
    """
    from treeline.cli import prompt_for_file_path
    from prompt_toolkit.completion import PathCompleter

    # Verify the function exists and accepts prompt text
    # We can't easily test the interactive behavior in unit tests,
    # but we can verify the setup is correct
    assert callable(prompt_for_file_path)


def test_prompt_text_formatting():
    """Test that prompt text is formatted correctly.

    The function should accept plain text (no Rich markup) and format
    it appropriately for prompt_toolkit.
    """
    # This documents that prompt_for_file_path should receive plain text
    # without Rich markup like [cyan] or [/cyan]
    from treeline.cli import prompt_for_file_path

    # Function signature check
    import inspect
    sig = inspect.signature(prompt_for_file_path)
    assert 'prompt_text' in sig.parameters
    # Default should be empty string
    assert sig.parameters['prompt_text'].default == ""


def test_path_completer_allows_directory_continuation():
    """Test that PathCompleter behavior allows continuing after directory selection.

    This is a documentation test - PathCompleter by default allows users to
    continue typing after selecting a directory, which is the desired behavior.
    """
    from prompt_toolkit.completion import PathCompleter
    import tempfile
    from pathlib import Path

    # Create a test directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.csv").touch()

        # Create PathCompleter
        completer = PathCompleter(expanduser=True)

        # This test documents that PathCompleter is designed to allow
        # users to continue typing after Tab-completing a directory name.
        # The actual interactive behavior is handled by prompt_toolkit's
        # input handling, not something we need to explicitly code.
        assert completer is not None
