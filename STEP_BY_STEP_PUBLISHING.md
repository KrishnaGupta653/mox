# Step-by-Step Publishing Guide for mox v6.0.0

## 🚀 Phase 1: Initial Setup & Git Repository

### Step 1: Create Initial Git Commit
```bash
# From your mox directory
cd /Users/krishnagupta/Downloads/mox

# Add all files to git
git add .

# Create initial commit
git commit -m "Initial release v6.0.0

- Terminal music CLI with web UI
- Support for YouTube, SoundCloud, Bandcamp
- mpv backend with advanced features
- Ready for npm, Homebrew, and Debian publishing"

# Push to GitHub (make sure your remote is set)
git remote add origin https://github.com/KrishnaGupta653/mox.git
git branch -M main
git push -u origin main
```

### Step 2: Create GitHub Release
```bash
# Create and push tag
git tag -a v6.0.0 -m "mox v6.0.0 - Terminal Music CLI"
git push origin v6.0.0
```

**Then on GitHub:**
1. Go to https://github.com/KrishnaGupta653/mox/releases
2. Click "Create a new release"
3. Choose tag: `v6.0.0`
4. Release title: `mox v6.0.0 - Terminal Music CLI`
5. Description: Copy from CHANGELOG.md
6. Click "Publish release"

---

## 📦 Phase 2: npm Publishing (Easiest First)

### Step 3: Test npm Package Locally
```bash
# Test package creation
npm pack

# This creates mox-cli-6.0.0.tgz - inspect it:
tar -tzf mox-cli-6.0.0.tgz

# Test installation locally
npm install -g ./mox-cli-6.0.0.tgz

# Test the installation
mox help
mox --version

# Uninstall test version
npm uninstall -g mox-cli

# Clean up test tarball
rm mox-cli-6.0.0.tgz
```

### Step 4: Publish to npm
```bash
# Login to npm (if not already logged in)
npm login
# Enter your npm username, password, and email

# Verify you're logged in
npm whoami

# Publish the package
npm publish

# Verify publication
npm view mox-cli
```

**✅ npm Publishing Complete!**
- Users can now install with: `npm install -g mox-cli`
- Package available at: https://www.npmjs.com/package/mox-cli

---

## 🍺 Phase 3: Homebrew Publishing

### Step 5: Get Release Tarball SHA256
```bash
# Get the SHA256 of your GitHub release tarball
curl -sL https://github.com/KrishnaGupta653/mox/archive/v6.0.0.tar.gz | shasum -a 256

# Copy the resulting hash (first part before the dash)
```

### Step 6: Update Homebrew Formula
```bash
# Edit the formula file
nano packaging/homebrew/mox.rb

# Update line 5 with the SHA256 hash:
# sha256 "YOUR_HASH_HERE"
```

### Step 7: Create Homebrew Tap Repository
```bash
# Create a new repository on GitHub named: homebrew-tap
# Clone it locally
cd ..  # Go up one directory
git clone https://github.com/KrishnaGupta653/homebrew-tap.git
cd homebrew-tap

# Create Formula directory
mkdir -p Formula

# Copy your formula
cp ../mox/packaging/homebrew/mox.rb Formula/mox.rb

# Commit and push
git add Formula/mox.rb
git commit -m "Add mox v6.0.0 formula"
git push origin main
```

### Step 8: Test Homebrew Installation
```bash
# Test the formula
brew install KrishnaGupta653/tap/mox

# Test it works
mox help

# Uninstall test
brew uninstall mox
```

**✅ Homebrew Publishing Complete!**
- Users can now install with: `brew install KrishnaGupta653/tap/mox`
- Formula available in your tap repository

---

## 📋 Phase 4: Debian/APT Publishing

### Step 9: Prepare Debian Build Environment
```bash
# Install build tools (Ubuntu/Debian)
sudo apt update
sudo apt install build-essential debhelper dh-make devscripts

# Or on macOS with Docker:
# docker run -it --rm -v $(pwd):/workspace ubuntu:22.04 bash
# Then inside container: apt update && apt install build-essential debhelper
```

### Step 10: Prepare Debian Package Structure
```bash
# Copy debian files to root
cp -r packaging/debian .

# Make sure the build script is executable
chmod +x debian/rules
```

### Step 11: Build Debian Package
```bash
# Build unsigned package (for testing)
debuild -us -uc

# This creates several files in parent directory:
# - mox-cli_6.0.0_all.deb (the package)
# - mox-cli_6.0.0.dsc (source description)
# - mox-cli_6.0.0.tar.xz (source tarball)
# - mox-cli_6.0.0_amd64.changes (changes file)
```

### Step 12: Test Debian Package
```bash
# Install the package
sudo dpkg -i ../mox-cli_6.0.0_all.deb

# Fix any dependency issues
sudo apt-get install -f

# Test installation
mox help

# Remove test installation
sudo apt remove mox-cli
```

### Step 13: Sign and Upload Package (Production)
```bash
# For production, sign the package
debuild

# Upload to your repository (see docs/DEBIAN_PUBLISHING.md for details)
# This involves setting up a repository with:
# - GPG signing
# - Repository structure
# - Packages file generation
```

**✅ Debian Publishing Complete!**
- Package built and ready for distribution
- Can be hosted in your own APT repository

---

## 🔄 Phase 5: Verification & Testing

### Step 14: Test All Installation Methods
```bash
# Test npm installation
npm install -g mox-cli
mox help
npm uninstall -g mox-cli

# Test Homebrew installation
brew install KrishnaGupta653/tap/mox
mox help
brew uninstall mox

# Test Debian installation (if on Linux)
sudo dpkg -i mox-cli_6.0.0_all.deb
mox help
sudo apt remove mox-cli
```

### Step 15: Update Documentation
```bash
# Update README.md installation instructions if needed
# Update any badges or links
# Commit any final changes

git add .
git commit -m "Update documentation post-publishing"
git push origin main
```

---

## 📊 Publishing Summary

| Platform | Status | Installation Command | Notes |
|----------|--------|---------------------|-------|
| **npm** | ✅ Ready | `npm install -g mox-cli` | Global package manager |
| **Homebrew** | ✅ Ready | `brew install KrishnaGupta653/tap/mox` | macOS/Linux via tap |
| **Debian** | ✅ Ready | `sudo dpkg -i mox-cli_6.0.0_all.deb` | Manual .deb install |

## 🎯 Recommended Publishing Order

1. **npm** (easiest, immediate global availability)
2. **Homebrew** (good for macOS/Linux users)
3. **Debian** (requires more setup for repository hosting)

## 📞 Support & Maintenance

After publishing:
- Monitor GitHub issues for user feedback
- Watch for installation problems
- Update versions consistently across all platforms
- Keep documentation up to date

## 🎵 You're Ready to Publish!

Follow these steps in order, and your mox terminal music CLI will be available across all major package managers. Each platform has its own audience and use cases, giving users multiple convenient ways to install your software.