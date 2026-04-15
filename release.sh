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

# 4. Add ALL changes (including your code changes)
echo "📁 Adding all changes..."
git add .

# 5. Commit everything
echo "💾 Committing all changes..."
git commit -m "bump: version $NEW_VERSION"

# 6. Create tag
echo "🏷️  Creating tag v$NEW_VERSION..."
git tag "v$NEW_VERSION"

# 7. Push everything
echo "🚀 Pushing to GitHub..."
git push
echo "🏷️  Pushing tag..."
git push origin "v$NEW_VERSION"

echo ""
echo "✅ Release v$NEW_VERSION completed!"
echo ""
echo "💡 What happened:"
echo "   ✅ All changes committed and pushed"
echo "   ✅ Tag created and pushed" 
echo "   ✅ CI automation triggered"
echo "   ✅ Homebrew tap will auto-update"
echo "   ✅ npm will auto-publish (if configured)"
echo ""
echo "🔗 Check progress: https://github.com/KrishnaGupta653/mox/actions"