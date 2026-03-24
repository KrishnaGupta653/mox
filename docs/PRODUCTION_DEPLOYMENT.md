# Production Deployment Guide

This guide covers deploying mox CLI in production environments with proper security, monitoring, and maintenance procedures.

## 🔒 Security Hardening

### 1. Input Validation
- All user inputs are validated and sanitized
- Command injection protection implemented
- Path traversal attacks prevented
- Rate limiting on API endpoints

### 2. File Permissions
```bash
# Set secure permissions
chmod 755 /usr/bin/mox
chmod 644 /usr/share/mox/*
chmod 700 ~/.config/mox/
```

### 3. Network Security
- Web UI server binds to localhost by default
- Use reverse proxy for external access
- Enable HTTPS with proper certificates
- Implement firewall rules

## 📦 Installation Methods

### npm (Recommended)
```bash
# Global installation
npm install -g mox

# Verify installation
mox --version
mox doctor
```

### Homebrew (macOS/Linux)
```bash
# Add tap
brew tap KrishnaGupta653/tap

# Install
brew install mox

# Update
brew upgrade mox
```

### Debian/Ubuntu
```bash
# Download .deb package
wget https://github.com/KrishnaGupta653/mox/releases/latest/download/mox-cli_6.0.0_all.deb

# Install
sudo dpkg -i mox-cli_6.0.0_all.deb
sudo apt-get install -f  # Fix dependencies if needed
```

### Manual Installation
```bash
# Clone repository
git clone https://github.com/KrishnaGupta653/mox.git
cd mox

# Run installation script
./scripts/install.sh

# Add to PATH
echo 'export PATH="$PWD:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## ⚙️ Configuration

### System-wide Configuration
```bash
# Create system config
sudo mkdir -p /etc/mox
sudo cp config.example /etc/mox/config

# Edit system settings
sudo nano /etc/mox/config
```

### User Configuration
```bash
# User-specific config
mkdir -p ~/.config/mox
cp config.example ~/.config/mox/config

# Edit user settings
nano ~/.config/mox/config
```

### Environment Variables
```bash
# Required
export MUSIC_ROOT="$HOME/music_system"

# Optional API keys for enhanced features
export YOUTUBE_API_KEY="your_youtube_api_key"
export LASTFM_API_KEY="your_lastfm_api_key"
export INVIDIOUS_HOST="https://invidious.example.com"
```

## 🌐 Web UI Deployment

### Standalone Server
```bash
# Start web UI server
mox uxi

# Custom port
UXI_PORT=8080 mox uxi
```

### Reverse Proxy (nginx)
```nginx
server {
    listen 80;
    server_name music.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:7700;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Server-Sent Events support
    location /api/events {
        proxy_pass http://127.0.0.1:7700;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### Systemd Service
```ini
# /etc/systemd/system/mox-uxi.service
[Unit]
Description=mox CLI Web Interface
After=network.target

[Service]
Type=simple
User=mox
Group=mox
WorkingDirectory=/home/mox
Environment=MUSIC_ROOT=/home/mox/music_system
Environment=UXI_PORT=7700
ExecStart=/usr/bin/mox uxi
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/mox/music_system

[Install]
WantedBy=multi-user.target
```

## 📊 Monitoring & Logging

### Log Configuration
```bash
# Enable logging
export MOX_LOG_LEVEL=INFO
export MOX_LOG_FILE="$MUSIC_ROOT/data/mox.log"

# Rotate logs
sudo logrotate -d /etc/logrotate.d/mox
```

### Health Checks
```bash
#!/bin/bash
# health-check.sh

# Check if mox is responsive
if ! timeout 5s mox status >/dev/null 2>&1; then
    echo "ERROR: mox not responsive"
    exit 1
fi

# Check web UI
if ! curl -f http://localhost:7700/api/state >/dev/null 2>&1; then
    echo "ERROR: Web UI not accessible"
    exit 1
fi

echo "OK: All services healthy"
```

### Prometheus Metrics
```bash
# Export metrics endpoint
mox stats --format=prometheus > /var/lib/prometheus/node-exporter/mox.prom
```

## 🔄 Backup & Recovery

### Backup Script
```bash
#!/bin/bash
# backup-mox.sh

BACKUP_DIR="/backup/mox/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Backup user data
cp -r "$MUSIC_ROOT/data" "$BACKUP_DIR/"
cp -r "$MUSIC_ROOT/playlists" "$BACKUP_DIR/"
cp -r "$MUSIC_ROOT/txts" "$BACKUP_DIR/"
cp "$HOME/.config/mox/config" "$BACKUP_DIR/"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

echo "Backup created: $BACKUP_DIR.tar.gz"
```

### Recovery Procedure
```bash
#!/bin/bash
# restore-mox.sh

BACKUP_FILE="$1"
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

# Stop services
systemctl stop mox-uxi

# Extract backup
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Restore data
cp -r "$TEMP_DIR"/*/data/* "$MUSIC_ROOT/data/"
cp -r "$TEMP_DIR"/*/playlists/* "$MUSIC_ROOT/playlists/"
cp -r "$TEMP_DIR"/*/txts/* "$MUSIC_ROOT/txts/"
cp "$TEMP_DIR"/*/config "$HOME/.config/mox/"

# Cleanup
rm -rf "$TEMP_DIR"

# Restart services
systemctl start mox-uxi

echo "Recovery completed"
```

## 🚀 Performance Optimization

### Cache Configuration
```bash
# Increase cache size for better performance
export CACHE_TTL=7200  # 2 hours
export HISTORY_MAX=1000
export SEARCH_RESULTS=50
```

### Resource Limits
```bash
# Set resource limits in systemd service
[Service]
MemoryMax=512M
CPUQuota=50%
TasksMax=100
```

### Database Optimization
```bash
# Optimize local index
mox index --rebuild
mox cache-prune
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Fix ownership
sudo chown -R $USER:$USER "$MUSIC_ROOT"
chmod -R 755 "$MUSIC_ROOT"
```

#### 2. Port Already in Use
```bash
# Find process using port
sudo lsof -i :7700
sudo kill -9 <PID>

# Or use different port
UXI_PORT=7701 mox uxi
```

#### 3. Dependencies Missing
```bash
# Check dependencies
mox doctor

# Install missing dependencies
# Ubuntu/Debian
sudo apt update && sudo apt install mpv curl jq python3 yt-dlp

# macOS
brew install mpv curl jq python3 yt-dlp
```

#### 4. Web UI Not Loading
```bash
# Check server status
curl -v http://localhost:7700/api/state

# Check logs
tail -f "$MUSIC_ROOT/data/server.log"

# Restart server
pkill -f music_ui_server.py
mox uxi
```

### Debug Mode
```bash
# Enable debug logging
export MOX_DEBUG=1
export MOX_LOG_LEVEL=DEBUG

# Run with verbose output
mox --verbose help
```

## 📈 Scaling & Load Balancing

### Multiple Instances
```bash
# Run multiple web UI instances
UXI_PORT=7700 mox uxi &
UXI_PORT=7701 mox uxi &
UXI_PORT=7702 mox uxi &
```

### Load Balancer Configuration
```nginx
upstream mox_backend {
    server 127.0.0.1:7700;
    server 127.0.0.1:7701;
    server 127.0.0.1:7702;
}

server {
    listen 80;
    server_name music.example.com;
    
    location / {
        proxy_pass http://mox_backend;
    }
}
```

## 🛡️ Security Best Practices

1. **Regular Updates**: Keep mox and dependencies updated
2. **Access Control**: Implement proper authentication for web UI
3. **Network Isolation**: Use VPN or private networks
4. **Audit Logs**: Monitor access and usage patterns
5. **Backup Encryption**: Encrypt backups at rest and in transit
6. **Dependency Scanning**: Regularly scan for vulnerabilities

## 📞 Support & Maintenance

### Regular Maintenance Tasks
```bash
# Weekly maintenance script
#!/bin/bash

# Update dependencies
mox update

# Clean cache
mox cache-prune

# Backup data
./backup-mox.sh

# Check health
./health-check.sh

# Rotate logs
sudo logrotate -f /etc/logrotate.d/mox
```

### Getting Help
- 📖 Documentation: https://github.com/KrishnaGupta653/mox#readme
- 🐛 Issues: https://github.com/KrishnaGupta653/mox/issues
- 💬 Discussions: https://github.com/KrishnaGupta653/mox/discussions
- 📧 Email: krishnagupta653@gmail.com

---

**Note**: This deployment guide assumes mox CLI v6.0.0 or later. For older versions, please refer to the version-specific documentation.