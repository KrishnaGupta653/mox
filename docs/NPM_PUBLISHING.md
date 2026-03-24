# NPM Publishing Guide for mox

## Prerequisites

1. **NPM Account**: Create account at https://www.npmjs.com/
2. **NPM CLI**: Install with `npm install -g npm`
3. **Authentication**: Login with `npm login`

## Pre-Publishing Checklist

```bash
# 1. Verify package structure
npm pack --dry-run

# 2. Run tests
cd tests && ./test.sh

# 3. Check package contents
npm pack
tar -tzf mox-6.0.0.tgz

# 4. Test local installation
npm install -g ./mox-6.0.0.tgz
mox --help
npm uninstall -g mox
```

## Publishing Steps

### First-time Publishing

```bash
# 1. Ensure you're in the root directory
cd /path/to/mox

# 2. Verify package.json is correct
cat package.json

# 3. Publish to NPM
npm publish

# 4. Verify publication
npm info mox
```

### Updating Versions

```bash
# 1. Update version (patch/minor/major)
npm version patch  # 6.0.0 → 6.0.1
npm version minor  # 6.0.0 → 6.1.0
npm version major  # 6.0.0 → 7.0.0

# 2. Update VERSION file to match
echo "6.0.1" > VERSION

# 3. Commit changes
git add .
git commit -m "Bump version to 6.0.1"
git push

# 4. Publish
npm publish

# 5. Create Git tag
git tag v6.0.1
git push --tags
```

## Installation for Users

```bash
# Global installation (recommended)
npm install -g mox

# Local installation
npm install mox
npx mox --help
```

## Troubleshooting

### Common Issues

1. **Name conflicts**: If 'mox' is taken, update package name in package.json
2. **Authentication**: Run `npm login` if publish fails
3. **Version conflicts**: Ensure version is incremented
4. **File permissions**: Ensure mox wrapper script is executable

### Verification Commands

```bash
# Check if package exists
npm view mox

# Check package contents
npm pack --dry-run

# Test installation
npm install -g mox@latest
```

## Automated Publishing with GitHub Actions

The CI workflow in `.github/workflows/ci.yml` can be extended for automatic publishing:

```yaml
  publish-npm:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v3
      with:
        node-version: '18'
        registry-url: 'https://registry.npmjs.org'
    - run: npm publish
      env:
        NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```