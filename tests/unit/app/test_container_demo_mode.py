"""Unit tests for Container demo mode functionality."""

import os
from pathlib import Path
import tempfile

import pytest

from treeline.app.container import Container
from treeline.infra.demo_provider import DemoDataProvider
from treeline.infra.simplefin import SimpleFINProvider


def test_container_uses_demo_provider_when_env_var_set():
    """Test that container returns demo provider when TREELINE_DEMO_MODE=true."""
    # Set demo mode
    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            registry = container.provider_registry()

            # Should have demo provider for simplefin
            assert "simplefin" in registry
            assert isinstance(registry["simplefin"], DemoDataProvider)

            # Should have demo provider for csv
            assert "csv" in registry
            assert isinstance(registry["csv"], DemoDataProvider)

    finally:
        # Clean up
        os.environ.pop("TREELINE_DEMO_MODE", None)


def test_container_uses_real_providers_when_env_var_not_set():
    """Test that container returns real providers when demo mode is disabled."""
    # Ensure demo mode is not set
    os.environ.pop("TREELINE_DEMO_MODE", None)

    with tempfile.TemporaryDirectory() as tmpdir:
        container = Container(str(Path(tmpdir) / "test.db"))
        registry = container.provider_registry()

        # Should have real SimpleFIN provider
        assert "simplefin" in registry
        assert isinstance(registry["simplefin"], SimpleFINProvider)

        # CSV provider is always real (not affected by demo mode in terms of type)
        assert "csv" in registry


def test_container_recognizes_various_truthy_values():
    """Test that container recognizes various truthy values for demo mode."""
    truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]

    for value in truthy_values:
        os.environ["TREELINE_DEMO_MODE"] = value

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create new container for each test
                container = Container(str(Path(tmpdir) / "test.db"))
                # Clear cached instances to force re-evaluation
                container._instances.clear()
                registry = container.provider_registry()

                assert isinstance(registry["simplefin"], DemoDataProvider), (
                    f"Failed for value: {value}"
                )

        finally:
            os.environ.pop("TREELINE_DEMO_MODE", None)


def test_container_treats_false_values_as_disabled():
    """Test that container treats false/empty values as demo mode disabled."""
    falsy_values = ["false", "False", "FALSE", "0", "no", "No", ""]

    for value in falsy_values:
        os.environ["TREELINE_DEMO_MODE"] = value

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                container = Container(str(Path(tmpdir) / "test.db"))
                # Clear cached instances to force re-evaluation
                container._instances.clear()
                registry = container.provider_registry()

                assert isinstance(registry["simplefin"], SimpleFINProvider), (
                    f"Failed for value: {value}"
                )

        finally:
            os.environ.pop("TREELINE_DEMO_MODE", None)
