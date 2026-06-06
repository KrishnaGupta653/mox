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
tar -tzf mox-cli-8.0.0.tgz

# 4. Test local installation
npm install -g ./mox-cli-8.0.0.tgz
mox --help
npm uninstall -g mox-cli
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
npm info mox-cli
```

### Updating Versions

```bash
# 1. Update version (patch/minor/major)
npm version patch  # 7.2.2 -> 7.2.3
npm version minor  # 7.2.2 -> 7.3.0
npm version major  # 7.2.2 -> 8.0.0

# 2. Update VERSION file to match
echo "7.2.3" > VERSION

# 3. Commit changes
git add .
git commit -m "Bump version to 7.2.3"
git push

# 4. Publish
npm publish

# 5. Create Git tag
git tag v7.2.3
git push --tags
```

## Installation for Users

```bash
# Global installation (recommended)
npm install -g mox-cli

# Local installation
npm install mox-cli
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
npm view mox-cli

# Check package contents
npm pack --dry-run

# Test installation
npm install -g mox-cli@latest
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
        node-version: "18"
        registry-url: "https://registry.npmjs.org"
    - run: npm publish
      env:
        NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```
