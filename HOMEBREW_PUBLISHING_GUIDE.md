# Complete Homebrew Publishing Guide for mox

## 🍺 Publishing to Your Own Homebrew Tap

### Step 1: Create GitHub Release

1. **Go to GitHub**: https://github.com/KrishnaGupta653/mox/releases
2. **Click "Create a new release"**
3. **Tag**: `v6.0.4`
4. **Title**: `mox v6.0.4 - Terminal Music CLI`
5. **Description**:
   ```
   ## What's New in v6.0.4
   
   ### 🔧 Bug Fixes
   - Fixed symlink handling in npm global installations
   - Resolved "No such file or directory" errors
   
   ### 💡 Improvements  
   - Enhanced dependency installation messages
   - Clear copy-pasteable brew install commands
   - Better error guidance for missing dependencies
   
   ### 📦 Installation
   ```bash
   # npm (recommended)
   npm install -g mox-cli
   
   # Homebrew (coming soon)
   brew install KrishnaGupta653/tap/mox
   ```
   
   ### 🎵 Quick Start
   ```bash
   mox help
   mox search "lofi hip hop"
   mox uxi  # Web interface
   ```
   ```
6. **Click "Publish release"**

### Step 2: Create Homebrew Tap Repository

1. **Go to GitHub**: https://github.com/new
2. **Repository name**: `homebrew-tap`
3. **Description**: `Homebrew tap for mox - Terminal Music CLI`
4. **Make it Public**
5. **Add README file**: ✅
6. **Click "Create repository"**

### Step 3: Set Up Your Tap

```bash
# Clone your new tap repository
cd ~/Desktop  # or wherever you want to work
git clone https://github.com/KrishnaGupta653/homebrew-tap.git
cd homebrew-tap

# Create Formula directory
mkdir -p Formula

# Copy your formula (run this from your mox directory)
cp /Users/krishnagupta/Downloads/mox/packaging/homebrew/mox.rb Formula/mox.rb

# Commit and push
git add Formula/mox.rb
git commit -m "Add mox v6.0.4 formula

- Terminal music CLI with web UI
- Supports YouTube, SoundCloud, Bandcamp
- mpv backend with advanced features
- Global installation via Homebrew tap"

git push origin main
```

### Step 4: Test Your Formula

```bash
# Test the formula locally
brew install --build-from-source Formula/mox.rb

# Or test from GitHub directly
brew install KrishnaGupta653/tap/mox

# Test it works
mox help
mox --version

# Uninstall test
brew uninstall mox
```

### Step 5: Update Documentation

Add to your main README.md:

```markdown
### Homebrew (macOS/Linux)
```bash
brew install KrishnaGupta653/tap/mox
```

Or add the tap first:
```bash
brew tap KrishnaGupta653/tap
brew install mox
```
```

## 🔄 Updating Your Homebrew Formula

When you release a new version:

### 1. Create New GitHub Release
- Tag: `v6.0.5` (or whatever version)
- Follow same process as Step 1

### 2. Update Formula
```bash
# Get new SHA256
curl -sL https://github.com/KrishnaGupta653/mox/archive/v6.0.5.tar.gz | shasum -a 256

# Update your formula file:
# - Change URL to new version
# - Update SHA256
# - Update version if specified

# In your homebrew-tap repository:
git add Formula/mox.rb
git commit -m "Update mox to v6.0.5"
git push origin main
```

### 3. Test Update
```bash
brew uninstall mox
brew install KrishnaGupta653/tap/mox
mox --version  # Should show new version
```

## 🏆 Advanced: Submit to Official Homebrew (Optional)

Once your project becomes popular, you can submit to official Homebrew:

### Requirements for Official Homebrew:
- ✅ Stable, well-maintained project
- ✅ 30+ forks OR 30+ watchers OR 75+ stars on GitHub
- ✅ No issues with existing formula
- ✅ Project has been around for at least 30 days

### Submission Process:
1. **Fork homebrew-core**: https://github.com/Homebrew/homebrew-core
2. **Add your formula** to `Formula/mox.rb`
3. **Test thoroughly**
4. **Submit pull request**
5. **Respond to maintainer feedback**

## 📊 Current Status

Your mox project is ready for personal tap distribution:

- ✅ **Formula ready**: `packaging/homebrew/mox.rb`
- ✅ **SHA256 updated**: For v6.0.4 release
- ✅ **Dependencies specified**: mpv, curl, jq, python3, etc.
- ✅ **Installation tested**: Works with symlink fixes
- ✅ **Documentation complete**: README and troubleshooting

## 🎯 Quick Commands Summary

```bash
# For users to install:
brew install KrishnaGupta653/tap/mox

# For you to update:
# 1. Create GitHub release
# 2. Get SHA256: curl -sL https://github.com/KrishnaGupta653/mox/archive/vX.X.X.tar.gz | shasum -a 256
# 3. Update Formula/mox.rb in homebrew-tap repo
# 4. Git commit and push
```

## 🎵 Ready to Brew!

Your Homebrew formula is production-ready. Just create the tap repository and follow the steps above!