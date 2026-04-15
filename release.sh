#!/bin/bash
# Complete version update and release script

set -e

if [ -z "$1" ]; then
    echo "Usage: ./release.sh 6.7.0"
    echo "This will update all version files and create a release"
    exit 1
fi

NEW_VERSION="$1"

echo "🚀 Preparing release v$NEW_VERSION..."

# 1. Update VERSION file
echo "📝 Updating VERSION file..."
echo "$NEW_VERSION" > VERSION

# 2. Update package.json
echo "📝 Updating package.json..."
npm version "$NEW_VERSION" --no-git-tag-version

# 3. Update Homebrew formula URL
echo "📝 Updating Homebrew formula URL..."
sed -i.bak "s|archive/v[0-9]\+\.[0-9]\+\.[0-9]\+\.tar\.gz|archive/v$NEW_VERSION.tar.gz|g" packaging/homebrew/mox-cli.rb
rm -f packaging/homebrew/mox-cli.rb.bak

# 4. Commit changes
echo "💾 Committing changes..."
git add VERSION package.json packaging/homebrew/mox-cli.rb
git commit -m "bump: version $NEW_VERSION"

# 5. Create and push tag
echo "🏷️  Creating tag v$NEW_VERSION..."
git tag "v$NEW_VERSION"

echo "✅ Ready to release!"
echo ""
echo "🚀 To complete the release, run:"
echo "   git push && git push origin v$NEW_VERSION"
echo ""
echo "💡 This will:"
echo "   ✅ Trigger CI automation"
echo "   ✅ Update Homebrew formula SHA256"  
echo "   ✅ Update your Homebrew tap"
echo "   ✅ Publish to npm (if configured)"