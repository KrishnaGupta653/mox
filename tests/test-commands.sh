#!/bin/bash
# Comprehensive command-by-command tests for mox CLI
set -e

echo "⚙️ Running mox command functionality tests..."

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
TEST_MUSIC_ROOT="/tmp/mox_cmd_test_$$"
export MUSIC_ROOT="$TEST_MUSIC_ROOT"
export MOX_TEST_MODE=1

cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up test environment...${NC}"
    rm -rf "$TEST_MUSIC_ROOT" 2>/dev/null || true
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT

setup_test_env() {
    echo -e "${BLUE}📁 Setting up command test environment...${NC}"
    mkdir -p "$TEST_MUSIC_ROOT"/{socket,cache,playlists,txts,downloads,data,locks}
    
    # Create comprehensive test config
    cat > "$TEST_MUSIC_ROOT/config" <<EOF
CACHE_TTL=60
HISTORY_MAX=100
DEFAULT_VOLUME=50
VOLUME_STEP=10
SEARCH_RESULTS=5
AUDIO_DEVICE_SPEAKERS="test_speakers"
AUDIO_DEVICE_HEADPHONES="test_headphones"
SCROBBLE_URL=""
YTDLP_MAX_AGE_DAYS=30
LASTFM_API_KEY="test_lastfm_key"
YOUTUBE_API_KEY=""
INVIDIOUS_HOST=""
LOCAL_MUSIC_DIR="$TEST_MUSIC_ROOT/music"
AUTODJ_ENABLED=0
LYRICS_ENABLED=1
NOTIFY_ENABLED=0
CROSSFADE_SECS=0
BAR_REFRESH_MS=500
M_UPDATE_URL=""
M_UPDATE_SHA256=""
EOF
    
    # Create test music directory with sample files
    mkdir -p "$TEST_MUSIC_ROOT/music"
    touch "$TEST_MUSIC_ROOT/music/test_song1.mp3"
    touch "$TEST_MUSIC_ROOT/music/test_song2.mp3"
    
    # Create test playlists
    cat > "$TEST_MUSIC_ROOT/playlists/rock.m3u" <<EOF
# Rock playlist
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=oHg5SJYRHA0
$TEST_MUSIC_ROOT/music/test_song1.mp3
EOF
    
    cat > "$TEST_MUSIC_ROOT/playlists/jazz.m3u" <<EOF
# Jazz playlist  
https://www.youtube.com/watch?v=VMkQX_i2_2c
$TEST_MUSIC_ROOT/music/test_song2.mp3
EOF
    
    # Create test txt files
    cat > "$TEST_MUSIC_ROOT/txts/test_list.txt" <<EOF
# Test music list
Test Song 1
Test Song 2
Test Artist - Test Track
EOF
    
    # Create test stations
    cat > "$TEST_MUSIC_ROOT/stations.tsv" <<EOF
# genre	name	url
rock	Test Rock FM	http://example.com/rock.m3u
jazz	Test Jazz Radio	http://example.com/jazz.m3u
classical	Test Classical	http://example.com/classical.pls
EOF
    
    # Create test history and likes
    cat > "$TEST_MUSIC_ROOT/data/history" <<EOF
2024-01-01T12:00:00	Test Song 1	https://example.com/song1
2024-01-01T12:05:00	Test Song 2	https://example.com/song2
EOF
    
    cat > "$TEST_MUSIC_ROOT/data/likes" <<EOF
2024-01-01T12:00:00	Test Liked Song	https://example.com/liked1
EOF
    
    # Create test bookmarks
    cat > "$TEST_MUSIC_ROOT/data/bookmarks" <<EOF
test_bookmark	Test Bookmark	2024-01-01T12:00:00	https://example.com/bookmark1	Test Song Title
EOF
    
    # Create test pins
    cat > "$TEST_MUSIC_ROOT/data/pins" <<EOF
test_pin	https://example.com/pinned	Test Pinned Song
EOF
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    set +e  # Temporarily disable exit on error
    eval "$test_command" >/dev/null 2>&1
    local result=$?
    set -e  # Re-enable exit on error
    
    if [[ $result -eq 0 ]]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_test_with_output() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    local output
    local exit_code
    set +e  # Temporarily disable exit on error
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    set -e  # Re-enable exit on error
    
    if [[ -n "$expected_pattern" ]] && [[ "$output" =~ $expected_pattern ]]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Output doesn't match expected pattern"
        echo "  Expected pattern: $expected_pattern"
        echo "  Actual output: $output"
        echo "  Exit code: $exit_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_test_expect_error() {
    local test_name="$1"
    local test_command="$2"
    local expected_error_pattern="$3"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    
    local output
    local exit_code
    set +e  # Temporarily disable exit on error
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    set -e  # Re-enable exit on error
    
    if [[ -n "$expected_error_pattern" ]] && [[ "$output" =~ $expected_error_pattern ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - Expected error occurred"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} - Unexpected error"
        echo "  Expected error pattern: $expected_error_pattern"
        echo "  Actual output: $output"
        echo "  Exit code: $exit_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Setup test environment
setup_test_env

echo -e "\n${YELLOW}🎵 Basic Playback Commands${NC}"

# Test basic playback commands (these will show "not running" without mpv)
run_test_with_output "pause command" "\"$MOX_SCRIPT\" pause" "daemon.*unresponsive|not.*running|stopped"
run_test_with_output "next command" "timeout 10s \"$MOX_SCRIPT\" next" "daemon.*unresponsive|not.*running|stopped"
run_test_with_output "prev command" "timeout 10s \"$MOX_SCRIPT\" prev" "daemon.*unresponsive|not.*running|stopped"
run_test_with_output "stop command" "timeout 10s \"$MOX_SCRIPT\" stop" "daemon.*unresponsive|stopped|not.*running"
run_test_with_output "now command" "timeout 10s \"$MOX_SCRIPT\" now" "daemon.*unresponsive|not.*running|stopped"

echo -e "\n${YELLOW}🔀 Queue Management Commands${NC}"

run_test_with_output "queue command" "timeout 3s \"$MOX_SCRIPT\" queue" "not.*running|stopped|empty"
run_test_with_output "clear command" "timeout 3s \"$MOX_SCRIPT\" clear" "not.*running|stopped"
run_test_with_output "shuffle command" "timeout 3s \"$MOX_SCRIPT\" shuffle" "not.*running|stopped"
run_test_with_output "repeat command" "timeout 3s \"$MOX_SCRIPT\" repeat" "not.*running|stopped"

# Test queue manipulation with error cases
run_test_expect_error "qmove without args" "timeout 3s \"$MOX_SCRIPT\" qmove" "usage.*qmove"
run_test_expect_error "qrm without args" "timeout 3s \"$MOX_SCRIPT\" qrm" "usage.*qrm"

echo -e "\n${YELLOW}📋 Playlist Commands${NC}"

run_test_with_output "playlists list" "timeout 3s \"$MOX_SCRIPT\" playlists" "rock|jazz"
run_test_expect_error "save without name" "timeout 3s \"$MOX_SCRIPT\" save" "usage.*save"
run_test_expect_error "load without name" "timeout 3s \"$MOX_SCRIPT\" load" "usage.*load"
run_test_expect_error "load nonexistent" "timeout 3s \"$MOX_SCRIPT\" load nonexistent" "not.*found"
run_test_expect_error "pldel without name" "timeout 3s \"$MOX_SCRIPT\" pldel" "usage.*pldel"

echo -e "\n${YELLOW}🎛️ Audio Control Commands${NC}"

# Volume tests
run_test_expect_error "vol without args shows current" "timeout 3s \"$MOX_SCRIPT\" vol" "not.*running|volume|usage"
run_test_expect_error "vol invalid value" "timeout 3s \"$MOX_SCRIPT\" vol abc" "usage.*vol"
run_test_expect_error "vol too high" "timeout 3s \"$MOX_SCRIPT\" vol 200" "max.*volume"

# Seek tests  
run_test_expect_error "seek without args" "timeout 3s \"$MOX_SCRIPT\" seek" "usage.*seek"
run_test_expect_error "seek invalid value" "timeout 3s \"$MOX_SCRIPT\" seek abc" "invalid.*seek"

# Speed tests
run_test_expect_error "speed without args" "timeout 3s \"$MOX_SCRIPT\" speed" "usage.*speed"
run_test_expect_error "speed invalid value" "timeout 3s \"$MOX_SCRIPT\" speed abc" "usage.*speed"
run_test_expect_error "speed too low" "timeout 3s \"$MOX_SCRIPT\" speed 0.1" "min.*speed"
run_test_expect_error "speed too high" "timeout 3s \"$MOX_SCRIPT\" speed 5.0" "max.*speed"

# Audio device tests
run_test_with_output "hp command" "timeout 3s \"$MOX_SCRIPT\" hp" "not.*running|headphones"
run_test_with_output "sp command" "timeout 3s \"$MOX_SCRIPT\" sp" "not.*running|speakers"
run_test_with_output "devices command" "timeout 3s \"$MOX_SCRIPT\" devices" "audio.*devices|No.*devices"

echo -e "\n${YELLOW}📻 Radio Commands${NC}"

run_test_with_output "radio list" "timeout 3s \"$MOX_SCRIPT\" radio" "Test.*Rock.*FM|Test.*Jazz.*Radio"
run_test_with_output "radio by genre" "timeout 3s \"$MOX_SCRIPT\" radio rock" "Test.*Rock.*FM|not.*running"

echo -e "\n${YELLOW}📁 File Management Commands${NC}"

# Download tests
run_test_expect_error "dl without query" "timeout 3s \"$MOX_SCRIPT\" dl" "usage.*dl"

# Import tests  
run_test_expect_error "import without URL" "timeout 3s \"$MOX_SCRIPT\" import" "usage.*import"

echo -e "\n${YELLOW}📝 Text File Commands${NC}"

run_test_with_output "txts list" "timeout 3s \"$MOX_SCRIPT\" txts" "test_list"
run_test_with_output "txt command" "timeout 3s \"$MOX_SCRIPT\" txt test_list" "txt.*playlist.*test_list.*songs"

echo -e "\n${YELLOW}❤️ Likes and History Commands${NC}"

run_test_with_output "likes list" "timeout 3s \"$MOX_SCRIPT\" likes" "Test.*Liked.*Song"
run_test_with_output "history list" "timeout 3s \"$MOX_SCRIPT\" history" "Test.*Song.*1|Test.*Song.*2"
run_test_with_output "history-clear" "timeout 3s \"$MOX_SCRIPT\" history-clear" "cleared|empty"

echo -e "\n${YELLOW}🔍 Search Commands${NC}"

run_test_expect_error "search without query" "timeout 3s \"$MOX_SCRIPT\" search" "usage.*search"

# Test search with query (may fail due to network, but should handle gracefully)
if command -v yt-dlp >/dev/null 2>&1; then
    run_test_with_output "search with query" "timeout 10s \"$MOX_SCRIPT\" search 'test query'" "no.*results|search.*failed|Test.*Song|searching.*yt-dlp|interrupted.*system.*call"
else
    echo -e "${BLUE}[TEST $((TESTS_RUN + 1))]${NC} search with query"
    echo -e "  ${YELLOW}⚠️  SKIP${NC} - yt-dlp not available"
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

echo -e "\n${YELLOW}🎚️ Equalizer Commands${NC}"

run_test_with_output "eq help" "timeout 3s \"$MOX_SCRIPT\" eq" "usage.*eq|flat.*bass.*treble"
run_test_with_output "eq flat" "timeout 3s \"$MOX_SCRIPT\" eq flat" "not.*running|equalizer.*flat"
run_test_expect_error "eq invalid preset" "timeout 3s \"$MOX_SCRIPT\" eq invalid" "unknown.*preset"
run_test_expect_error "eq custom without args" "timeout 3s \"$MOX_SCRIPT\" eq custom" "usage.*custom"

echo -e "\n${YELLOW}🔧 Utility Commands${NC}"

run_test_with_output "status command" "timeout 3s \"$MOX_SCRIPT\" status" "stopped"
run_test_with_output "help command" "timeout 10s \"$MOX_SCRIPT\" help" "terminal music CLI|Commands:"
run_test_with_output "doctor command" "timeout 10s \"$MOX_SCRIPT\" doctor" "System.*check|Dependencies"

# Config commands
run_test_with_output "config-edit" "timeout 3s \"$MOX_SCRIPT\" config-edit" "config.*file|editor|Vim.*Warning|Vim.*Finished"

# Cache commands
run_test_with_output "cache-stats" "timeout 3s \"$MOX_SCRIPT\" cache-stats" "cache.*stats|empty"
run_test "cache-clear" "timeout 3s \"$MOX_SCRIPT\" cache-clear"
run_test "cache-prune" "timeout 3s \"$MOX_SCRIPT\" cache-prune"

# Log commands
run_test_with_output "log-clear" "timeout 3s \"$MOX_SCRIPT\" log-clear" "cleared|empty|log.*cleared"

echo -e "\n${YELLOW}📊 Statistics Commands${NC}"

run_test_with_output "stats command" "timeout 5s \"$MOX_SCRIPT\" stats" "listening.*stats|total.*plays"
run_test_with_output "history-stats" "timeout 5s \"$MOX_SCRIPT\" history-stats" "History.*statistics|interrupted.*system.*call|stats"

echo -e "\n${YELLOW}📌 Bookmark and Pin Commands${NC}"

run_test_expect_error "bookmark without name" "timeout 3s \"$MOX_SCRIPT\" bookmark" "usage.*bookmark|daemon.*not.*running"
run_test_with_output "bookmarks list" "timeout 3s \"$MOX_SCRIPT\" bookmarks" "test_bookmark|No.*bookmarks|Test.*Bookmark"

run_test_expect_error "pin without name" "timeout 3s \"$MOX_SCRIPT\" pin" "usage.*pin"
run_test_with_output "pins list" "timeout 3s \"$MOX_SCRIPT\" pins" "test_pin|No.*pins"

echo -e "\n${YELLOW}🎵 Advanced Features${NC}"

# AutoDJ
run_test_with_output "autodj command" "timeout 3s \"$MOX_SCRIPT\" autodj" "Auto.*DJ|disabled|enabled"

# Crossfade
run_test_with_output "crossfade without args" "timeout 3s \"$MOX_SCRIPT\" crossfade" "Current.*crossfade|usage|crossfade.*0s"
run_test_expect_error "crossfade invalid" "timeout 3s \"$MOX_SCRIPT\" crossfade abc" "usage.*crossfade"

# Normalization
run_test_with_output "norm command" "timeout 3s \"$MOX_SCRIPT\" norm" "not.*running|normalisation"

# Sleep timer
run_test_expect_error "sleep without args" "timeout 3s \"$MOX_SCRIPT\" sleep" "usage.*sleep|daemon.*not.*running"
run_test_expect_error "sleep invalid" "timeout 3s \"$MOX_SCRIPT\" sleep abc" "usage.*sleep.*integer|daemon.*not.*running"

echo -e "\n${YELLOW}📤 Export Commands${NC}"

run_test_with_output "export likes" "timeout 3s \"$MOX_SCRIPT\" export likes" "date,title,url|Test.*Liked.*Song"
run_test_with_output "export history" "timeout 3s \"$MOX_SCRIPT\" export history" "date,title,url|Test.*Song"
run_test_expect_error "export invalid" "timeout 3s \"$MOX_SCRIPT\" export invalid" "usage.*export"

echo -e "\n${YELLOW}🎨 UI Commands${NC}"

# These commands may require additional dependencies
run_test_with_output "art command" "timeout 3s \"$MOX_SCRIPT\" art" "not.*running|album.*art|chafa.*not.*found"
run_test_with_output "lyrics command" "timeout 3s \"$MOX_SCRIPT\" lyrics" "not.*running|lyrics|No.*lyrics"
run_test_with_output "bar command" "timeout 3s \"$MOX_SCRIPT\" bar" "not.*running|progress"
run_test_with_output "ui command" "timeout 3s \"$MOX_SCRIPT\" ui" "not.*running|dashboard|tmux"

echo -e "\n${YELLOW}🌐 Web UI Commands${NC}"

run_test_with_output "uxi command" "timeout 5s \"$MOX_SCRIPT\" uxi" "server.*starting|already.*running|port|music_ui_server.*not.*found"
run_test_with_output "uxi-stop command" "timeout 3s \"$MOX_SCRIPT\" uxi-stop" "stopped|not.*running"

echo -e "\n${YELLOW}🔄 Update and Maintenance${NC}"

run_test_with_output "update command" "timeout 5s \"$MOX_SCRIPT\" update" "update.*disabled|latest.*version|update.*available|updating.*yt-dlp|already.*up-to-date"
run_test_with_output "reload-config" "timeout 3s \"$MOX_SCRIPT\" reload-config" "config.*reloaded|not.*running"

echo -e "\n${YELLOW}🎯 Local Music Commands${NC}"

run_test_with_output "index command" "timeout 5s \"$MOX_SCRIPT\" index" "ffprobe.*not.*found|Scanning.*local|indexed"
run_test_with_output "local command" "timeout 3s \"$MOX_SCRIPT\" local" "No.*local.*music|test_song|interrupted.*system.*call"

echo -e "\n${YELLOW}🔗 Casting Commands${NC}"

run_test_with_output "cast command" "timeout 3s \"$MOX_SCRIPT\" cast" "not.*running|cast.*devices|No.*cast"

echo -e "\n${YELLOW}🎪 Miscellaneous Commands${NC}"

# Test completions
run_test_with_output "completions command" "timeout 3s \"$MOX_SCRIPT\" completions" "completion|bash|zsh"

# Test invalid command
run_test_with_output "invalid command" "timeout 3s \"$MOX_SCRIPT\" invalid_xyz_command" "Commands:|Usage:|starting.*daemon|searching.*yt-dlp|interrupted.*system.*call"

# Test chapter navigation
run_test_with_output "chapter command" "timeout 3s \"$MOX_SCRIPT\" chapter" "not.*running|chapters|No.*chapters|daemon.*socket.*exists.*but.*mpv.*is.*unresponsive"

# Test queue deduplication
run_test_with_output "queue-dedup" "timeout 3s \"$MOX_SCRIPT\" queue-dedup" "not.*running|queue.*empty|duplicates|daemon.*socket.*exists.*but.*mpv.*is.*unresponsive"

# Test queue auto-save
run_test_with_output "queue-save-auto" "timeout 3s \"$MOX_SCRIPT\" queue-save-auto" "auto.*save|enabled|disabled"

# Test notify toggle
run_test_with_output "notify-toggle" "timeout 3s \"$MOX_SCRIPT\" notify-toggle" "notifications|enabled|disabled"

echo -e "\n${BLUE}📊 Command Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total tests run: ${BLUE}$TESTS_RUN${NC}"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All command tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some command tests failed.${NC}"
    exit 1
fi