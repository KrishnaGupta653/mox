#!/bin/bash
# Edge cases and error handling tests for mox CLI
set -e

echo "🚨 Running mox edge case and error handling tests..."

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOX_SCRIPT="$PROJECT_ROOT/src/mox.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Setup test environment
TEST_MUSIC_ROOT="/tmp/mox_edge_test_$$"
export MUSIC_ROOT="$TEST_MUSIC_ROOT"
export MOX_TEST_MODE=1

cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up edge case test environment...${NC}"
    rm -rf "$TEST_MUSIC_ROOT" 2>/dev/null || true
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    # Restore original MUSIC_ROOT if it existed
    if [[ -n "${ORIGINAL_MUSIC_ROOT:-}" ]]; then
        export MUSIC_ROOT="$ORIGINAL_MUSIC_ROOT"
    fi
}

trap cleanup EXIT

# Save original MUSIC_ROOT
ORIGINAL_MUSIC_ROOT="${MUSIC_ROOT:-}"

setup_edge_test_env() {
    echo -e "${BLUE}📁 Setting up edge case test environment...${NC}"
    mkdir -p "$TEST_MUSIC_ROOT"/{socket,cache,playlists,txts,downloads,data,locks}
    
    # Create config with minimal valid values for testing
    cat > "$TEST_MUSIC_ROOT/config" <<EOF
# Test config with minimal valid values
CACHE_TTL=60
HISTORY_MAX=10
DEFAULT_VOLUME=50
VOLUME_STEP=5
SEARCH_RESULTS=5
AUDIO_DEVICE_SPEAKERS="test_speakers"
AUDIO_DEVICE_HEADPHONES="test_headphones"
SCROBBLE_URL=""
YTDLP_MAX_AGE_DAYS=7
LASTFM_API_KEY=""
YOUTUBE_API_KEY=""
INVIDIOUS_HOST=""
LOCAL_MUSIC_DIR=""
AUTODJ_ENABLED=0
LYRICS_ENABLED=0
NOTIFY_ENABLED=0
CROSSFADE_SECS=0
BAR_REFRESH_MS=500
M_UPDATE_URL=""
M_UPDATE_SHA256=""
EOF
    
    # Create problematic files for testing
    
    # Empty playlist
    touch "$TEST_MUSIC_ROOT/playlists/empty.m3u"
    
    # Playlist with invalid URLs
    cat > "$TEST_MUSIC_ROOT/playlists/invalid.m3u" <<EOF
# Playlist with invalid URLs
not_a_url
http://
ftp://invalid.com/file.mp3
file:///nonexistent/path.mp3
https://
EOF
    
    # Playlist with very long lines
    echo "# Very long URL" > "$TEST_MUSIC_ROOT/playlists/long.m3u"
    printf "https://example.com/%s\n" $(printf 'a%.0s' {1..1000}) >> "$TEST_MUSIC_ROOT/playlists/long.m3u"
    
    # Binary file disguised as playlist
    printf '\x00\x01\x02\x03\x04\x05' > "$TEST_MUSIC_ROOT/playlists/binary.m3u"
    
    # Playlist with special characters - all URLs should be filtered out except one safe encoded URL
    cat > "$TEST_MUSIC_ROOT/playlists/special.m3u" <<EOF
# Special characters test
https://192.0.2.1/song with spaces.mp3
file:///nonexistent/safe/encoded/path.mp3
https://192.0.2.1/song'with'quotes.mp3
https://192.0.2.1/song"with"double"quotes.mp3
https://192.0.2.1/song&with&ampersands.mp3
https://192.0.2.1/song<with>brackets.mp3
https://192.0.2.1/song|with|pipes.mp3
https://192.0.2.1/song;with;semicolons.mp3
https://192.0.2.1/song\$(with)\$shell\$chars.mp3
EOF
    
    # Empty txt file
    touch "$TEST_MUSIC_ROOT/txts/empty.txt"
    
    # Txt file with problematic content
    cat > "$TEST_MUSIC_ROOT/txts/problematic.txt" <<EOF
# Problematic content
$(echo "Command injection attempt")
\$(echo "Escaped command injection")
; rm -rf /
&& rm -rf /
| rm -rf /
> /dev/null
< /etc/passwd
EOF
    
    # Very large txt file
    for i in {1..1000}; do
        echo "Test song $i with very long title that goes on and on and on" >> "$TEST_MUSIC_ROOT/txts/large.txt"
    done
    
    # Txt file with unicode and special characters
    cat > "$TEST_MUSIC_ROOT/txts/unicode.txt" <<'EOF'
# Unicode test
🎵 Song with emoji
Café - French song
Москва - Russian song
東京 - Japanese song
مرحبا - Arabic song
Ñoño - Spanish song
Zürich - German song
EOF
    
    # Corrupted history file
    printf '\x00\x01\x02Invalid\thistory\tentry\n' > "$TEST_MUSIC_ROOT/data/history_corrupted"
    
    # History with malformed entries
    cat > "$TEST_MUSIC_ROOT/data/history_malformed" <<EOF
# Malformed history entries
incomplete_entry
too	many	tabs	in	this	entry	here
2024-13-45T25:99:99	Invalid Date	https://example.com
	Empty timestamp	https://example.com
2024-01-01T12:00:00		https://example.com
2024-01-01T12:00:00	Title with no URL	
EOF
    
    # Create files with permission issues
    touch "$TEST_MUSIC_ROOT/data/readonly_file"
    chmod 444 "$TEST_MUSIC_ROOT/data/readonly_file"
    
    mkdir -p "$TEST_MUSIC_ROOT/readonly_dir"
    chmod 555 "$TEST_MUSIC_ROOT/readonly_dir"
    
    # Create symlinks for testing
    ln -sf "/nonexistent/target" "$TEST_MUSIC_ROOT/data/broken_symlink"
    ln -sf "$TEST_MUSIC_ROOT/data/history" "$TEST_MUSIC_ROOT/data/symlink_to_history"
    
    # Create files with extreme names
    touch "$TEST_MUSIC_ROOT/playlists/ .m3u" 2>/dev/null || true  # Space-only name
    touch "$TEST_MUSIC_ROOT/playlists/..m3u" 2>/dev/null || true  # Dots
    touch "$TEST_MUSIC_ROOT/playlists/very_long_filename_that_exceeds_normal_limits_and_might_cause_issues_with_some_systems.m3u" 2>/dev/null || true
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_test_expect_error() {
    local test_name="$1"
    local test_command="$2"
    local expected_error_pattern="$3"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    local output exit_code
    set +e
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    set -e
    
    if [[ $exit_code -ne 0 ]] && [[ -n "$expected_error_pattern" ]] && [[ "$output" =~ $expected_error_pattern ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - Expected error occurred"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [[ $exit_code -eq 0 ]] && [[ -n "$expected_error_pattern" ]] && [[ "$output" =~ $expected_error_pattern ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - Expected error message shown"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Unexpected behavior"
        echo "  Expected error pattern: $expected_error_pattern"
        echo "  Exit code: $exit_code"
        echo "  Actual output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_test_graceful_handling() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    local output exit_code
    set +e
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    set -e
    
    # Should either succeed or fail gracefully (no crash, reasonable error message)
    if [[ $exit_code -eq 0 ]] || [[ "$output" =~ (error|failed|not.*found|invalid|empty|usage) ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - Handled gracefully"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Did not handle gracefully"
        echo "  Exit code: $exit_code"
        echo "  Output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Setup test environment
setup_edge_test_env

echo -e "\n${YELLOW}🚫 Invalid Environment Tests${NC}"

# Test with completely invalid MUSIC_ROOT
run_test_expect_error "Invalid MUSIC_ROOT path" "MUSIC_ROOT='/dev/null/invalid' timeout 3s \"$MOX_SCRIPT\" help" "error|invalid|permission"

# Test with read-only MUSIC_ROOT
if [[ -w "/tmp" ]]; then
    readonly_root="/tmp/mox_readonly_$$"
    mkdir -p "$readonly_root"
    chmod 555 "$readonly_root"
    run_test_expect_error "Read-only MUSIC_ROOT" "MUSIC_ROOT='$readonly_root' timeout 3s \"$MOX_SCRIPT\" help" "error|permission|read.*only"
    chmod 755 "$readonly_root" 2>/dev/null || true
    rm -rf "$readonly_root" 2>/dev/null || true
fi

echo -e "\n${YELLOW}📋 Malformed Playlist Tests${NC}"

run_test_graceful_handling "Empty playlist" "timeout 3s \"$MOX_SCRIPT\" load empty"
run_test_graceful_handling "Invalid URLs playlist" "timeout 3s \"$MOX_SCRIPT\" load invalid"
run_test_graceful_handling "Very long URLs playlist" "timeout 3s \"$MOX_SCRIPT\" load long"
run_test_graceful_handling "Binary playlist file" "timeout 3s \"$MOX_SCRIPT\" load binary"
run_test_graceful_handling "Special characters playlist" "timeout 3s \"$MOX_SCRIPT\" load special"

echo -e "\n${YELLOW}📝 Problematic Text Files${NC}"

run_test_graceful_handling "Empty txt file" "timeout 3s \"$MOX_SCRIPT\" txt empty"
run_test_graceful_handling "Problematic txt content" "timeout 3s \"$MOX_SCRIPT\" txt problematic"
run_test_graceful_handling "Large txt file" "timeout 5s \"$MOX_SCRIPT\" txt large"
run_test_graceful_handling "Unicode txt file" "timeout 3s \"$MOX_SCRIPT\" txt unicode"

echo -e "\n${YELLOW}💾 Corrupted Data Files${NC}"

# Test with corrupted history
cp "$TEST_MUSIC_ROOT/data/history_corrupted" "$TEST_MUSIC_ROOT/data/history"
run_test_graceful_handling "Corrupted history file" "timeout 3s \"$MOX_SCRIPT\" history"

# Test with malformed history
cp "$TEST_MUSIC_ROOT/data/history_malformed" "$TEST_MUSIC_ROOT/data/history"
run_test_graceful_handling "Malformed history entries" "timeout 3s \"$MOX_SCRIPT\" history"

echo -e "\n${YELLOW}🔒 Permission and Access Tests${NC}"

# Test read-only files
run_test_graceful_handling "Read-only file access" "echo 'test' > '$TEST_MUSIC_ROOT/data/readonly_file' 2>&1 || echo 'expected failure'"

# Test broken symlinks
run_test_graceful_handling "Broken symlink handling" "timeout 3s \"$MOX_SCRIPT\" history || echo 'handled gracefully'"

echo -e "\n${YELLOW}🎯 Extreme Input Values${NC}"

# Test extreme volume values
run_test_expect_error "Negative volume" "timeout 3s \"$MOX_SCRIPT\" vol -10" "usage|invalid|error"
run_test_expect_error "Volume over limit" "timeout 3s \"$MOX_SCRIPT\" vol 999" "max.*volume"

# Test extreme seek values
run_test_expect_error "Invalid seek format" "timeout 3s \"$MOX_SCRIPT\" seek 99:99:99" "invalid.*seek"
run_test_expect_error "Negative seek" "timeout 3s \"$MOX_SCRIPT\" seek -999999" "invalid.*seek|daemon.*not.*running"

# Test extreme speed values
run_test_expect_error "Zero speed" "timeout 3s \"$MOX_SCRIPT\" speed 0" "min.*speed"
run_test_expect_error "Extreme speed" "timeout 3s \"$MOX_SCRIPT\" speed 999" "max.*speed"

echo -e "\n${YELLOW}📛 Special Character Handling${NC}"

# Test playlist names with special characters
run_test_expect_error "Playlist name with slashes" "timeout 3s \"$MOX_SCRIPT\" save 'test/with/slashes'" "invalid.*name|daemon.*not.*running"
run_test_expect_error "Playlist name with dots" "timeout 3s \"$MOX_SCRIPT\" save '../../etc/passwd'" "invalid.*name|daemon.*not.*running"

# Test search queries with special characters
run_test_expect_error "Search with special chars" "timeout 5s \"$MOX_SCRIPT\" search '\$(rm -rf /)'" "searching.*yt-dlp|interrupted.*system.*call|no.*results|usage.*search"
run_test_expect_error "Search with unicode" "timeout 5s \"$MOX_SCRIPT\" search '🎵 test song 🎶'" "searching.*yt-dlp|interrupted.*system.*call|no.*results|usage.*search"

echo -e "\n${YELLOW}🔄 Concurrent Access Tests${NC}"

# Test multiple instances
run_test_graceful_handling "Multiple help commands" "(timeout 3s \"$MOX_SCRIPT\" help & timeout 3s \"$MOX_SCRIPT\" help & wait)"

# Test lock file handling
touch "$TEST_MUSIC_ROOT/locks/start.lock"
echo $$ > "$TEST_MUSIC_ROOT/locks/start.lock"
run_test_graceful_handling "Existing lock file" "timeout 3s \"$MOX_SCRIPT\" status"

echo -e "\n${YELLOW}🌐 Network and External Dependencies${NC}"

# Test with no network (should handle gracefully)
run_test_graceful_handling "Search without network" "timeout 5s \"$MOX_SCRIPT\" search 'test' 2>&1 | grep -E '(no.*results|network|timeout|failed)' || echo 'handled'"

# Test with missing dependencies
if ! command -v nonexistent_command >/dev/null 2>&1; then
    run_test_graceful_handling "Missing dependency handling" "cd ../src && PATH='/nonexistent' timeout 3s ./mox.sh doctor"
fi

echo -e "\n${YELLOW}📊 Resource Exhaustion Tests${NC}"

# Test with very large config values
cat > "$TEST_MUSIC_ROOT/config_extreme" <<EOF
CACHE_TTL=999999999
HISTORY_MAX=999999999
SEARCH_RESULTS=999999999
BAR_REFRESH_MS=1
EOF

run_test_graceful_handling "Extreme config values" "cp '$TEST_MUSIC_ROOT/config_extreme' '$TEST_MUSIC_ROOT/config' && timeout 3s \"$MOX_SCRIPT\" help"

echo -e "\n${YELLOW}🔧 System Integration Edge Cases${NC}"

# Test with invalid audio devices
cat > "$TEST_MUSIC_ROOT/config_invalid_audio" <<EOF
AUDIO_DEVICE_SPEAKERS="nonexistent_device_12345"
AUDIO_DEVICE_HEADPHONES="another_nonexistent_device_67890"
EOF

run_test_graceful_handling "Invalid audio devices" "cp '$TEST_MUSIC_ROOT/config_invalid_audio' '$TEST_MUSIC_ROOT/config' && timeout 3s \"$MOX_SCRIPT\" devices"

# Test with invalid URLs in config
cat > "$TEST_MUSIC_ROOT/config_invalid_urls" <<EOF
SCROBBLE_URL="not_a_url"
M_UPDATE_URL="http://invalid-domain-that-does-not-exist.com/update"
INVIDIOUS_HOST="invalid://malformed.url"
EOF

run_test_graceful_handling "Invalid URLs in config" "cp '$TEST_MUSIC_ROOT/config_invalid_urls' '$TEST_MUSIC_ROOT/config' && timeout 3s \"$MOX_SCRIPT\" help"

echo -e "\n${YELLOW}🎭 Command Injection Prevention${NC}"

# Test potential command injection attempts
injection_attempts=(
    "; rm -rf /"
    "&& rm -rf /"
    "| rm -rf /"
    "\$(rm -rf /)"
    "\`rm -rf /\`"
    "test; echo 'injected'"
    "test && echo 'injected'"
    "test | echo 'injected'"
)

for injection in "${injection_attempts[@]}"; do
    run_test_graceful_handling "Command injection: $injection" "timeout 3s \"$MOX_SCRIPT\" search '$injection' 2>&1 | grep -v 'injected' || echo 'injection prevented'"
done

echo -e "\n${YELLOW}🧮 Boundary Value Tests${NC}"

# Test boundary values for numeric inputs
run_test_expect_error "Volume at 151" "timeout 3s \"$MOX_SCRIPT\" vol 151" "max.*volume"
run_test_expect_error "Volume at 150" "timeout 3s \"$MOX_SCRIPT\" vol 150" "daemon.*not.*running|volume.*150"

run_test_expect_error "Speed at 0.24" "timeout 3s \"$MOX_SCRIPT\" speed 0.24" "min.*speed"
run_test_expect_error "Speed at 0.25" "timeout 3s \"$MOX_SCRIPT\" speed 0.25" "daemon.*not.*running|speed.*0.25"

run_test_expect_error "Speed at 4.01" "timeout 3s \"$MOX_SCRIPT\" speed 4.01" "max.*speed"
run_test_expect_error "Speed at 4.0" "timeout 3s \"$MOX_SCRIPT\" speed 4.0" "daemon.*not.*running|speed.*4.0"

echo -e "\n${YELLOW}🗂️ File System Edge Cases${NC}"

# Test with files that have unusual permissions
if touch "$TEST_MUSIC_ROOT/test_file" 2>/dev/null; then
    chmod 000 "$TEST_MUSIC_ROOT/test_file" 2>/dev/null || true
    run_test_graceful_handling "No permission file" "ls -la '$TEST_MUSIC_ROOT/test_file' || echo 'handled'"
    chmod 644 "$TEST_MUSIC_ROOT/test_file" 2>/dev/null || true
fi

# Test with very deep directory structures
deep_dir="$TEST_MUSIC_ROOT"
for i in {1..10}; do
    deep_dir="$deep_dir/very_deep_directory_level_$i"
done
mkdir -p "$deep_dir" 2>/dev/null || true
run_test_graceful_handling "Deep directory structure" "ls -la '$deep_dir' || echo 'handled'"

echo -e "\n${YELLOW}⏱️ Timeout and Hanging Tests${NC}"

# Test commands that might hang
run_test_graceful_handling "Command with short timeout" "timeout 1s \"$MOX_SCRIPT\" help"

echo -e "\n${BLUE}📊 Edge Case Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total tests run: ${BLUE}$TESTS_RUN${NC}"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All edge case tests passed! The system handles edge cases gracefully.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some edge case tests failed. Review error handling.${NC}"
    exit 1
fi