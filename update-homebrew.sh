#!/bin/bash
# Auto-update Homebrew formula for current version

set -e

# Get current version
VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
if [ "$VERSION" = "unknown" ]; then
    echo "❌ VERSION file not found"
    exit 1
fi

echo "📦 Updating Homebrew formula for version v$VERSION..."

# Calculate SHA256
echo "🔢 Calculating SHA256..."
SHA256=$(curl -sL "https://github.com/KrishnaGupta653/mox/archive/v$VERSION.tar.gz" | shasum -a 256 | cut -d' ' -f1)

if [ ${#SHA256} -ne 64 ]; then
    echo "❌ Failed to calculate SHA256"
    exit 1
fi

echo "✅ SHA256: $SHA256"

# Update formula
echo "📝 Updating formula..."
sed -i.bak "s|archive/v[0-9]\+\.[0-9]\+\.[0-9]\+\.tar\.gz|archive/v$VERSION.tar.gz|g" packaging/homebrew/mox-cli.rb
sed -i.bak "s|sha256 \"[a-f0-9]\{64\}\"|sha256 \"$SHA256\"|g" packaging/homebrew/mox-cli.rb
rm -f packaging/homebrew/mox-cli.rb.bak

echo "✅ Formula updated!"
echo ""
echo "📋 Summary:"
echo "  Version: v$VERSION"
echo "  URL: https://github.com/KrishnaGupta653/mox/archive/v$VERSION.tar.gz"
echo "  SHA256: $SHA256"
echo ""
echo "💡 Next steps:"
echo "  git add packaging/homebrew/mox-cli.rb"
echo "  git commit -m \"fix: update Homebrew formula for v$VERSION\""
echo "  git push"