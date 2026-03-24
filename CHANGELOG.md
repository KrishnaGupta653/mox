# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.0.0] - 2026-03-23

### Added
- **Package Management**: Added npm and Homebrew support for easy installation
- **Dependency Validation**: Automatic checking and guidance for missing dependencies
- **Improved Error Handling**: Better error messages and troubleshooting guidance
- **Installation Script**: Automated setup script with dependency checking
- **Documentation**: Comprehensive README with installation and usage instructions
- **License**: MIT license for open source distribution

### Fixed
- **Web UI Commands**: Fixed missing 'qrm' command in allowed actions list
- **Path Configuration**: Python server now respects MUSIC_ROOT environment variable
- **Code Duplication**: Removed duplicate lib/ directory

### Changed
- **Project Structure**: Simplified to single source files without duplication
- **Version Management**: Centralized version in VERSION file
- **Configuration**: Enhanced configuration validation and error reporting

### Technical Improvements
- Added .gitignore and .npmignore for proper version control
- Created Homebrew formula for macOS/Linux installation
- Enhanced Python server with better error handling and dependency checks
- Improved shell script with dependency validation
- Added comprehensive installation and setup automation

## [5.0.0] - Previous Release

### Added (from v5 changelog in source)
- **Critical Bug Fixes**: Multiple stability improvements
- **Performance**: YouTube Data API v3 integration for faster search
- **UI Enhancements**: Terminal album art, real-time lyrics, unified TUI
- **Features**: Auto-DJ mode, bookmarks, queue management improvements
- **Local Library**: Music indexing and search capabilities
- **Graceful Shutdown**: Proper cleanup and lock management

### Performance Improvements
- Single jq parse pass for progress bar (9 forks → 1 per frame)
- Parallel text playlist resolution
- Live async search UI with fzf
- Reservoir sampling for shuffle operations

### UI/UX Improvements
- Terminal album art via chafa
- Real-time synced lyrics from lrclib.net
- Unified TUI dashboard with tmux integration
- Enhanced progress bar with cursor restoration

### Features
- Auto-DJ/radio mode with Last.fm integration
- Named bookmarks for queue snapshots
- Resume functionality for text playlists
- Hot-reload configuration without daemon restart
- SponsorBlock integration documentation

## Previous Versions

See inline changelog in mox.sh for detailed version history from v1-v4.