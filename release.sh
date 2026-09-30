#!/bin/bash
# Bump every version reference to a new version. Edits files only: review, commit,
# push and tag yourself (pushing the v* tag is what publishes to npm and Homebrew).

set -euo pipefail

if [ $# -ne 1 ] || ! [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Usage: ./release.sh X.Y.Z   (e.g. ./release.sh 8.0.3)"
    exit 1
fi

NEW_VERSION="$1"
TODAY="$(date +%Y-%m-%d)"
cd "$(dirname "$0")"

# -i.bak + -E work the same on macOS (BSD) and Linux (GNU) sed
_sed() {
    local expr="$1" file="$2"
    sed -i.bak -E "$expr" "$file"
    rm -f "$file.bak"
}

echo "📝 Bumping to v$NEW_VERSION..."

echo "$NEW_VERSION" > VERSION
npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version >/dev/null

# mox --version/help/doctor and the web UI read VERSION at runtime; the README badge reads npm.
_sed "s|archive/v[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz|archive/v$NEW_VERSION.tar.gz|g" packaging/homebrew/mox-cli.rb

if grep -q '^## \[Unreleased\]' CHANGELOG.md; then
    _sed "s/^## \[Unreleased\].*/## [$NEW_VERSION] - $TODAY/" CHANGELOG.md
elif ! grep -qF "## [$NEW_VERSION]" CHANGELOG.md; then
    tmp="$(mktemp)"
    awk -v v="$NEW_VERSION" -v d="$TODAY" '
        !done && /^## \[/ { print "## [" v "] - " d "\n\n### Changed\n- TODO: describe this release\n"; done = 1 }
        { print }
    ' CHANGELOG.md > "$tmp"
    mv "$tmp" CHANGELOG.md
fi
cp CHANGELOG.md docs/CHANGELOG.md

if ! head -1 packaging/debian/changelog | grep -qF "($NEW_VERSION-1)"; then
    tmp="$(mktemp)"
    {
        printf 'mox-cli (%s-1) unstable; urgency=medium\n\n' "$NEW_VERSION"
        printf '  * New release %s\n  * See CHANGELOG.md for detailed changes\n\n' "$NEW_VERSION"
        printf ' -- Krishna Gupta <krishnagupta653@gmail.com>  %s\n\n' "$(date -R 2>/dev/null || date '+%a, %d %b %Y %H:%M:%S %z')"
        cat packaging/debian/changelog
    } > "$tmp"
    mv "$tmp" packaging/debian/changelog
fi

echo ""
echo "✅ Version references updated to $NEW_VERSION:"
grep -Hn -F "$NEW_VERSION" VERSION package.json packaging/homebrew/mox-cli.rb \
    | sed 's/^/   /'
echo ""
echo "Next (edit the CHANGELOG.md TODO first if one was added):"
echo "   git diff"
echo "   git add -A && git commit -m \"bump: version $NEW_VERSION\" && git push"
echo "   # wait for CI on main to go green, then publish:"
echo "   git tag v$NEW_VERSION && git push origin v$NEW_VERSION"
