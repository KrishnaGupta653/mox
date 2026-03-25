# mox - Terminal Music CLI

> A powerful command-line music player with web UI, mpv backend, and extensive features

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-6.0.0-blue.svg)](https://github.com/KrishnaGupta653/mox)

## ✨ Features

- **🎵 Multiple Sources**: YouTube, SoundCloud, Bandcamp, local files, radio stations
- **🌐 Web Interface**: Beautiful browser-based UI with real-time sync
- **📱 Terminal UI**: Rich terminal interface with progress bars and visualizations
- **🎤 Lyrics Support**: Real-time synced lyrics from lrclib.net
- **🎨 Album Art**: Terminal album art display via chafa
- **📋 Playlists**: Create, manage, and share playlists
- **🔀 Auto-DJ**: Automatic queue refill from Last.fm recommendations
- **🔖 Bookmarks**: Save and restore queue states with timestamps
- **📊 History**: Track listening history with search and export
- **⚡ Fast Search**: YouTube Data API v3 integration for instant results
- **🎛️ Audio Controls**: Volume, speed, equalizer, crossfade support
- **🔄 Queue Management**: Advanced queue operations and manipulation

## 🚀 Quick Install

### npm (Recommended)
```bash
npm install -g mox-cli
```

### Homebrew (macOS/Linux)
```bash
brew install KrishnaGupta653/tap/mox
```

### Manual Installation
```bash
git clone https://github.com/KrishnaGupta653/mox.git
cd mox
./scripts/install.sh
```

## 📋 Requirements

### Essential Dependencies
- **zsh** - Shell interpreter
- **python3** (≥3.6) - For web UI server
- **mpv** - Media player backend
- **curl** - HTTP requests
- **jq** - JSON processing

### Optional (Recommended)
- **yt-dlp** - YouTube/streaming support
- **fzf** - Interactive fuzzy search
- **chafa** - Terminal image display
- **ffmpeg** - Audio metadata and conversion

### Installation Commands

**macOS (Homebrew):**
```bash
brew install mpv curl jq python3 zsh yt-dlp fzf chafa ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install mpv curl jq python3 zsh yt-dlp fzf chafa ffmpeg
```

**Fedora/RHEL:**
```bash
sudo dnf install mpv curl jq python3 zsh yt-dlp fzf chafa ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S mpv curl jq python zsh yt-dlp fzf chafa ffmpeg
```

**WSL (Windows Subsystem for Linux):**
```bash
# Install dependencies
sudo apt update && sudo apt install mpv curl jq python3 zsh yt-dlp fzf chafa ffmpeg

# Audio setup (choose one):
# Option 1: PulseAudio
sudo apt install pulseaudio
pulseaudio --start

# Option 2: Windows audio (experimental)
export PULSE_SERVER=tcp:localhost
```

## 🎯 Quick Start

```bash
# Search and play music
mox search "your favorite song"

# Open web interface
mox uxi

# Show help
mox help

# Play from URL
mox play "https://youtube.com/watch?v=..."

# Control playback
mox pause    # or mox pp
mox next     # or mox mn  
mox prev     # or mox mb
mox vol 80   # Set volume to 80%

# View current status
mox status   # or mox bar
```

## 🌐 Web Interface

Launch the web UI with:
```bash
mox uxi
```

The web interface provides:
- 🎵 Real-time player status and controls
- 📋 Queue management with drag & drop
- 🎤 Synchronized lyrics display
- 🎨 Album art and track information
- 🎛️ Volume and speed controls
- 🌓 Dark/light theme toggle

## 📖 Command Reference

### Playback Control
```bash
mox play <url|query>     # Play music from URL or search
mox pause               # Toggle pause (alias: pp)
mox stop                # Stop playback
mox next                # Next track (alias: mn)
mox prev                # Previous track (alias: mb)
mox seek <time>         # Seek to position (e.g., +30, -10, 1:30)
```

### Volume & Audio
```bash
mox vol <level>         # Set volume (0-100)
mox vol +/-<amount>     # Adjust volume relatively
mox speed <rate>        # Set playback speed (0.5-2.0)
mox eq                  # Open equalizer
mox norm                # Normalize audio
```

### Queue Management
```bash
mox add <url|query>     # Add to queue
mox add-next <query>    # Add after current track
mox clear               # Clear queue
mox shuffle             # Shuffle queue
mox repeat              # Toggle repeat mode
mox queue               # Show current queue
```

### Search & Discovery
```bash
mox search <query>      # Search for music
mox similar             # Find similar tracks
mox radio               # Start radio mode
mox autodj              # Toggle Auto-DJ mode
```

### Playlists
```bash
mox save <name>         # Save current queue as playlist
mox load <name>         # Load playlist
mox playlists           # List all playlists
mox playlist <name>     # Show playlist contents
```

### History & Likes
```bash
mox history             # Show listening history
mox like                # Like current track
mox likes               # Show liked tracks
mox export              # Export data to CSV
```

### Information
```bash
mox status              # Current track info (alias: bar)
mox lyrics              # Show synchronized lyrics
mox art                 # Display album art in terminal
mox info                # Detailed track information
```

### System
```bash
mox start               # Start mpv daemon
mox kill                # Stop mpv daemon
mox restart             # Restart mpv daemon
mox config              # Edit configuration
mox index               # Scan local music library
```

## ⚙️ Configuration

Configuration file: `~/music_system/config`

```bash
# API Keys (recommended for full functionality)
LASTFM_API_KEY="your_lastfm_key"
YOUTUBE_API_KEY="your_youtube_key"
INVIDIOUS_HOST="https://invidious.snopyta.org"

# Audio Settings
DEFAULT_VOLUME=80
VOLUME_STEP=5
CROSSFADE_SECS=3

# Features
AUTODJ_ENABLED=1
LYRICS_ENABLED=1
NOTIFY_ENABLED=1

# Performance
CACHE_TTL=3600
SEARCH_RESULTS=20
BAR_REFRESH_MS=500

# Paths
LOCAL_MUSIC_DIR="$HOME/Music"
MUSIC_ROOT="$HOME/music_system"
```

## 📁 Directory Structure

```
~/music_system/
├── config              # Configuration file
├── socket/             # mpv IPC socket
├── cache/              # Cached metadata
├── playlists/          # Saved playlists
├── data/
│   ├── history         # Listening history
│   ├── likes           # Liked tracks
│   ├── bookmarks       # Saved queue states
│   └── local_index.tsv # Local music index
├── downloads/          # Downloaded files
└── logs/               # Application logs
```

## 🔧 Advanced Usage

### Bookmarks
Save and restore complete queue states:
```bash
mox bookmark save "party-mix"    # Save current state
mox bookmark load "party-mix"    # Restore queue and position
mox bookmarks                    # List all bookmarks
```

### Text File Playlists
Play from text files with URLs:
```bash
mox txt playlist.txt             # Play from text file
mox txt playlist.txt --resume    # Resume from last position
```

### Local Music Library
Index and search your local music:
```bash
mox index                        # Scan ~/Music directory
mox local "artist name"          # Search local library
```

### Keyboard Shortcuts (Web UI)
- `Space` - Play/Pause
- `→` / `←` - Next/Previous track
- `↑` / `↓` - Volume up/down
- `M` - Mute toggle
- `L` - Toggle lyrics
- `T` - Toggle theme
- `F` - Toggle fullscreen

## 🐛 Troubleshooting

### Common Issues

**mpv not starting:**
```bash
mox kill && mox start    # Restart mpv daemon
```

**Web UI not accessible:**
```bash
# Check if port is available
lsof -i :7700
# Try different port
UXI_PORT=7701 mox uxi
```

**Missing dependencies:**
```bash
./scripts/install.sh        # Re-run installation script
```

**Permission issues:**
```bash
chmod +x mox.sh music_ui_server.py
```

### Debug Mode
Enable verbose logging:
```bash
export DEBUG=1
mox <command>
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **mpv** - Powerful media player backend
- **yt-dlp** - YouTube and streaming support
- **lrclib.net** - Lyrics database
- **Last.fm** - Music recommendations
- **fzf** - Fuzzy search interface

## 🔗 Links

- [GitHub Repository](https://github.com/KrishnaGupta653/mox)
- [Issue Tracker](https://github.com/KrishnaGupta653/mox/issues)
- [npm Package](https://www.npmjs.com/package/mox-cli)

---

**Enjoy your music!** 🎶

Made with ❤️ for terminal music lovers.