# Debian/APT Publishing Guide for mox

## Overview

Publishing to APT involves creating Debian packages (.deb) and hosting them in a repository. You can create your own APT repository or submit to official Debian repositories.

## Prerequisites

1. **Debian/Ubuntu system** for building packages
2. **GPG key** for signing packages
3. **Web hosting** for APT repository (GitHub Pages works)

## Method 1: Personal APT Repository (Recommended)

### Step 1: Install Build Tools

```bash
# On Debian/Ubuntu
sudo apt-get update
sudo apt-get install devscripts debhelper dh-make build-essential lintian
```

### Step 2: Prepare Package Structure

```bash
# 1. Create working directory
mkdir -p ~/debian-packages/mox-6.0.0
cd ~/debian-packages/mox-6.0.0

# 2. Copy your source
cp -r /path/to/mox/* .

# 3. Move debian files to correct location
mv packaging/debian .
```

### Step 3: Update Debian Files

Update `debian/rules` for new structure:

```makefile
#!/usr/bin/make -f

%:
	dh $@

override_dh_auto_install:
	# Create directories
	mkdir -p debian/mox/usr/share/mox
	mkdir -p debian/mox/usr/bin
	
	# Install source files
	cp -r src/* debian/mox/usr/share/mox/
	cp -r scripts debian/mox/usr/share/mox/
	cp -r tests debian/mox/usr/share/mox/
	cp -r docs debian/mox/usr/share/mox/
	
	# Install data files
	cp VERSION LICENSE README.md debian/mox/usr/share/mox/
	
	# Make scripts executable
	chmod +x debian/mox/usr/share/mox/src/mox.sh
	chmod +x debian/mox/usr/share/mox/src/music_ui_server.py
	chmod +x debian/mox/usr/share/mox/scripts/install.sh

override_dh_auto_clean:
	dh_clean
```

### Step 4: Build Package

```bash
# 1. Build the package
debuild -us -uc

# 2. Check package quality
lintian ../mox_6.0.0-1_all.deb

# 3. Test installation
sudo dpkg -i ../mox_6.0.0-1_all.deb
mox --help
sudo dpkg -r mox
```

### Step 5: Create APT Repository

```bash
# 1. Create repository structure
mkdir -p ~/apt-repo/{dists/stable/main/binary-amd64,pool/main}

# 2. Copy package
cp ../mox_6.0.0-1_all.deb ~/apt-repo/pool/main/

# 3. Create Packages file
cd ~/apt-repo
dpkg-scanpackages pool/ /dev/null | gzip -9c > dists/stable/main/binary-amd64/Packages.gz
dpkg-scanpackages pool/ /dev/null > dists/stable/main/binary-amd64/Packages

# 4. Create Release file
cat > dists/stable/Release << EOF
Origin: YourName
Label: YourName
Suite: stable
Codename: stable
Version: 1.0
Architectures: amd64 all
Components: main
Description: Personal APT repository for mox
Date: $(date -Ru)
EOF

# 5. Sign Release file (optional but recommended)
gpg --armor --detach-sign --sign dists/stable/Release
gpg --clearsign --detach-sign --armor --sign --output dists/stable/InRelease dists/stable/Release
```

### Step 6: Host Repository

#### Option A: GitHub Pages

```bash
# 1. Create repository: https://github.com/yourusername/apt-repo
git clone https://github.com/yourusername/apt-repo.git
cd apt-repo

# 2. Copy APT repository files
cp -r ~/apt-repo/* .

# 3. Commit and push
git add .
git commit -m "Add mox package"
git push

# 4. Enable GitHub Pages in repository settings
```

#### Option B: Web Server

```bash
# Upload apt-repo contents to your web server
rsync -av ~/apt-repo/ user@yourserver.com:/var/www/apt/
```

### Step 7: Usage Instructions for Users

```bash
# 1. Add your repository
echo "deb https://yourusername.github.io/apt-repo stable main" | sudo tee /etc/apt/sources.list.d/mox.list

# 2. Add GPG key (if signed)
curl -s https://yourusername.github.io/apt-repo/key.gpg | sudo apt-key add -

# 3. Update and install
sudo apt-get update
sudo apt-get install mox
```

## Method 2: Submit to Official Debian

### Requirements for Official Submission

1. **Debian Developer** status or sponsor
2. **ITP (Intent to Package)** bug report
3. **Strict compliance** with Debian policies
4. **Thorough testing** on multiple architectures

### Process Overview

```bash
# 1. File ITP bug
reportbug wnpp

# 2. Create package following Debian Policy
# 3. Upload to mentors.debian.net
# 4. Find sponsor for review
# 5. Upload to Debian archive
```

## Method 3: Ubuntu PPA (Personal Package Archive)

### Prerequisites

1. **Launchpad account**: https://launchpad.net/
2. **GPG key** uploaded to Launchpad
3. **Source package** (not binary)

### Steps

```bash
# 1. Create source package
debuild -S

# 2. Upload to PPA
dput ppa:yourusername/mox ../mox_6.0.0-1_source.changes

# 3. Wait for build completion
```

### Usage for Users

```bash
# Add PPA
sudo add-apt-repository ppa:yourusername/mox
sudo apt-get update
sudo apt-get install mox
```

## Automated Building with GitHub Actions

Add to `.github/workflows/build-deb.yml`:

```yaml
name: Build Debian Package

on:
  release:
    types: [published]

jobs:
  build-deb:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install build dependencies
      run: |
        sudo apt-get update
        sudo apt-get install devscripts debhelper build-essential
    
    - name: Prepare package
      run: |
        mv packaging/debian .
        
    - name: Build package
      run: |
        debuild -us -uc
        
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: debian-package
        path: ../*.deb
```

## Troubleshooting

### Common Issues

1. **Lintian errors**: Fix all warnings and errors
2. **Dependencies**: Ensure all deps are available in target distro
3. **File permissions**: Scripts must be executable
4. **Architecture**: Use "all" for shell scripts

### Testing Commands

```bash
# Check package contents
dpkg-deb -c mox_6.0.0-1_all.deb

# Check package info
dpkg-deb -I mox_6.0.0-1_all.deb

# Test installation in clean environment
docker run -it ubuntu:22.04
# Install package and test
```

## Maintenance

### Updating Packages

1. **Increment version** in `debian/changelog`
2. **Rebuild package**: `debuild -us -uc`
3. **Update repository**: Re-run `dpkg-scanpackages`
4. **Re-sign Release file**

### Version Naming Convention

- **Upstream version**: 6.0.0
- **Debian revision**: -1, -2, etc.
- **Full version**: 6.0.0-1