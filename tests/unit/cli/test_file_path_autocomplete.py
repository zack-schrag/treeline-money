"""Unit tests for file path autocomplete functionality."""

from pathlib import Path
import tempfile
import os
import pytest


def test_get_file_path_completions_with_home_directory():
    """Test that typing '~/' returns home directory suggestions."""
    from treeline.cli import get_file_path_completions

    completions = get_file_path_completions("~/")

    # Should return directories starting with ~/
    # At minimum, most systems have ~/Documents, ~/Downloads, etc
    assert len(completions) > 0
    # All completions should start with ~/
    for comp in completions:
        assert comp.startswith("~/") or comp.startswith(os.path.expanduser("~"))


def test_get_file_path_completions_with_partial_path():
    """Test that partial paths return matching completions."""
    from treeline.cli import get_file_path_completions

    # Create a temp directory with known structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test directories
        test_dirs = ["test_data", "test_docs", "other_folder"]
        for dirname in test_dirs:
            (Path(tmpdir) / dirname).mkdir()

        # Test partial match
        completions = get_file_path_completions(f"{tmpdir}/test")

        # Should return both test_ directories
        assert any("test_data" in c for c in completions)
        assert any("test_docs" in c for c in completions)
        # Should not return other_folder
        assert not any("other_folder" in c for c in completions)


def test_get_file_path_completions_empty_returns_current_dir():
    """Test that empty string returns current directory suggestions."""
    from treeline.cli import get_file_path_completions

    completions = get_file_path_completions("")

    # Should return items from current directory
    assert isinstance(completions, list)


def test_get_file_path_completions_with_absolute_path():
    """Test that absolute paths work correctly."""
    from treeline.cli import get_file_path_completions

    # Create a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        (Path(tmpdir) / "file1.csv").touch()
        (Path(tmpdir) / "file2.csv").touch()
        (Path(tmpdir) / "other.txt").touch()

        # Test completions for CSV files
        completions = get_file_path_completions(f"{tmpdir}/file")

        # Should return both CSV files starting with "file"
        assert any("file1.csv" in c for c in completions)
        assert any("file2.csv" in c for c in completions)
        # Should not return other.txt
        assert not any("other.txt" in c for c in completions)


def test_get_file_path_completions_nonexistent_path():
    """Test that nonexistent paths return empty list."""
    from treeline.cli import get_file_path_completions

    completions = get_file_path_completions("/nonexistent/path/that/does/not/exist/")

    # Should return empty list for nonexistent paths
    assert len(completions) == 0
