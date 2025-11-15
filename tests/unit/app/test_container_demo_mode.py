"""Unit tests for Container demo mode functionality."""

import os
from pathlib import Path
import tempfile

from treeline.app.container import Container
from treeline.infra.demo_provider import DemoDataProvider
from treeline.infra.simplefin import SimpleFINProvider
from treeline.infra.csv_provider import CSVProvider


def test_container_uses_demo_provider_when_demo_mode_enabled():
    """Test that container uses demo provider for bank integrations in demo mode.

    CSV provider should always use real CSVProvider since it imports from actual files.
    """
    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            registry = container.provider_registry()

            # SimpleFIN should use demo provider in demo mode
            assert isinstance(registry["simplefin"], DemoDataProvider)

            # CSV should always use real provider, even in demo mode
            assert isinstance(registry["csv"], CSVProvider)
            assert not isinstance(registry["csv"], DemoDataProvider)
    finally:
        os.environ.pop("TREELINE_DEMO_MODE", None)


def test_container_uses_real_providers_when_demo_mode_disabled():
    """Test that container uses real providers when demo mode is disabled."""
    os.environ.pop("TREELINE_DEMO_MODE", None)

    with tempfile.TemporaryDirectory() as tmpdir:
        container = Container(str(Path(tmpdir) / "test.db"))
        registry = container.provider_registry()

        # Should use real provider implementations
        assert isinstance(registry["simplefin"], SimpleFINProvider)
        assert not isinstance(registry["simplefin"], DemoDataProvider)

        # CSV should always use real provider
        assert isinstance(registry["csv"], CSVProvider)
