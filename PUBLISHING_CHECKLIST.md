# Publishing Checklist for mox v6.0.0

## ✅ Completed Cleanup Tasks

- [x] Removed build artifacts (test reports, tar.gz files, __pycache__)
- [x] Fixed package.json files array conflicts with .npmignore
- [x] Fixed README.md incorrect GitHub and npm links
- [x] Fixed README.md manual install path references
- [x] Resolved duplicate Homebrew formulas (kept packaging/homebrew/mox.rb)
- [x] Fixed Homebrew formula config path references
- [x] Fixed Debian packaging wrapper script issue
- [x] Updated .gitignore patterns
- [x] Removed duplicate CI workflow
- [x] Created CHANGELOG.md at root
- [x] Verified version consistency (6.0.0)
- [x] Ran comprehensive tests - all passing

## 📦 Publishing Preparation

### For npm Publishing

**Prerequisites:**
- npm account with publishing rights
- `NPM_TOKEN` environment variable or `npm login`

**Ready to publish:**
```bash
# The package is ready - just run:
npm publish

# Or for testing:
npm pack  # Creates tarball for inspection
```

**What gets published:**
- Main executable: `mox`
- Source files: `src/`
- Installation script: `scripts/`
- Documentation: `README.md`, `CHANGELOG.md`, `LICENSE`, `VERSION`

### For Homebrew Publishing

**Prerequisites:**
- Create GitHub release with tag `v6.0.0`
- Update SHA256 in `packaging/homebrew/mox.rb`
- Create separate tap repository

**Steps:**
1. Create GitHub release:
   ```bash
   git tag v6.0.0
   git push origin v6.0.0
   # Create release on GitHub
   ```

2. Get SHA256 of release tarball:
   ```bash
   curl -sL https://github.com/KrishnaGupta653/mox/archive/v6.0.0.tar.gz | shasum -a 256
   ```

3. Update `packaging/homebrew/mox.rb` with the SHA256

4. Copy formula to tap repository:
   ```bash
   # In your homebrew-tap repository:
   cp packaging/homebrew/mox.rb Formula/mox.rb
   git add Formula/mox.rb
   git commit -m "Add mox v6.0.0"
   git push
   ```

### For APT/Debian Publishing

**Prerequisites:**
- Debian build environment
- GPG key for signing
- Repository hosting setup

**Ready files:**
- `packaging/debian/` - Complete Debian package configuration
- Fixed wrapper script issue for proper installation

**Steps:**
1. Move debian files to root:
   ```bash
   cp -r packaging/debian .
   ```

2. Build package:
   ```bash
   debuild -us -uc  # Unsigned build for testing
   debuild          # Signed build for production
   ```

3. Upload to repository (see `docs/DEBIAN_PUBLISHING.md`)

## 🔧 Configuration Notes

### Package Managers Configuration

**npm:** 
- Package name: `mox`
- Global installation: `npm install -g mox`
- Postinstall runs: `./scripts/install.sh`

**Homebrew:**
- Formula: `packaging/homebrew/mox.rb`
- Installation: `brew install KrishnaGupta653/tap/mox`
- Uses libexec pattern with wrapper script

**Debian:**
- Package name: `mox-cli`
- Installation: `apt install mox-cli`
- Files go to `/usr/share/mox/` with wrapper in `/usr/bin/mox`

### Runtime Requirements

**Essential:**
- zsh
- python3 (≥3.6)
- mpv
- curl
- jq

**Recommended:**
- yt-dlp
- fzf
- chafa
- ffmpeg

## 🚀 Final Steps Before Publishing

1. **Create initial git commit:**
   ```bash
   git add .
   git commit -m "Initial release v6.0.0"
   git push origin master
   ```

2. **Test npm package locally:**
   ```bash
   npm pack
   npm install -g ./mox-6.0.0.tgz
   mox help  # Test installation
   npm uninstall -g mox  # Cleanup
   ```

3. **Create GitHub release:**
   - Tag: `v6.0.0`
   - Title: `mox v6.0.0 - Terminal Music CLI`
   - Description: Use content from CHANGELOG.md

4. **Publish to npm:**
   ```bash
   npm publish
   ```

5. **Update Homebrew formula and publish to tap**

6. **Build and publish Debian package**

## 📋 Post-Publishing Tasks

- [ ] Update documentation with installation instructions
- [ ] Test installations from all package managers
- [ ] Monitor for issues and user feedback
- [ ] Update version badges in README if needed

## 🎵 Ready to Rock!

The codebase is clean, tested, and ready for publishing across all three package managers. All major issues have been resolved and the package structure is consistent.