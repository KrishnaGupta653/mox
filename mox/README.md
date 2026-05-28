# 🎵 Mox Music System - Modern Architecture

A next-generation terminal-based music player with a modern web UI, featuring smart queue management, waveform visualization, and an extensible plugin system.

## 🚀 Features

### Core Features
- **Terminal CLI** - Full-featured command-line music player
- **Modern Web UI** - Glassmorphism design with responsive layout
- **Smart Queue** - AI-powered recommendations and auto-DJ
- **Waveform Visualizer** - Real-time audio visualization
- **Advanced Search** - Multi-source search (local, YouTube, SoundCloud)
- **Share Links** - Shareable URLs with QR codes
- **Scheduler** - Alarms, sleep timers, and scheduled playback
- **Plugin System** - Extensible architecture with sandboxed plugins

### Technical Highlights
- **Security First** - JWT authentication, rate limiting, CSP headers
- **Performance Optimized** - Adaptive polling, caching, compression
- **Modern Stack** - FastAPI backend, React/Vue-ready frontend
- **Scalable** - Redis caching, connection pooling, microservices-ready

## 📁 Project Structure

```
mox/
├── src/
│   ├── ui/                 # Frontend components
│   │   ├── css/           # Stylesheets
│   │   ├── js/            # JavaScript modules
│   │   └── components/    # UI components
│   ├── server/            # Backend server code
│   └── plugins/           # Plugin loader and API
├── static/                # Static assets
│   ├── css/              # Compiled CSS
│   ├── js/               # Compiled JS
│   └── images/           # Images and icons
├── templates/             # HTML templates
├── plugins/               # Installed plugins
├── mox.py                # Main CLI entry point
├── server.py             # HTTP server
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- mpv media player
- Node.js 18+ (for frontend development)
- Redis (optional, for caching)

### Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies (development)
cd frontend && npm install

# Run the server
python server.py

# Or use the CLI
python mox.py play "song.mp3"
```

## 🎨 UI Development

The frontend uses modern build tools for optimal performance:

```bash
# Development mode with HMR
npm run dev

# Production build
npm run build
```

## 🔌 Plugin Development

Create plugins in the `plugins/` directory with a `manifest.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "permissions": ["network", "storage"]
}
```

## 📖 Documentation

- [API Documentation](docs/api.md)
- [Plugin Guide](docs/plugins.md)
- [User Manual](docs/user-guide.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details
