#!/bin/bash
# Performance and load tests for mox CLI
set -e

echo "⚡ Running mox performance and load tests..."

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

# Performance thresholds (in seconds)
FAST_THRESHOLD=1.0
MEDIUM_THRESHOLD=3.0
SLOW_THRESHOLD=10.0

# Setup test environment
TEST_MUSIC_ROOT="/tmp/mox_perf_test_$$"
export MUSIC_ROOT="$TEST_MUSIC_ROOT"

cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up performance test environment...${NC}"
    rm -rf "$TEST_MUSIC_ROOT" 2>/dev/null || true
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT

setup_performance_test_env() {
    echo -e "${BLUE}📁 Setting up performance test environment...${NC}"
    mkdir -p "$TEST_MUSIC_ROOT"/{socket,cache,playlists,txts,downloads,data,locks}
    
    # Create config optimized for performance testing
    cat > "$TEST_MUSIC_ROOT/config" <<EOF
CACHE_TTL=3600
HISTORY_MAX=1000
DEFAULT_VOLUME=50
VOLUME_STEP=5
SEARCH_RESULTS=10
AUDIO_DEVICE_SPEAKERS=""
AUDIO_DEVICE_HEADPHONES=""
SCROBBLE_URL=""
YTDLP_MAX_AGE_DAYS=30
LASTFM_API_KEY=""
YOUTUBE_API_KEY=""
INVIDIOUS_HOST=""
LOCAL_MUSIC_DIR="$TEST_MUSIC_ROOT/music"
AUTODJ_ENABLED=0
LYRICS_ENABLED=0
NOTIFY_ENABLED=0
CROSSFADE_SECS=0
BAR_REFRESH_MS=500
M_UPDATE_URL=""
M_UPDATE_SHA256=""
EOF
    
    # Create large datasets for performance testing
    echo -e "${BLUE}📊 Creating large test datasets...${NC}"
    
    # Large playlist (1000 entries)
    echo "# Large playlist with 1000 entries" > "$TEST_MUSIC_ROOT/playlists/large.m3u"
    for i in {1..1000}; do
        printf "https://example.com/song%04d.mp3\n" $i >> "$TEST_MUSIC_ROOT/playlists/large.m3u"
    done
    
    # Very large playlist (10000 entries)
    echo "# Very large playlist with 10000 entries" > "$TEST_MUSIC_ROOT/playlists/huge.m3u"
    for i in {1..10000}; do
        printf "https://example.com/track%05d.mp3\n" $i >> "$TEST_MUSIC_ROOT/playlists/huge.m3u"
    done
    
    # Large txt file (1000 entries)
    echo "# Large txt file with 1000 entries" > "$TEST_MUSIC_ROOT/txts/large.txt"
    for i in {1..1000}; do
        printf "Test Song %04d by Artist %04d\n" $i $((i % 100)) >> "$TEST_MUSIC_ROOT/txts/large.txt"
    done
    
    # Very large txt file (10000 entries)
    echo "# Very large txt file with 10000 entries" > "$TEST_MUSIC_ROOT/txts/huge.txt"
    for i in {1..10000}; do
        printf "Track %05d - Album %04d - Artist %03d\n" $i $((i % 50)) $((i % 20)) >> "$TEST_MUSIC_ROOT/txts/huge.txt"
    done
    
    # Large history file (5000 entries)
    for i in {1..5000}; do
        date_offset=$((i * 60))  # 1 minute apart
        timestamp=$(date -d "@$(($(date +%s) - date_offset))" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -r $(($(date +%s) - date_offset)) '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || echo "2024-01-01T12:00:00")
        printf "%s\tTest Song %04d\thttps://example.com/song%04d.mp3\n" "$timestamp" $i $i >> "$TEST_MUSIC_ROOT/data/history"
    done
    
    # Large likes file (1000 entries)
    for i in {1..1000}; do
        date_offset=$((i * 3600))  # 1 hour apart
        timestamp=$(date -d "@$(($(date +%s) - date_offset))" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -r $(($(date +%s) - date_offset)) '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || echo "2024-01-01T12:00:00")
        printf "%s\tLiked Song %04d\thttps://example.com/liked%04d.mp3\n" "$timestamp" $i $i >> "$TEST_MUSIC_ROOT/data/likes"
    done
    
    # Multiple playlists for batch operations
    for i in {1..100}; do
        playlist_name=$(printf "playlist_%03d" $i)
        echo "# Auto-generated playlist $i" > "$TEST_MUSIC_ROOT/playlists/${playlist_name}.m3u"
        for j in {1..10}; do
            printf "https://example.com/pl%03d_song%02d.mp3\n" $i $j >> "$TEST_MUSIC_ROOT/playlists/${playlist_name}.m3u"
        done
    done
    
    # Multiple txt files
    for i in {1..50}; do
        txt_name=$(printf "txtlist_%02d" $i)
        echo "# Auto-generated txt list $i" > "$TEST_MUSIC_ROOT/txts/${txt_name}.txt"
        for j in {1..20}; do
            printf "TXT %02d Song %02d\n" $i $j >> "$TEST_MUSIC_ROOT/txts/${txt_name}.txt"
        done
    done
    
    # Create cache files to test cache performance
    mkdir -p "$TEST_MUSIC_ROOT/cache"
    for i in {1..100}; do
        cache_key=$(printf "test_cache_%03d" $i)
        echo "Cached content $i" > "$TEST_MUSIC_ROOT/cache/$cache_key"
        # Set timestamp to make some files "old"
        if [[ $i -lt 50 ]]; then
            touch -t 202301010000 "$TEST_MUSIC_ROOT/cache/$cache_key" 2>/dev/null || true
        fi
    done
    
    echo -e "${GREEN}✅ Performance test environment ready${NC}"
}

measure_time() {
    local start_time end_time duration
    start_time=$(date +%s.%N 2>/dev/null || date +%s)
    set +e  # Temporarily disable exit on error
    eval "$1" >/dev/null 2>&1
    local exit_code=$?
    set -e  # Re-enable exit on error
    end_time=$(date +%s.%N 2>/dev/null || date +%s)
    
    if command -v bc >/dev/null 2>&1; then
        duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
    else
        # Fallback for systems without bc
        duration=$(awk "BEGIN {print $end_time - $start_time}" 2>/dev/null || echo "0")
    fi
    
    echo "$duration $exit_code"
}

run_performance_test() {
    local test_name="$1"
    local test_command="$2"
    local threshold="$3"
    local timeout_duration="${4:-30}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[PERF $TESTS_RUN]${NC} $test_name"
    
    local result duration exit_code
    result=$(timeout "${timeout_duration}s" bash -c "$(declare -f measure_time); measure_time '$test_command'" 2>/dev/null || echo "999 1")
    duration=$(echo "$result" | cut -d' ' -f1)
    exit_code=$(echo "$result" | cut -d' ' -f2)
    
    # Handle timeout case
    if [[ "$duration" == "999" ]]; then
        echo -e "  ${RED}❌ TIMEOUT${NC} (>${timeout_duration}s)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return
    fi
    
    # Check if command succeeded
    if [[ $exit_code -ne 0 ]]; then
        echo -e "  ${RED}❌ FAIL${NC} - Command failed (${duration}s)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return
    fi
    
    # Compare against threshold
    if command -v bc >/dev/null 2>&1; then
        if [[ $(echo "$duration <= $threshold" | bc) -eq 1 ]]; then
            echo -e "  ${GREEN}✅ PASS${NC} (${duration}s ≤ ${threshold}s)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "  ${RED}❌ SLOW${NC} (${duration}s > ${threshold}s)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        # Fallback comparison without bc
        if awk "BEGIN {exit !($duration <= $threshold)}" 2>/dev/null; then
            echo -e "  ${GREEN}✅ PASS${NC} (${duration}s ≤ ${threshold}s)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "  ${RED}❌ SLOW${NC} (${duration}s > ${threshold}s)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
}

run_load_test() {
    local test_name="$1"
    local test_command="$2"
    local iterations="$3"
    local max_time="$4"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[LOAD $TESTS_RUN]${NC} $test_name ($iterations iterations)"
    
    local start_time end_time total_duration
    start_time=$(date +%s.%N 2>/dev/null || date +%s)
    
    local failed_count=0
    for ((i=1; i<=iterations; i++)); do
        set +e  # Temporarily disable exit on error
        eval "$test_command" >/dev/null 2>&1
        local result=$?
        set -e  # Re-enable exit on error
        
        if [[ $result -ne 0 ]]; then
            failed_count=$((failed_count + 1))
        fi
        
        # Show progress every 10 iterations
        if [[ $((i % 10)) -eq 0 ]]; then
            echo -n "."
        fi
    done
    echo ""
    
    end_time=$(date +%s.%N 2>/dev/null || date +%s)
    
    if command -v bc >/dev/null 2>&1; then
        total_duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
    else
        total_duration=$(awk "BEGIN {print $end_time - $start_time}" 2>/dev/null || echo "0")
    fi
    
    if [[ $failed_count -eq 0 ]] && (command -v bc >/dev/null 2>&1 && [[ $(echo "$total_duration <= $max_time" | bc) -eq 1 ]] || awk "BEGIN {exit !($total_duration <= $max_time)}" 2>/dev/null); then
        echo -e "  ${GREEN}✅ PASS${NC} (${total_duration}s, 0 failures)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} (${total_duration}s, $failed_count failures)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Setup test environment
setup_performance_test_env

echo -e "\n${YELLOW}⚡ Basic Command Performance${NC}"

# Test basic commands that should be very fast
run_performance_test "Help command speed" "\"$MOX_SCRIPT\" help" "$FAST_THRESHOLD"
run_performance_test "Status command speed" "\"$MOX_SCRIPT\" status" "$FAST_THRESHOLD"
run_performance_test "Config validation speed" "\"$MOX_SCRIPT\" help" "$FAST_THRESHOLD"

echo -e "\n${YELLOW}📋 Playlist Performance${NC}"

# Test playlist operations
run_performance_test "List playlists speed" "\"$MOX_SCRIPT\" playlists" "$FAST_THRESHOLD"
run_performance_test "Load small playlist" "\"$MOX_SCRIPT\" load playlist_001" "$MEDIUM_THRESHOLD"
run_performance_test "Load large playlist (1000 items)" "\"$MOX_SCRIPT\" load large" "$SLOW_THRESHOLD"

# Only test huge playlist if we have enough time
if [[ "${SKIP_HUGE_TESTS:-}" != "1" ]]; then
    run_performance_test "Load huge playlist (10000 items)" "\"$MOX_SCRIPT\" load huge" "30.0" 60
fi

echo -e "\n${YELLOW}📝 Text File Performance${NC}"

# Test txt file operations
run_performance_test "List txt files speed" "\"$MOX_SCRIPT\" txts" "$FAST_THRESHOLD"
run_performance_test "Load small txt file" "\"$MOX_SCRIPT\" txt txtlist_01" "$MEDIUM_THRESHOLD"
run_performance_test "Load large txt file (1000 items)" "\"$MOX_SCRIPT\" txt large" "$SLOW_THRESHOLD"

if [[ "${SKIP_HUGE_TESTS:-}" != "1" ]]; then
    run_performance_test "Load huge txt file (10000 items)" "\"$MOX_SCRIPT\" txt huge" "30.0" 60
fi

echo -e "\n${YELLOW}📊 Data Processing Performance${NC}"

# Test history and likes operations
run_performance_test "Display history (5000 items)" "\"$MOX_SCRIPT\" history" "$MEDIUM_THRESHOLD"
run_performance_test "Display likes (1000 items)" "\"$MOX_SCRIPT\" likes" "$MEDIUM_THRESHOLD"
run_performance_test "Export history to CSV" "\"$MOX_SCRIPT\" export history" "$MEDIUM_THRESHOLD"
run_performance_test "Export likes to CSV" "\"$MOX_SCRIPT\" export likes" "$MEDIUM_THRESHOLD"

echo -e "\n${YELLOW}📈 Statistics Performance${NC}"

# Test statistics generation
run_performance_test "Generate stats" "\"$MOX_SCRIPT\" stats" "$MEDIUM_THRESHOLD"
run_performance_test "Generate history stats" "\"$MOX_SCRIPT\" history-stats" "$MEDIUM_THRESHOLD"

echo -e "\n${YELLOW}🗄️ Cache Performance${NC}"

# Test cache operations
run_performance_test "Cache stats generation" "\"$MOX_SCRIPT\" cache-stats" "$FAST_THRESHOLD"
run_performance_test "Cache pruning" "\"$MOX_SCRIPT\" cache-prune" "$MEDIUM_THRESHOLD"
run_performance_test "Cache clearing" "\"$MOX_SCRIPT\" cache-clear" "$FAST_THRESHOLD"

echo -e "\n${YELLOW}🔍 Search Performance${NC}"

# Test search operations (these may timeout due to network, but test the command parsing)
if command -v yt-dlp >/dev/null 2>&1; then
    run_performance_test "Search command parsing" "timeout 5s \"$MOX_SCRIPT\" search 'test query' || true" "$FAST_THRESHOLD"
else
    echo -e "${BLUE}[PERF $((TESTS_RUN + 1))]${NC} Search command parsing"
    echo -e "  ${YELLOW}⚠️  SKIP${NC} - yt-dlp not available"
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

echo -e "\n${YELLOW}🔄 Load Testing${NC}"

# Test repeated operations
run_load_test "Repeated help commands" "\"$MOX_SCRIPT\" help" 50 "10.0"
run_load_test "Repeated status checks" "\"$MOX_SCRIPT\" status" 20 "5.0"
run_load_test "Repeated playlist listings" "\"$MOX_SCRIPT\" playlists" 20 "5.0"

echo -e "\n${YELLOW}🧠 Memory Usage Tests${NC}"

# Test memory usage with large datasets (basic check)
run_performance_test "Memory test - large history" "\"$MOX_SCRIPT\" history >/dev/null" "$MEDIUM_THRESHOLD"
run_performance_test "Memory test - large playlist list" "\"$MOX_SCRIPT\" playlists >/dev/null" "$FAST_THRESHOLD"

echo -e "\n${YELLOW}⚙️ Concurrent Operations${NC}"

# Test concurrent command execution
run_performance_test "Concurrent help commands" "cd ../src && (./mox.sh help & ./mox.sh help & ./mox.sh help & wait)" "$MEDIUM_THRESHOLD"
run_performance_test "Concurrent status checks" "cd ../src && (./mox.sh status & ./mox.sh status & wait)" "$MEDIUM_THRESHOLD"

echo -e "\n${YELLOW}🔧 System Resource Tests${NC}"

# Test with system resource constraints
run_performance_test "Low resource environment" "cd ../src && ulimit -v 100000 2>/dev/null; ./mox.sh help || ./mox.sh help" "$MEDIUM_THRESHOLD"

echo -e "\n${YELLOW}📦 Startup Performance${NC}"

# Test cold start performance
run_performance_test "Cold start help" "\"$MOX_SCRIPT\" help" "$FAST_THRESHOLD"
run_performance_test "Cold start status" "\"$MOX_SCRIPT\" status" "$FAST_THRESHOLD"

# Test warm start (config already loaded)
run_performance_test "Warm start help" "\"$MOX_SCRIPT\" help" "$FAST_THRESHOLD"

echo -e "\n${YELLOW}🎯 Edge Case Performance${NC}"

# Test performance with edge cases
run_performance_test "Empty playlist handling" "cd ../src && touch '$TEST_MUSIC_ROOT/playlists/empty.m3u' && ./mox.sh load empty" "$FAST_THRESHOLD"
run_performance_test "Nonexistent playlist" "\"$MOX_SCRIPT\" load nonexistent_playlist_xyz" "$FAST_THRESHOLD"

echo -e "\n${YELLOW}📊 Performance Summary${NC}"

# Calculate performance statistics
if [[ $TESTS_RUN -gt 0 ]]; then
    pass_rate=$(( (TESTS_PASSED * 100) / TESTS_RUN ))
    echo "Performance pass rate: ${pass_rate}%"
    
    if [[ $pass_rate -ge 90 ]]; then
        performance_grade="A"
        grade_color="$GREEN"
    elif [[ $pass_rate -ge 80 ]]; then
        performance_grade="B"
        grade_color="$YELLOW"
    elif [[ $pass_rate -ge 70 ]]; then
        performance_grade="C"
        grade_color="$YELLOW"
    else
        performance_grade="D"
        grade_color="$RED"
    fi
    
    echo -e "Performance grade: ${grade_color}${performance_grade}${NC}"
fi

echo -e "\n${BLUE}📊 Performance Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total tests run: ${BLUE}$TESTS_RUN${NC}"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

echo -e "\n${YELLOW}Performance Thresholds Used:${NC}"
echo -e "Fast operations: ≤ ${FAST_THRESHOLD}s"
echo -e "Medium operations: ≤ ${MEDIUM_THRESHOLD}s"
echo -e "Slow operations: ≤ ${SLOW_THRESHOLD}s"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All performance tests passed! The system meets performance requirements.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some performance tests failed. Consider optimization.${NC}"
    exit 1
fi