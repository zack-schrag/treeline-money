#!/bin/bash
set -e

# Build CLI binary for the current platform and place it in src-tauri/binaries/
# This script is called before Tauri builds

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$UI_DIR")"
CLI_DIR="$REPO_ROOT/cli"
BINARIES_DIR="$UI_DIR/src-tauri/binaries"

# Get the target triple
TARGET_TRIPLE=$(rustc -Vv | grep host | cut -d' ' -f2)

echo "Building CLI for target: $TARGET_TRIPLE"

# Create binaries directory if it doesn't exist
mkdir -p "$BINARIES_DIR"

# Build the CLI binary
cd "$CLI_DIR"

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Installing CLI dependencies..."
    uv sync --locked
fi

# Install PyInstaller if needed
uv pip install pyinstaller --quiet

# Build binary
echo "Building CLI binary with PyInstaller..."
uv run pyinstaller --onefile --name tl --hidden-import=treeline --collect-all treeline src/treeline/cli.py --distpath dist --workpath build --specpath . -y

# Copy to binaries directory with target triple suffix
SOURCE_BINARY="$CLI_DIR/dist/tl"
if [[ "$TARGET_TRIPLE" == *"windows"* ]]; then
    SOURCE_BINARY="$CLI_DIR/dist/tl.exe"
    DEST_BINARY="$BINARIES_DIR/tl-${TARGET_TRIPLE}.exe"
else
    DEST_BINARY="$BINARIES_DIR/tl-${TARGET_TRIPLE}"
fi

echo "Copying $SOURCE_BINARY to $DEST_BINARY"
cp "$SOURCE_BINARY" "$DEST_BINARY"
chmod +x "$DEST_BINARY"

echo "CLI binary ready at: $DEST_BINARY"
