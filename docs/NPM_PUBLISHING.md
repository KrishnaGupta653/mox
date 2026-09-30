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
tar -tzf "mox-cli-$(cat VERSION).tgz"

# 4. Test local installation
npm install -g "./mox-cli-$(cat VERSION).tgz"
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

Releases are published by CI, not from your machine. Pushing a `v*` tag publishes to
npm and updates the Homebrew tap in the same run.

```bash
# 1. Bump VERSION + package.json (+ formula URL and changelog stubs); everything else reads VERSION
./release.sh 8.0.3          # edits files only; prints the git commands to run next

# 2. Commit and push main, then wait for CI to go green
git add -A
git commit -m "bump: version 8.0.3"
git push

# 3. Tag to publish (the tag must match VERSION and package.json, or CI stops)
git tag v8.0.3
git push origin v8.0.3
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

The `publish-npm` job in `.github/workflows/ci.yml` uses npm **trusted publishing** (OIDC),
so no npm token is stored in GitHub. It runs only when a `v*` tag is pushed.

```yaml
publish-npm:
  needs: [test, build]
  runs-on: ubuntu-latest
  if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
  permissions:
    contents: read
    id-token: write
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "24"          # needs npm >= 11.5.1
        registry-url: "https://registry.npmjs.org"
    - run: npm publish
```

One-time setup on npmjs.com → `mox-cli` → Settings → Trusted Publisher → GitHub Actions:
owner `KrishnaGupta653`, repository `mox`, workflow `ci.yml`, environment empty.
