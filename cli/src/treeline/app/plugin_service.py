"""Plugin management service."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

from treeline.domain import Result


class PluginService:
    """Service for managing external plugins."""

    def __init__(self, plugins_dir: Path):
        """Initialize plugin service.

        Args:
            plugins_dir: Directory where plugins are installed (e.g., ~/.treeline/plugins)
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def create_plugin(
        self, name: str, target_dir: Path | None = None
    ) -> Result[Dict[str, Any]]:
        """Create a new plugin from template.

        Args:
            name: Plugin name (will be used as plugin ID and directory name)
            target_dir: Directory to create plugin in (defaults to current directory)

        Returns:
            Result with plugin directory path
        """
        # Validate name
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            return Result(
                success=False,
                error="Plugin name must contain only letters, numbers, hyphens, and underscores",
            )

        # Determine target directory
        if target_dir is None:
            target_dir = Path.cwd()

        plugin_dir = target_dir / name
        if plugin_dir.exists():
            return Result(
                success=False, error=f"Directory already exists: {plugin_dir}"
            )

        # Find plugin template (relative to this service file)
        # The template is at: treeline-money/plugin-template/
        service_file = Path(__file__)  # cli/src/treeline/app/plugin_service.py
        repo_root = (
            service_file.parent.parent.parent.parent.parent
        )  # Go up to repo root
        template_dir = repo_root / "plugin-template"

        if not template_dir.exists():
            return Result(
                success=False, error=f"Plugin template not found at {template_dir}"
            )

        # Copy template
        try:
            shutil.copytree(
                template_dir,
                plugin_dir,
                ignore=shutil.ignore_patterns(
                    "node_modules", "dist", ".git", "*.log", "__pycache__"
                ),
            )
        except Exception as e:
            return Result(success=False, error=f"Failed to copy template: {e}")

        # Update manifest.json with plugin name
        manifest_path = plugin_dir / "manifest.json"
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            manifest["id"] = name
            manifest["name"] = name.replace("-", " ").replace("_", " ").title()

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            return Result(success=False, error=f"Failed to update manifest: {e}")

        return Result(
            success=True,
            data={
                "plugin_dir": str(plugin_dir),
                "plugin_id": name,
            },
        )

    def install_plugin(
        self, source: str, force_build: bool = False
    ) -> Result[Dict[str, Any]]:
        """Install a plugin from a local directory or GitHub URL.

        Args:
            source: Local directory path or GitHub URL
            force_build: Force rebuild even if dist/index.js exists

        Returns:
            Result with installation details
        """
        # Determine source type
        is_github = source.startswith(("http://", "https://", "git@"))

        if is_github:
            return self._install_from_github(source, force_build)
        else:
            return self._install_from_directory(Path(source).expanduser(), force_build)

    def _install_from_directory(
        self, source_dir: Path, force_build: bool
    ) -> Result[Dict[str, Any]]:
        """Install plugin from local directory.

        Args:
            source_dir: Path to plugin directory
            force_build: Force rebuild

        Returns:
            Result with installation details
        """
        if not source_dir.exists():
            return Result(success=False, error=f"Directory not found: {source_dir}")

        # Read manifest
        manifest_path = source_dir / "manifest.json"
        if not manifest_path.exists():
            return Result(
                success=False, error=f"No manifest.json found in {source_dir}"
            )

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            return Result(success=False, error=f"Failed to parse manifest.json: {e}")

        plugin_id = manifest.get("id")
        if not plugin_id:
            return Result(success=False, error="manifest.json missing 'id' field")

        # Check if plugin needs to be built
        dist_file = source_dir / "dist" / "index.js"
        needs_build = force_build or not dist_file.exists()

        if needs_build:
            # Check if this looks like a source plugin (has package.json)
            if (source_dir / "package.json").exists():
                build_result = self._build_plugin(source_dir)
                if not build_result.success:
                    return build_result
            else:
                return Result(
                    success=False,
                    error=f"Plugin not built and no package.json found. Expected dist/index.js at {dist_file}",
                )

        # Verify dist file exists after build
        if not dist_file.exists():
            return Result(
                success=False,
                error=f"Build succeeded but dist/index.js not found at {dist_file}",
            )

        # Install to plugins directory
        install_dir = self.plugins_dir / plugin_id
        install_dir.mkdir(parents=True, exist_ok=True)

        # Copy manifest and dist
        try:
            shutil.copy2(manifest_path, install_dir / "manifest.json")
            shutil.copy2(dist_file, install_dir / "index.js")
        except Exception as e:
            return Result(success=False, error=f"Failed to copy plugin files: {e}")

        return Result(
            success=True,
            data={
                "plugin_id": plugin_id,
                "plugin_name": manifest.get("name", plugin_id),
                "version": manifest.get("version", "unknown"),
                "install_dir": str(install_dir),
                "built": needs_build,
            },
        )

    def _install_from_github(
        self, url: str, force_build: bool
    ) -> Result[Dict[str, Any]]:
        """Install plugin from GitHub URL.

        Args:
            url: GitHub repository URL
            force_build: Force rebuild

        Returns:
            Result with installation details
        """
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clone repository
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", url, str(temp_path / "repo")],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                return Result(
                    success=False, error=f"Failed to clone repository: {e.stderr}"
                )
            except FileNotFoundError:
                return Result(
                    success=False, error="git command not found. Please install git."
                )

            repo_path = temp_path / "repo"

            # Install from the cloned directory
            return self._install_from_directory(repo_path, force_build)

    def _build_plugin(self, plugin_dir: Path) -> Result[None]:
        """Build a plugin using npm.

        Args:
            plugin_dir: Plugin directory

        Returns:
            Result indicating success or failure
        """
        # Check if npm is available
        try:
            subprocess.run(
                ["npm", "--version"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return Result(
                success=False,
                error="npm command not found. Please install Node.js and npm.",
            )

        # Install dependencies
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=plugin_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return Result(success=False, error=f"npm install failed: {e.stderr}")

        # Build plugin
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=plugin_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return Result(success=False, error=f"npm run build failed: {e.stderr}")

        return Result(success=True)

    def uninstall_plugin(self, plugin_id: str) -> Result[Dict[str, Any]]:
        """Uninstall a plugin.

        Args:
            plugin_id: ID of plugin to uninstall

        Returns:
            Result with uninstallation details
        """
        plugin_dir = self.plugins_dir / plugin_id

        if not plugin_dir.exists():
            return Result(success=False, error=f"Plugin not found: {plugin_id}")

        # Read manifest for plugin name
        manifest_path = plugin_dir / "manifest.json"
        plugin_name = plugin_id
        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    plugin_name = manifest.get("name", plugin_id)
            except Exception:
                pass  # Use plugin_id as fallback

        # Remove plugin directory
        try:
            shutil.rmtree(plugin_dir)
        except Exception as e:
            return Result(success=False, error=f"Failed to remove plugin: {e}")

        return Result(
            success=True,
            data={
                "plugin_id": plugin_id,
                "plugin_name": plugin_name,
            },
        )

    def list_plugins(self) -> Result[list[Dict[str, Any]]]:
        """List all installed plugins.

        Returns:
            Result with list of plugin info
        """
        plugins = []

        if not self.plugins_dir.exists():
            return Result(success=True, data=plugins)

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)

                plugins.append(
                    {
                        "id": manifest.get("id", plugin_dir.name),
                        "name": manifest.get("name", plugin_dir.name),
                        "version": manifest.get("version", "unknown"),
                        "description": manifest.get("description", ""),
                        "author": manifest.get("author", ""),
                    }
                )
            except Exception:
                # Skip invalid plugins
                continue

        return Result(success=True, data=plugins)
