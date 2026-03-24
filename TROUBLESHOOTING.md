# mox-cli Troubleshooting Guide

## 🔧 Common Installation Issues

### Issue: Conflicting Homebrew Installation

**Symptoms:**
```
rm /opt/homebrew/bin/mox
rm -rf /opt/homebrew/bin/src
```

**Cause:** You have both Homebrew and npm versions installed, causing conflicts. This often happens because npm is misconfigured to use Homebrew's directory (`/opt/homebrew/bin`) instead of its own.

**Root Cause Check:**
```bash
npm config get prefix
# If this shows "/opt/homebrew", that's the problem!
```

**Solution:**
```bash
# 1. Remove Homebrew version completely
brew uninstall mox 2>/dev/null || true

# 2. Fix npm configuration (choose one):
# Option A: Reset npm prefix
npm config delete prefix

# Option B: Set npm to use its own directory
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc

# 3. Clean up any leftover files
sudo rm -f /opt/homebrew/bin/mox /usr/local/bin/mox
sudo rm -rf /opt/homebrew/bin/src /usr/local/bin/src

# 4. Reinstall npm version cleanly
npm uninstall -g mox-cli
npm install -g mox-cli
```

### Issue: Missing System Dependencies

**Symptoms:**
```
❌ mpv not found
❌ yt-dlp not found  
❌ fzf not found
❌ chafa not found
❌ ffprobe not found
```

**Solution by OS:**

**macOS:**
```bash
# Required dependencies
brew install mpv curl jq python3 zsh

# Recommended dependencies (for full functionality)
brew install yt-dlp fzf chafa ffmpeg
```

**Ubuntu/Debian:**
```bash
# Required dependencies
sudo apt update
sudo apt install mpv curl jq python3 zsh

# Recommended dependencies
sudo apt install yt-dlp fzf chafa ffmpeg
```

**Fedora/RHEL:**
```bash
# Required dependencies
sudo dnf install mpv curl jq python3 zsh

# Recommended dependencies  
sudo dnf install yt-dlp fzf chafa ffmpeg
```

**Arch Linux:**
```bash
# Required dependencies
sudo pacman -S mpv curl jq python zsh

# Recommended dependencies
sudo pacman -S yt-dlp fzf chafa ffmpeg
```

### Issue: Permission Errors

**Symptoms:**
```
npm error EACCES: permission denied
```

**Solution:**
```bash
# Option 1: Use npm's recommended fix
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
npm install -g mox-cli

# Option 2: Use sudo (not recommended but works)
sudo npm install -g mox-cli
```

### Issue: Command Not Found After Installation

**Symptoms:**
```bash
mox help
# zsh: command not found: mox
```

**Solution:**
```bash
# Check if npm global bin is in PATH
npm config get prefix
echo $PATH

# Add npm global bin to PATH if missing
echo 'export PATH=$(npm config get prefix)/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

## 🧪 Testing Your Installation

After fixing issues, test your installation:

```bash
# 1. Check mox is available
which mox
mox --version

# 2. Check dependencies
mox doctor  # If this command exists, or:

# 3. Manual dependency check
mpv --version
curl --version  
jq --version
python3 --version
yt-dlp --version
fzf --version
chafa --version
ffprobe -version
```

## 🔄 Clean Reinstallation

If all else fails, completely clean and reinstall:

```bash
# 1. Remove everything
brew uninstall mox 2>/dev/null || true
npm uninstall -g mox-cli 2>/dev/null || true
sudo rm -f /opt/homebrew/bin/mox /usr/local/bin/mox
sudo rm -rf /opt/homebrew/bin/src /usr/local/bin/src
rm -rf ~/music_system  # WARNING: This removes your data!

# 2. Install dependencies first
brew install mpv curl jq python3 zsh yt-dlp fzf chafa ffmpeg

# 3. Install mox-cli
npm install -g mox-cli

# 4. Test
mox help
```

## 📞 Getting Help

If you're still having issues:

1. **Check the logs:** Look for detailed error messages
2. **Verify your environment:** Run `echo $SHELL` and `node --version`
3. **Create an issue:** https://github.com/KrishnaGupta653/mox/issues

Include:
- Your operating system and version
- Node.js and npm versions
- Complete error messages
- Output of `which mox` and `npm list -g mox-cli`