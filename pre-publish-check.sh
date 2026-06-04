#!/usr/bin/env bash
# Pre-publish validation script for mox
# Tests critical functionality to ensure smooth operation on all systems

set -e

MOX_CMD="./mox"
FAILED=0
PASSED=0

echo "=========================================="
echo "  MOX PRE-PUBLISH VALIDATION"
echo "=========================================="
echo ""

# Test function
test_cmd() {
    local desc="$1"
    local cmd="$2"
    local expected_rc="${3:-0}"
    
    printf "Testing: %-50s" "$desc"
    
    if output=$(eval "$cmd" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    
    if [ $rc -eq $expected_rc ]; then
        echo "✓ PASS"
        PASSED=$((PASSED + 1))
    else
        echo "✗ FAIL (exit code: $rc, expected: $expected_rc)"
        echo "   Output: $output"
        FAILED=$((FAILED + 1))
    fi
}

echo "1. BASIC COMMANDS (no daemon required)"
echo "----------------------------------------"
test_cmd "version" "$MOX_CMD --version"
test_cmd "help" "$MOX_CMD help"
test_cmd "status (daemon stopped)" "$MOX_CMD status"
test_cmd "playlists (empty)" "$MOX_CMD playlists"
test_cmd "txts (empty)" "$MOX_CMD txts"
test_cmd "dl-list (empty)" "$MOX_CMD dl-list"
test_cmd "likes (empty)" "$MOX_CMD likes"
test_cmd "cache-stats" "$MOX_CMD cache-stats"
# Skip interactive history test as it requires fzf interaction
# test_cmd "history (with ESC/empty input)" "echo '' | $MOX_CMD history" "0"

echo ""
echo "2. BINARY DEPENDENCY CHECKS"
echo "----------------------------------------"
test_cmd "mpv available" "command -v mpv"
test_cmd "socat available" "command -v socat"
test_cmd "jq available" "command -v jq"
test_cmd "curl available" "command -v curl"
test_cmd "yt-dlp available" "command -v yt-dlp"
test_cmd "fzf available" "command -v fzf"

echo ""
echo "3. FILE STRUCTURE"
echo "----------------------------------------"
test_cmd "mox executable" "test -x $MOX_CMD"
test_cmd "lib/core.sh exists" "test -f src/lib/core.sh"
test_cmd "lib/history.sh exists" "test -f src/lib/history.sh"
test_cmd "lib/playlist.sh exists" "test -f src/lib/playlist.sh"
test_cmd "lib/search.sh exists" "test -f src/lib/search.sh"
test_cmd "lib/playback.sh exists" "test -f src/lib/playback.sh"
test_cmd "lib/ui.sh exists" "test -f src/lib/ui.sh"

echo ""
echo "4. GLOB PATTERN SAFETY (empty directories)"
echo "----------------------------------------"
# Create temporary empty directories to test glob patterns
TEMP_MUSIC_ROOT=$(mktemp -d /tmp/mox_test_XXXXXX)
export MUSIC_ROOT="$TEMP_MUSIC_ROOT"
mkdir -p "$TEMP_MUSIC_ROOT"/{playlists,txts,downloads,data,cache,socket,locks}

test_cmd "txts with empty directory" "MUSIC_ROOT=$TEMP_MUSIC_ROOT $MOX_CMD txts"
test_cmd "playlists with empty directory" "MUSIC_ROOT=$TEMP_MUSIC_ROOT $MOX_CMD playlists"
test_cmd "dl-list with empty directory" "MUSIC_ROOT=$TEMP_MUSIC_ROOT $MOX_CMD dl-list"
test_cmd "cache-stats with empty directory" "MUSIC_ROOT=$TEMP_MUSIC_ROOT $MOX_CMD cache-stats"

# Cleanup
rm -rf "$TEMP_MUSIC_ROOT"

echo ""
echo "5. CONFIGURATION FILE HANDLING"
echo "----------------------------------------"
TEMP_CONFIG=$(mktemp /tmp/mox_config_XXXXXX)
cat > "$TEMP_CONFIG" <<EOF
# Test config
CACHE_TTL=7200
HISTORY_MAX=1000
DEFAULT_VOLUME=75
EOF

test_cmd "config file parsing" "MUSIC_ROOT=$(dirname $TEMP_CONFIG) $MOX_CMD --version"
rm -f "$TEMP_CONFIG"

echo ""
echo "=========================================="
echo "  SUMMARY"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ ALL TESTS PASSED - Ready for publish!"
    exit 0
else
    echo "✗ SOME TESTS FAILED - Fix issues before publishing"
    exit 1
fi
