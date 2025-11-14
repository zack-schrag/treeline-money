"""Unit tests for Container demo mode functionality."""

import os
from pathlib import Path
import tempfile

from treeline.app.container import Container
from treeline.infra.demo_provider import DemoDataProvider
from treeline.infra.simplefin import SimpleFINProvider


def test_container_uses_demo_provider_when_demo_mode_enabled():
    """Test that container uses demo provider when TREELINE_DEMO_MODE=true."""
    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            registry = container.provider_registry()

            # Both providers should be DemoDataProvider instances
            assert isinstance(registry["simplefin"], DemoDataProvider)
            assert isinstance(registry["csv"], DemoDataProvider)
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
