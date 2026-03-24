#!/bin/bash
set -e

# mox - Terminal Music CLI Installation Script
# This script sets up the music system directory and checks for dependencies

MUSIC_ROOT="${MUSIC_ROOT:-$HOME/music_system}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🎵 Installing mox - Terminal Music CLI"
echo "   Music system directory: $MUSIC_ROOT"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$MUSIC_ROOT"/{socket,cache,playlists,txts,downloads,data,locks,plugins}

# Set up initial config if it doesn't exist
if [ ! -f "$MUSIC_ROOT/config" ]; then
    echo "⚙️  Creating initial configuration..."
    cat > "$MUSIC_ROOT/config" << 'EOF'
# mox - Terminal Music CLI Configuration
# Uncomment and modify as needed

# Cache settings
# CACHE_TTL=3600
# HISTORY_MAX=500

# Audio settings
# DEFAULT_VOLUME=80
# VOLUME_STEP=5

# Search settings
# SEARCH_RESULTS=20

# API Keys (optional but recommended)
# LASTFM_API_KEY=""
# YOUTUBE_API_KEY=""
# INVIDIOUS_HOST=""

# Local music directory
# LOCAL_MUSIC_DIR="$HOME/Music"

# Features
# AUTODJ_ENABLED=0
# LYRICS_ENABLED=1
# NOTIFY_ENABLED=0
# CROSSFADE_SECS=0

# Performance
# BAR_REFRESH_MS=500
EOF
fi

# Check for required dependencies
echo "🔍 Checking dependencies..."

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "  ✅ $1 found"
        return 0
    else
        echo "  ❌ $1 not found"
        return 1
    fi
}

# Essential dependencies
MISSING_DEPS=()

if ! check_command "zsh"; then
    MISSING_DEPS+=("zsh")
fi

if ! check_command "python3"; then
    MISSING_DEPS+=("python3")
fi

if ! check_command "mpv"; then
    MISSING_DEPS+=("mpv")
fi

if ! check_command "curl"; then
    MISSING_DEPS+=("curl")
fi

if ! check_command "jq"; then
    MISSING_DEPS+=("jq")
fi

# Optional but recommended dependencies
OPTIONAL_DEPS=()

if ! check_command "yt-dlp"; then
    OPTIONAL_DEPS+=("yt-dlp")
fi

if ! check_command "fzf"; then
    OPTIONAL_DEPS+=("fzf")
fi

if ! check_command "chafa"; then
    OPTIONAL_DEPS+=("chafa")
fi

if ! check_command "ffprobe"; then
    OPTIONAL_DEPS+=("ffmpeg")
fi

# Report missing dependencies
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo ""
    echo "❌ Missing required dependencies:"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "   - $dep"
    done
    echo ""
    echo "📋 To install missing dependencies, copy and run this command:"
    echo ""
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   brew install ${MISSING_DEPS[*]}"
        echo ""
        echo "   (macOS with Homebrew)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "   sudo apt update && sudo apt install ${MISSING_DEPS[*]}"
        echo ""
        echo "   (Ubuntu/Debian - or use dnf/pacman for other distros)"
    fi
    echo ""
    echo "After installing dependencies, run 'mox help' to start using the music CLI."
    exit 1
fi

if [ ${#OPTIONAL_DEPS[@]} -gt 0 ]; then
    echo ""
    echo "💡 Optional dependencies (recommended for full functionality):"
    for dep in "${OPTIONAL_DEPS[@]}"; do
        echo "   - $dep"
    done
    echo ""
    echo "📋 For the best experience, also install these optional dependencies:"
    echo ""
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   brew install ${OPTIONAL_DEPS[*]}"
        echo ""
        echo "   (Enables YouTube downloads, fuzzy search, terminal images, etc.)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "   sudo apt update && sudo apt install ${OPTIONAL_DEPS[*]}"
        echo ""
        echo "   (Enables YouTube downloads, fuzzy search, terminal images, etc.)"
    fi
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR/../src/mox.sh"
chmod +x "$SCRIPT_DIR/../src/music_ui_server.py"

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "🚀 Quick start:"
echo "   mox help          - Show all available commands"
echo "   mox search <term> - Search for music"
echo "   mox uxi           - Open web interface"
echo ""
echo "📖 Configuration file: $MUSIC_ROOT/config"
echo "📁 Data directory: $MUSIC_ROOT"
echo ""
echo "Enjoy your music! 🎶"