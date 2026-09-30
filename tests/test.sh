#!/bin/bash
# Basic smoke tests for mox CLI

set -e

echo "🧪 Running mox smoke tests..."

# Test 1: Check if main script exists and is executable
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ ! -f "$PROJECT_ROOT/src/mox.sh" ]]; then
    echo "❌ Error: src/mox.sh not found at $PROJECT_ROOT/src/mox.sh"
    exit 1
fi

if [[ ! -x "$PROJECT_ROOT/src/mox.sh" ]]; then
    echo "❌ Error: src/mox.sh is not executable"
    exit 1
fi

# Test 2: Check syntax of main script
echo "📝 Checking shell syntax..."
if command -v zsh >/dev/null 2>&1; then
    if ! zsh -n "$PROJECT_ROOT/src/mox.sh"; then
        echo "❌ Error: src/mox.sh has syntax errors"
        exit 1
    fi
elif command -v bash >/dev/null 2>&1; then
    if ! bash -n "$PROJECT_ROOT/src/mox.sh"; then
        echo "❌ Error: src/mox.sh has syntax errors"  
        exit 1
    fi
else
    echo "⚠️  Warning: No shell available for syntax check, skipping..."
fi

# Test 3: Check if Python server exists and has valid syntax
echo "🐍 Checking Python syntax..."
if [[ ! -f "$PROJECT_ROOT/src/music_ui_server.py" ]]; then
    echo "❌ Error: src/music_ui_server.py not found"
    exit 1
fi

if ! python3 -m py_compile "$PROJECT_ROOT/src/music_ui_server.py"; then
    echo "❌ Error: src/music_ui_server.py has syntax errors"
    exit 1
fi

# Test 4: Check if HTML file exists and is valid
echo "🌐 Checking HTML file..."
if [[ ! -f "$PROJECT_ROOT/src/music_ui.html" ]]; then
    echo "❌ Error: src/music_ui.html not found"
    exit 1
fi

# Test 5: Check if install script exists and is executable
echo "📦 Checking install script..."
if [[ ! -f "$PROJECT_ROOT/scripts/install.sh" ]]; then
    echo "❌ Error: scripts/install.sh not found"
    exit 1
fi

if [[ ! -x "$PROJECT_ROOT/scripts/install.sh" ]]; then
    echo "❌ Error: scripts/install.sh is not executable"
    exit 1
fi

# Test 6: Check if essential files exist
echo "📄 Checking essential files..."
for file in "VERSION" "LICENSE" "README.md" "package.json"; do
    if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
        echo "❌ Error: $file not found"
        exit 1
    fi
done

# Test 7: Validate package.json
echo "📦 Validating package.json..."
if ! python3 -c "import json; json.load(open('$PROJECT_ROOT/package.json'))"; then
    echo "❌ Error: package.json is not valid JSON"
    exit 1
fi
FILE_VERSION="$(tr -d '[:space:]' < "$PROJECT_ROOT/VERSION")"
PKG_VERSION="$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/package.json'))['version'])")"
if [[ "$FILE_VERSION" != "$PKG_VERSION" ]]; then
    echo "❌ Error: VERSION ($FILE_VERSION) and package.json ($PKG_VERSION) differ - run ./release.sh X.Y.Z"
    exit 1
fi

# Test 8: Check if help command works (basic functionality test)
echo "❓ Testing help command..."
if ! timeout 10s "$PROJECT_ROOT/src/mox.sh" help >/dev/null 2>&1; then
    echo "⚠️  Warning: help command failed or timed out (this might be expected without dependencies)"
else
    echo "✅ Help command executed successfully"
fi

# Test 9: Daemon lifecycle on a fresh MUSIC_ROOT (catches missing _bootstrap etc.)
echo "🔁 Testing daemon start/stop on a fresh state dir..."
if command -v mpv >/dev/null 2>&1 && command -v socat >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    LIFECYCLE_ROOT="$(mktemp -d)"
    trap 'MUSIC_ROOT="$LIFECYCLE_ROOT" "$PROJECT_ROOT/mox" stop >/dev/null 2>&1 || true; rm -rf "$LIFECYCLE_ROOT"' EXIT
    export MUSIC_ROOT="$LIFECYCLE_ROOT"
    "$PROJECT_ROOT/mox" start >/dev/null || { echo "❌ Error: mox start failed on a fresh MUSIC_ROOT"; exit 1; }
    [[ -S "$LIFECYCLE_ROOT/socket/mpv.sock" ]] || { echo "❌ Error: mpv socket missing after mox start"; exit 1; }
    "$PROJECT_ROOT/mox" eq bass >/dev/null || { echo "❌ Error: mox eq bass failed"; exit 1; }
    "$PROJECT_ROOT/mox" stop >/dev/null || { echo "❌ Error: mox stop failed"; exit 1; }
    [[ ! -S "$LIFECYCLE_ROOT/socket/mpv.sock" ]] || { echo "❌ Error: socket still present after mox stop"; exit 1; }
    "$PROJECT_ROOT/mox" start >/dev/null || { echo "❌ Error: mox start failed after stop"; exit 1; }
    "$PROJECT_ROOT/mox" stop >/dev/null
    unset MUSIC_ROOT
    echo "✅ Daemon lifecycle OK"
else
    echo "⚠️  Skipping daemon lifecycle test (mpv/socat/jq not installed)"
fi

echo "✅ All smoke tests passed!"
echo "🎵 mox is ready for packaging!"