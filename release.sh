#!/bin/bash
# Complete version update and release script

set -e

if [ -z "$1" ]; then
    echo "Usage: ./release.sh 7.2.3"
    echo "This will update all version files and create a release"
    exit 1
fi

NEW_VERSION="$1"
TODAY="$(date +%Y-%m-%d)"

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
sed -i.bak -E "s/hardened build v[0-9]+\\.[0-9]+\\.[0-9]+/hardened build v$NEW_VERSION/g; s/\\(v[0-9]+\\.[0-9]+\\.[0-9]+\\)/\(v$NEW_VERSION\)/g" src/mox.sh
rm -f src/mox.sh.bak

# 4. Update release metadata and documentation references
echo "📝 Updating README, docs, and packaging versions..."
sed -i.bak "s|version-[0-9]\+\.[0-9]\+\.[0-9]\+-blue|version-$NEW_VERSION-blue|g" README.md
rm -f README.md.bak

if ! grep -q "## \\[$NEW_VERSION\\]" CHANGELOG.md; then
    tmp_changelog="$(mktemp)"
    {
        sed -n '1,/^## \\[/p' CHANGELOG.md | sed '$d'
        cat << EOF
## [$NEW_VERSION] - $TODAY

### Changed
- Release metadata, packaging, and documentation updated for v$NEW_VERSION.

EOF
        sed -n '/^## \\[/,$p' CHANGELOG.md
    } > "$tmp_changelog"
    mv "$tmp_changelog" CHANGELOG.md
fi

if ! head -1 packaging/debian/changelog | grep -q "($NEW_VERSION-1)"; then
    tmp_deb="$(mktemp)"
    {
        cat << EOF
mox ($NEW_VERSION-1) unstable; urgency=medium

  * New release $NEW_VERSION

 -- Krishna Gupta <krishnagupta653@gmail.com>  $(date -R)

EOF
        cat packaging/debian/changelog
    } > "$tmp_deb"
    mv "$tmp_deb" packaging/debian/changelog
fi

find docs -type f -name '*.md' -exec sed -i.bak -E "s/6\\.0\\.0/$NEW_VERSION/g; s/v6\\.0\\.0/v$NEW_VERSION/g" {} +
find docs -type f -name '*.bak' -delete

# 5. Add ALL changes (including your code changes)
echo "📁 Adding all changes..."
git add .

# 6. Commit everything
echo "💾 Committing all changes..."
git commit -m "bump: version $NEW_VERSION"

# 7. Create tag
echo "🏷️  Creating tag v$NEW_VERSION..."
git tag "v$NEW_VERSION"

# 8. Push everything
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
