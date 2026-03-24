# Homebrew Publishing Guide for mox

## Overview

Homebrew publishing involves creating a formula in your own tap (custom repository) or submitting to the main Homebrew repository.

## Prerequisites

1. **GitHub Repository**: Your mox repository must be public
2. **Release**: Create a GitHub release with source tarball
3. **Homebrew**: Install Homebrew on macOS/Linux

## Step 1: Create a GitHub Release

```bash
# 1. Tag your release
git tag v6.0.0
git push --tags

# 2. Create release on GitHub
# Go to: https://github.com/KrishnaGupta653/mox/releases/new
# - Tag: v6.0.0
# - Title: "mox v6.0.0"
# - Description: Release notes
# - Upload: mox-6.0.0.tar.gz (if you have one)
```

## Step 2: Create Your Own Tap

```bash
# 1. Create a new repository named 'homebrew-tap'
# Repository name MUST start with 'homebrew-'
# Example: https://github.com/KrishnaGupta653/homebrew-tap

# 2. Clone the tap repository
git clone https://github.com/KrishnaGupta653/homebrew-tap.git
cd homebrew-tap

# 3. Create Formula directory
mkdir -p Formula
```

## Step 3: Create the Formula

Create `Formula/mox.rb`:

```ruby
class Mox < Formula
  desc "Terminal music CLI - A powerful command-line music player"
  homepage "https://github.com/KrishnaGupta653/mox"
  url "https://github.com/KrishnaGupta653/mox/archive/v6.0.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"
  version "6.0.0"

  depends_on "mpv"
  depends_on "curl"
  depends_on "jq"
  depends_on "python@3.11"
  depends_on "zsh"

  # Optional but recommended dependencies
  depends_on "yt-dlp" => :optional
  depends_on "fzf" => :optional
  depends_on "chafa" => :optional
  depends_on "ffmpeg" => :optional

  def install
    # Install source files
    (libexec/"src").install Dir["src/*"]
    (libexec/"scripts").install Dir["scripts/*"]
    (libexec/"tests").install Dir["tests/*"]
    (libexec/"docs").install Dir["docs/*"]
    
    # Install data files
    libexec.install "VERSION", "LICENSE", "README.md"
    
    # Create wrapper script
    (bin/"mox").write <<~EOS
      #!/bin/bash
      exec "#{libexec}/src/mox.sh" "$@"
    EOS
    
    # Make scripts executable
    chmod "+x", libexec/"src/mox.sh"
    chmod "+x", libexec/"src/music_ui_server.py"
    chmod "+x", libexec/"scripts/install.sh"
  end

  def post_install
    system libexec/"scripts/install.sh"
  end

  test do
    # Test that the command runs
    system bin/"mox", "--help"
  end
end
```

## Step 4: Calculate SHA256

```bash
# Download the release tarball
curl -L https://github.com/KrishnaGupta653/mox/archive/v6.0.0.tar.gz -o mox-6.0.0.tar.gz

# Calculate SHA256
shasum -a 256 mox-6.0.0.tar.gz

# Update the sha256 in your formula
```

## Step 5: Test the Formula

```bash
# Install from your tap
brew install KrishnaGupta653/tap/mox

# Test the installation
mox --help

# Uninstall for testing
brew uninstall mox
```

## Step 6: Publish Your Tap

```bash
# Commit and push your formula
git add Formula/mox.rb
git commit -m "Add mox formula v6.0.0"
git push origin main
```

## Usage for End Users

```bash
# Add your tap
brew tap KrishnaGupta653/tap

# Install mox
brew install mox

# Or install directly
brew install KrishnaGupta653/tap/mox
```

## Updating the Formula

```bash
# 1. Update version in formula
# 2. Update URL and SHA256
# 3. Test installation
brew reinstall KrishnaGupta653/tap/mox

# 4. Commit and push
git add Formula/mox.rb
git commit -m "Update mox to v6.0.1"
git push
```

## Submit to Main Homebrew (Optional)

For inclusion in the main Homebrew repository:

```bash
# 1. Fork homebrew-core
git clone https://github.com/Homebrew/homebrew-core.git

# 2. Create formula in Formula/mox.rb
# 3. Test thoroughly
brew install --build-from-source ./Formula/mox.rb

# 4. Submit PR to homebrew-core
```

## Troubleshooting

### Common Issues

1. **SHA256 mismatch**: Recalculate hash after any changes
2. **Dependencies**: Ensure all system deps are listed
3. **Permissions**: Scripts must be executable
4. **Path issues**: Use `libexec` for internal files, `bin` for executables

### Testing Commands

```bash
# Audit formula
brew audit --strict Formula/mox.rb

# Test installation
brew install --verbose --debug Formula/mox.rb

# Check linkage
brew linkage mox
```