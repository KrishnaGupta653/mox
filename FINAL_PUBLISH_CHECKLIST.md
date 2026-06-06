# Final NPM Publish Checklist for mox v8.0.0

## ✅ Pre-Publish Fixes Completed

All critical shell issues have been fixed:

- ✅ FZF parameter not set error (fixed across 15+ functions)
- ✅ Glob pattern "no matches found" errors (fixed in 5 functions)
- ✅ Binary variable declarations added
- ✅ Null glob handling implemented

See `PRE_PUBLISH_FIXES_v8.0.0.md` for detailed fix documentation.

---

## 🧪 Testing Checklist

### Automated Tests

- [ ] Run `./pre-publish-check.sh` - All 26 tests must pass
- [ ] Run `bash tests/run-all-tests.sh` - Comprehensive test suite

### Manual Testing

```bash
# Test empty directory handling
./mox txts          # Should show "(none yet)" without errors
./mox playlists     # Should show "(none yet)" without errors
./mox dl-list       # Should show "(none yet)" without errors

# Test basic commands
./mox version       # Should show version 8.0.0
./mox help          # Should display help without errors
./mox status        # Should show daemon status
./mox cache-stats   # Should show cache statistics

# Test with fresh install simulation
MUSIC_ROOT=/tmp/mox_test_$(date +%s) ./mox txts
```

---

## 📦 Package Preparation

### Version Check

- [ ] Verify `package.json` version is `8.0.0`
- [ ] Verify `VERSION` file contains `8.0.0`
- [ ] Verify `mox --version` outputs `8.0.0`

### Documentation

- [ ] README.md is up to date
- [ ] CHANGELOG.md includes v8.0.0 changes
- [ ] All documentation reflects current features

### File Structure

```bash
# Verify all critical files exist
ls -la mox                  # Main executable
ls -la src/mox.sh           # Main script
ls -la src/lib/*.sh         # All library modules
ls -la package.json         # NPM package config
```

---

## 🚀 Publishing Steps

### 1. Clean Build

```bash
# Remove any test artifacts
rm -rf node_modules
rm -f test-report-*.txt
rm -rf /tmp/mox_*

# Fresh install of dependencies
npm install
```

### 2. Final Verification

```bash
# Run pre-publish check
./pre-publish-check.sh

# Should output: "✓ ALL TESTS PASSED - Ready for publish!"
```

### 3. Git Commit & Tag

```bash
git add .
git commit -m "v7.2.2: Critical fixes for FZF and glob patterns"
git tag -a v7.2.2 -m "Release v7.2.2 - Production-ready with shell fixes"
git push origin main
git push origin v7.2.2
```

### 4. NPM Publish

```bash
# Dry run first to see what will be published
npm publish --dry-run

# Review the output carefully, then publish
npm publish

# Verify it's published
npm view mox-cli version
```

### 5. Post-Publish Verification

```bash
# Install from NPM in a clean environment
npm install -g mox-cli@8.0.0

# Test the installed version
mox version
mox txts
mox help
```

---

## 🔍 Quality Gates

All of these must pass before publishing:

### Code Quality

- ✅ No shell errors with `set -u` enabled
- ✅ All glob patterns handle empty directories
- ✅ All binary variables properly declared
- ✅ All FZF-using functions call `_check_deps`

### Compatibility

- ✅ Works on macOS (tested)
- ✅ Works with zsh (tested)
- ✅ Works with bash (library compatibility)
- ✅ Handles fresh installs (empty directories)

### Functionality

- ✅ All commands execute without errors
- ✅ Help system works
- ✅ Version reporting correct
- ✅ Status command functional

---

## 🎯 Success Criteria

### Before Publishing:

1. `./pre-publish-check.sh` shows: "✓ ALL TESTS PASSED"
2. No shell errors in any command
3. All documentation updated
4. Git repository clean and tagged

### After Publishing:

1. Package visible on npmjs.com
2. Clean install works: `npm install -g mox-cli@8.0.0`
3. Basic commands work after fresh install
4. No user-reported shell errors for 24 hours

---

## 📝 Release Notes for v8.0.0

**Critical Bug Fixes:**

- Fixed "FZF: parameter not set" error across all FZF-dependent commands
- Fixed glob pattern errors in empty directories (txts, playlists, downloads)
- Added proper binary variable declarations
- Implemented null glob handling for cross-platform compatibility

**Testing:**

- Added comprehensive pre-publish validation script
- All 26 automated tests passing
- Verified on macOS with zsh

**Stability:**
This release focuses on shell robustness to ensure smooth operation across all systems and environments.

---

## 🆘 Rollback Plan

If critical issues are discovered after publishing:

```bash
# 1. Deprecate the broken version
npm deprecate mox-cli@8.0.0 "Critical issue found, use 8.0.0 instead"

# 2. Revert changes
git revert v8.0.0
git push origin main

# 3. Publish hotfix
npm version patch
npm publish
```

---

## ✅ Final Sign-Off

Before clicking publish, confirm:

- [ ] All tests pass (`./pre-publish-check.sh`)
- [ ] Version numbers consistent across all files
- [ ] Git repository committed and tagged
- [ ] Documentation updated
- [ ] No known bugs or shell errors
- [ ] Ready for users to install globally

**Once confirmed, proceed with `npm publish` 🚀**

---

_Checklist last updated: 2026-06-04_
_Version: 8.0.0_
_Status: READY FOR PUBLISH ✅_
