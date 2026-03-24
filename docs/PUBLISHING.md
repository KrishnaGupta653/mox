# 📦 Publishing Guide for mox

This guide covers how to publish **mox** to various package managers and distribution channels.

## 🚀 Quick Release Checklist

Before publishing a new release:

1. **Update version numbers**:
   - [ ] Update `VERSION` file
   - [ ] Update `package.json` version
   - [ ] Update `mox.rb` version
   - [ ] Update `debian/changelog`

2. **Run tests**:
   ```bash
   ./test.sh                    # Basic tests
   ./test-comprehensive.sh      # Full test suite
   ```

3. **Clean repository**:
   ```bash
   rm -rf __pycache__ *.pyc .DS_Store *~
   ```

4. **Create git tag**:
   ```bash
   git tag -a v6.0.0 -m "Release v6.0.0"
   git push origin v6.0.0
   ```

## 📦 NPM Publishing

### Prerequisites
- npm account with publishing rights
- `NPM_TOKEN` environment variable or `npm login`

### Manual Publishing
```bash
# 1. Verify package contents
npm pack --dry-run

# 2. Test installation locally
npm install -g ./mox-*.tgz

# 3. Publish to npm
npm publish

# 4. Verify publication
npm info mox
```

### Automated Publishing
Publishing is automated via GitHub Actions when you create a release:

1. Create a release on GitHub
2. CI/CD pipeline will automatically publish to npm
3. Requires `NPM_TOKEN` secret in repository settings

### NPM Package Details
- **Package name**: `mox`
- **Global command**: `mox`
- **Files included**: See `package.json` `files` array
- **Post-install**: Runs `install.sh` automatically

## 🍺 Homebrew Publishing

### Prerequisites
- Homebrew tap repository: `KrishnaGupta653/homebrew-tap`
- Release tarball with SHA256 hash

### Steps

1. **Create release tarball**:
   ```bash
   VERSION=$(cat VERSION)
   git archive --format=tar.gz --prefix=mox-${VERSION}/ HEAD > mox-${VERSION}.tar.gz
   ```

2. **Calculate SHA256**:
   ```bash
   sha256sum mox-${VERSION}.tar.gz
   # macOS: shasum -a 256 mox-${VERSION}.tar.gz
   ```

3. **Update formula**:
   ```bash
   # Update mox.rb with new version and SHA256
   sed -i "s/sha256 \".*\"/sha256 \"NEW_SHA256_HERE\"/" mox.rb
   ```

4. **Test formula locally**:
   ```bash
   brew install --build-from-source ./mox.rb
   brew test mox
   brew uninstall mox
   ```

5. **Push to tap repository**:
   ```bash
   # In your homebrew-tap repository
   cp mox.rb Formula/
   git add Formula/mox.rb
   git commit -m "Update mox to v6.0.0"
   git push origin main
   ```

### Homebrew Installation
Users can install with:
```bash
brew tap KrishnaGupta653/tap
brew install mox
```

## 🐧 APT/Debian Publishing

### Prerequisites
- Debian package building tools: `build-essential`, `debhelper`, `devscripts`
- GPG key for package signing (optional but recommended)

### Building Debian Package

1. **Install build dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install build-essential debhelper devscripts
   ```

2. **Build package**:
   ```bash
   # Build unsigned package (for testing)
   debuild -us -uc -b
   
   # Build signed package (for distribution)
   debuild -b
   ```

3. **Test package**:
   ```bash
   sudo dpkg -i ../mox_6.0.0-1_all.deb
   mox help
   sudo dpkg -r mox
   ```

### Package Repository Setup

For a proper APT repository, you'll need to:

1. **Create repository structure**:
   ```bash
   mkdir -p apt-repo/{dists/stable/main/binary-amd64,pool/main}
   ```

2. **Add packages**:
   ```bash
   cp mox_*.deb apt-repo/pool/main/
   ```

3. **Generate package index**:
   ```bash
   cd apt-repo
   dpkg-scanpackages pool/ /dev/null | gzip -9c > dists/stable/main/binary-amd64/Packages.gz
   ```

4. **Create Release file**:
   ```bash
   cd dists/stable
   apt-ftparchive release . > Release
   ```

5. **Sign Release file** (optional):
   ```bash
   gpg --armor --detach-sign --sign Release
   ```

### Users Installation
Users can install with:
```bash
# Add repository (if using custom repo)
echo "deb [trusted=yes] https://your-repo.com/apt stable main" | sudo tee /etc/apt/sources.list.d/mox.list
sudo apt update
sudo apt install mox

# Or install directly from .deb file
wget https://github.com/KrishnaGupta653/mox/releases/download/v6.0.0/mox_6.0.0-1_all.deb
sudo dpkg -i mox_6.0.0-1_all.deb
sudo apt-get install -f  # Fix dependencies if needed
```

## 🔄 Automated Release Process

The repository includes GitHub Actions for automated releases:

### Workflow Triggers
- **Push to main/develop**: Runs tests
- **Pull requests**: Runs full test suite
- **Release creation**: Builds and publishes packages

### Required Secrets
Set these in GitHub repository settings:

- `NPM_TOKEN`: npm authentication token
- `GPG_PRIVATE_KEY`: For signing packages (optional)
- `GPG_PASSPHRASE`: GPG key passphrase (optional)

### Creating a Release

1. **Update versions** (see checklist above)

2. **Create GitHub release**:
   ```bash
   # Via GitHub CLI
   gh release create v6.0.0 --title "v6.0.0" --notes "See CHANGELOG.md"
   
   # Or use GitHub web interface
   ```

3. **Automated actions**:
   - ✅ Run comprehensive tests
   - 📦 Build npm package and publish
   - 🍺 Validate Homebrew formula
   - 🐧 Build Debian package
   - 📋 Create release assets
   - 🔔 Send notifications

## 🔍 Verification

After publishing, verify installations:

### NPM
```bash
npm install -g mox
mox help
npm uninstall -g mox
```

### Homebrew
```bash
brew install KrishnaGupta653/tap/mox
mox help
brew uninstall mox
```

### APT/Debian
```bash
sudo dpkg -i mox_*.deb
mox help
sudo dpkg -r mox
```

## 🐛 Troubleshooting

### Common Issues

**NPM publish fails**:
- Check `NPM_TOKEN` is valid
- Verify version number is higher than published
- Ensure package.json is valid

**Homebrew formula fails**:
- Verify SHA256 hash matches tarball
- Check all dependencies are available in Homebrew
- Test formula locally first

**Debian package fails**:
- Check debian/control dependencies
- Verify all files exist and have correct permissions
- Test build in clean environment

### Getting Help

- 📖 Check existing issues: https://github.com/KrishnaGupta653/mox/issues
- 💬 Start a discussion: https://github.com/KrishnaGupta653/mox/discussions
- 📧 Contact maintainer: krishnagupta653@gmail.com

## 📊 Release Metrics

Track these metrics for each release:

- Download counts (npm, GitHub releases)
- Installation success rates
- User feedback and issues
- Performance benchmarks
- Test coverage

---

**Happy publishing!** 🚀