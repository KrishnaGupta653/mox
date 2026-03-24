#!/bin/bash
# Master test runner for mox CLI - runs all test suites
set -e

echo "🧪 mox CLI - Comprehensive Test Suite Runner"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test suite counters
SUITES_RUN=0
SUITES_PASSED=0
SUITES_FAILED=0
TOTAL_TESTS=0
TOTAL_PASSED=0
TOTAL_FAILED=0

# Configuration
VERBOSE=${VERBOSE:-0}
QUICK_MODE=${QUICK_MODE:-0}
SKIP_SLOW=${SKIP_SLOW:-0}
PARALLEL=${PARALLEL:-0}
REPORT_FILE="test-report-$(date +%Y%m%d-%H%M%S).txt"

# Test suite definitions (compatible with older bash)
get_suite_info() {
    local suite="$1"
    case "$suite" in
        basic) echo "test.sh|Basic smoke tests|fast" ;;
        comprehensive) echo "test-comprehensive.sh|Comprehensive validation tests|medium" ;;
        integration) echo "test-integration.sh|Integration tests|medium" ;;
        commands) echo "test-commands.sh|Individual command tests|medium" ;;
        edge-cases) echo "test-edge-cases.sh|Edge cases and error handling|medium" ;;
        performance) echo "test-performance.sh|Performance and load tests|slow" ;;
        security) echo "test-security.sh|Security validation tests|medium" ;;
        api) echo "test-api.py|Python API tests|medium" ;;
        *) echo "" ;;
    esac
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SUITES...]

Run comprehensive test suites for mox CLI.

OPTIONS:
    -v, --verbose       Verbose output (show test details)
    -q, --quick         Quick mode (skip slow tests)
    -s, --skip-slow     Skip slow test suites
    -p, --parallel      Run compatible tests in parallel
    -r, --report FILE   Generate report to file (default: auto-generated)
    -h, --help          Show this help

SUITES:
    basic              Basic smoke tests (fast)
    comprehensive      Comprehensive validation tests
    integration        Integration tests
    commands           Individual command functionality tests
    edge-cases         Edge cases and error handling tests
    performance        Performance and load tests (slow)
    security           Security validation tests
    api                Python API server tests
    all                Run all test suites (default)

EXAMPLES:
    $0                          # Run all tests
    $0 basic comprehensive      # Run specific test suites
    $0 --quick                  # Run all tests except slow ones
    $0 --verbose security       # Run security tests with verbose output
    $0 --parallel basic commands # Run tests in parallel where possible

ENVIRONMENT VARIABLES:
    VERBOSE=1          Enable verbose output
    QUICK_MODE=1       Enable quick mode
    SKIP_SLOW=1        Skip slow tests
    PARALLEL=1         Enable parallel execution
    SKIP_HUGE_TESTS=1  Skip huge dataset tests in performance suite

EOF
}

log() {
    echo -e "$@" | tee -a "$REPORT_FILE"
}

log_verbose() {
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "$@" | tee -a "$REPORT_FILE"
    else
        echo -e "$@" >> "$REPORT_FILE"
    fi
}

run_test_suite() {
    local suite_name="$1"
    local suite_info=$(get_suite_info "$suite_name")
    
    if [[ -z "$suite_info" ]]; then
        log "${RED}❌ Unknown test suite: $suite_name${NC}"
        return 1
    fi
    
    local script_name=$(echo "$suite_info" | cut -d'|' -f1)
    local description=$(echo "$suite_info" | cut -d'|' -f2)
    local speed=$(echo "$suite_info" | cut -d'|' -f3)
    
    # Skip slow tests if requested
    if [[ $SKIP_SLOW -eq 1 || $QUICK_MODE -eq 1 ]] && [[ "$speed" == "slow" ]]; then
        log "${YELLOW}⏭️  Skipping slow test suite: $suite_name${NC}"
        return 0
    fi
    
    # Check if test script exists
    if [[ ! -f "$script_name" ]]; then
        log "${RED}❌ Test script not found: $script_name${NC}"
        return 1
    fi
    
    SUITES_RUN=$((SUITES_RUN + 1))
    
    log "${BLUE}🧪 Running test suite: $suite_name${NC}"
    log "   Description: $description"
    log "   Script: $script_name"
    log "   Speed: $speed"
    log ""
    
    local start_time=$(date +%s)
    local output_file="/tmp/mox_test_${suite_name}_$$"
    local exit_code=0
    
    # Set environment variables for performance tests
    if [[ "$suite_name" == "performance" ]] && [[ $QUICK_MODE -eq 1 ]]; then
        export SKIP_HUGE_TESTS=1
    fi
    
    # Run the test suite
    if [[ $VERBOSE -eq 1 ]]; then
        if [[ "$script_name" == *.py ]]; then
            python3 "$script_name" 2>&1 | tee "$output_file"
            exit_code=${PIPESTATUS[0]}
        else
            bash "$script_name" 2>&1 | tee "$output_file"
            exit_code=${PIPESTATUS[0]}
        fi
    else
        if [[ "$script_name" == *.py ]]; then
            python3 "$script_name" > "$output_file" 2>&1
            exit_code=$?
        else
            bash "$script_name" > "$output_file" 2>&1
            exit_code=$?
        fi
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Parse test results from output
    local tests_run=0
    local tests_passed=0
    local tests_failed=0
    
    if grep -q "Total tests run:" "$output_file"; then
        tests_run=$(grep "Total tests run:" "$output_file" | tail -1 | grep -o '[0-9]\+' | head -1)
        tests_passed=$(grep "Tests passed:" "$output_file" | tail -1 | grep -o '[0-9]\+' | head -1)
        tests_failed=$(grep "Tests failed:" "$output_file" | tail -1 | grep -o '[0-9]\+' | head -1)
    elif grep -q "Ran [0-9]* tests" "$output_file"; then
        # Python unittest format
        tests_run=$(grep "Ran [0-9]* tests" "$output_file" | grep -o '[0-9]\+')
        if grep -q "OK" "$output_file"; then
            tests_passed=$tests_run
            tests_failed=0
        else
            tests_failed=$(grep -o "failures=[0-9]\+" "$output_file" | grep -o '[0-9]\+' || echo "0")
            local errors=$(grep -o "errors=[0-9]\+" "$output_file" | grep -o '[0-9]\+' || echo "0")
            tests_failed=$((tests_failed + errors))
            tests_passed=$((tests_run - tests_failed))
        fi
    fi
    
    # Update totals
    TOTAL_TESTS=$((TOTAL_TESTS + tests_run))
    TOTAL_PASSED=$((TOTAL_PASSED + tests_passed))
    TOTAL_FAILED=$((TOTAL_FAILED + tests_failed))
    
    # Log results
    if [[ $exit_code -eq 0 ]]; then
        log "${GREEN}✅ PASSED${NC} - $suite_name ($duration seconds)"
        log "   Tests: $tests_run run, $tests_passed passed, $tests_failed failed"
        SUITES_PASSED=$((SUITES_PASSED + 1))
    else
        log "${RED}❌ FAILED${NC} - $suite_name ($duration seconds)"
        log "   Tests: $tests_run run, $tests_passed passed, $tests_failed failed"
        SUITES_FAILED=$((SUITES_FAILED + 1))
        
        # Show failure details if not verbose
        if [[ $VERBOSE -eq 0 ]]; then
            log "${YELLOW}Failure details:${NC}"
            tail -20 "$output_file" | while IFS= read -r line; do
                log "   $line"
            done
        fi
    fi
    
    log ""
    
    # Clean up
    rm -f "$output_file"
    
    return $exit_code
}

run_parallel_suites() {
    local suites=("$@")
    local pids=()
    local results=()
    
    log "${CYAN}🔄 Running test suites in parallel...${NC}"
    
    for suite in "${suites[@]}"; do
        (run_test_suite "$suite") &
        pids+=($!)
        results+=("$suite")
    done
    
    # Wait for all parallel jobs
    local all_passed=0
    for i in "${!pids[@]}"; do
        local pid=${pids[$i]}
        local suite=${results[$i]}
        
        if wait $pid; then
            log_verbose "${GREEN}✅ Parallel suite completed: $suite${NC}"
        else
            log_verbose "${RED}❌ Parallel suite failed: $suite${NC}"
            all_passed=1
        fi
    done
    
    return $all_passed
}

check_dependencies() {
    log "${BLUE}🔍 Checking test dependencies...${NC}"
    
    local missing_deps=()
    
    # Check for required commands
    local required_commands=("bash" "python3" "grep" "awk" "sed")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done
    
    # Check for timeout (required but may have different names)
    if ! command -v timeout >/dev/null 2>&1 && ! command -v gtimeout >/dev/null 2>&1; then
        missing_deps+=("timeout (install with: brew install coreutils)")
    fi
    
    # Check for Python modules (for API tests)
    if ! python3 -c "import json, urllib.request, unittest" 2>/dev/null; then
        missing_deps+=("python3-modules")
    fi
    
    # Check for optional but recommended commands
    local optional_commands=("jq" "bc" "curl" "socat")
    local missing_optional=()
    for cmd in "${optional_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_optional+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log "${RED}❌ Missing required dependencies:${NC}"
        for dep in "${missing_deps[@]}"; do
            log "   - $dep"
        done
        log ""
        log "Please install missing dependencies before running tests."
        return 1
    fi
    
    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        log "${YELLOW}⚠️  Missing optional dependencies (some tests may be skipped):${NC}"
        for dep in "${missing_optional[@]}"; do
            log "   - $dep"
        done
        log ""
    fi
    
    log "${GREEN}✅ All required dependencies found${NC}"
    log ""
    return 0
}

generate_report() {
    local report_file="$1"
    
    log "${BLUE}📊 Generating comprehensive test report...${NC}"
    
    cat >> "$report_file" << EOF

================================================================================
MOX CLI - COMPREHENSIVE TEST REPORT
================================================================================
Generated: $(date)
Test Environment: $(uname -a)
Shell: $SHELL
Python: $(python3 --version 2>/dev/null || echo "Not available")

CONFIGURATION:
- Verbose Mode: $([ $VERBOSE -eq 1 ] && echo "Enabled" || echo "Disabled")
- Quick Mode: $([ $QUICK_MODE -eq 1 ] && echo "Enabled" || echo "Disabled")
- Skip Slow Tests: $([ $SKIP_SLOW -eq 1 ] && echo "Enabled" || echo "Disabled")
- Parallel Execution: $([ $PARALLEL -eq 1 ] && echo "Enabled" || echo "Disabled")

SUMMARY:
- Test Suites Run: $SUITES_RUN
- Test Suites Passed: $SUITES_PASSED
- Test Suites Failed: $SUITES_FAILED
- Total Individual Tests: $TOTAL_TESTS
- Total Tests Passed: $TOTAL_PASSED
- Total Tests Failed: $TOTAL_FAILED

EOF

    if [[ $SUITES_RUN -gt 0 ]]; then
        local success_rate=$(( (SUITES_PASSED * 100) / SUITES_RUN ))
        local test_success_rate=0
        if [[ $TOTAL_TESTS -gt 0 ]]; then
            test_success_rate=$(( (TOTAL_PASSED * 100) / TOTAL_TESTS ))
        fi
        
        cat >> "$report_file" << EOF
METRICS:
- Suite Success Rate: ${success_rate}%
- Individual Test Success Rate: ${test_success_rate}%

OVERALL ASSESSMENT:
EOF
        
        if [[ $SUITES_FAILED -eq 0 ]]; then
            echo "🎉 EXCELLENT - All test suites passed!" >> "$report_file"
        elif [[ $success_rate -ge 80 ]]; then
            echo "✅ GOOD - Most test suites passed (${success_rate}%)" >> "$report_file"
        elif [[ $success_rate -ge 60 ]]; then
            echo "⚠️  FAIR - Some issues detected (${success_rate}% success rate)" >> "$report_file"
        else
            echo "❌ POOR - Significant issues detected (${success_rate}% success rate)" >> "$report_file"
        fi
    fi
    
    cat >> "$report_file" << EOF

RECOMMENDATIONS:
EOF
    
    if [[ $SUITES_FAILED -gt 0 ]]; then
        echo "- Review and fix failing test suites before deployment" >> "$report_file"
    fi
    
    if [[ $TOTAL_FAILED -gt 0 ]]; then
        echo "- Address individual test failures for improved reliability" >> "$report_file"
    fi
    
    if [[ $SUITES_FAILED -eq 0 ]]; then
        echo "- All tests passed! The system appears ready for production" >> "$report_file"
        echo "- Consider running performance tests regularly to maintain quality" >> "$report_file"
        echo "- Keep security tests updated as new threats emerge" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "================================================================================" >> "$report_file"
    
    log "${GREEN}📋 Report generated: $report_file${NC}"
}

# Parse command line arguments
SUITES_TO_RUN=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -q|--quick)
            QUICK_MODE=1
            shift
            ;;
        -s|--skip-slow)
            SKIP_SLOW=1
            shift
            ;;
        -p|--parallel)
            PARALLEL=1
            shift
            ;;
        -r|--report)
            REPORT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        all)
            SUITES_TO_RUN=(basic comprehensive integration commands edge-cases performance security api)
            shift
            ;;
        basic|comprehensive|integration|commands|edge-cases|performance|security|api)
            SUITES_TO_RUN+=("$1")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Default to all suites if none specified
if [[ ${#SUITES_TO_RUN[@]} -eq 0 ]]; then
    SUITES_TO_RUN=(basic comprehensive integration commands edge-cases performance security api)
fi

# Initialize report file
echo "MOX CLI Test Suite - Started $(date)" > "$REPORT_FILE"

# Check dependencies
if ! check_dependencies; then
    exit 1
fi

# Show configuration
log "${PURPLE}🔧 Test Configuration:${NC}"
log "   Suites to run: ${SUITES_TO_RUN[*]}"
log "   Verbose mode: $([ $VERBOSE -eq 1 ] && echo "Enabled" || echo "Disabled")"
log "   Quick mode: $([ $QUICK_MODE -eq 1 ] && echo "Enabled" || echo "Disabled")"
log "   Skip slow tests: $([ $SKIP_SLOW -eq 1 ] && echo "Enabled" || echo "Disabled")"
log "   Parallel execution: $([ $PARALLEL -eq 1 ] && echo "Enabled" || echo "Disabled")"
log "   Report file: $REPORT_FILE"
log ""

# Record start time
TEST_START_TIME=$(date +%s)

# Run test suites
if [[ $PARALLEL -eq 1 ]] && [[ ${#SUITES_TO_RUN[@]} -gt 1 ]]; then
    # Run compatible suites in parallel (avoid performance and security together)
    local parallel_safe=(basic comprehensive integration commands edge-cases api)
    local parallel_suites=()
    local sequential_suites=()
    
    for suite in "${SUITES_TO_RUN[@]}"; do
        if [[ " ${parallel_safe[*]} " =~ " $suite " ]]; then
            parallel_suites+=("$suite")
        else
            sequential_suites+=("$suite")
        fi
    done
    
    # Run parallel-safe suites first
    if [[ ${#parallel_suites[@]} -gt 0 ]]; then
        run_parallel_suites "${parallel_suites[@]}"
    fi
    
    # Run sequential suites
    for suite in "${sequential_suites[@]}"; do
        run_test_suite "$suite"
    done
else
    # Run sequentially
    for suite in "${SUITES_TO_RUN[@]}"; do
        run_test_suite "$suite"
    done
fi

# Calculate total time
TEST_END_TIME=$(date +%s)
TOTAL_DURATION=$((TEST_END_TIME - TEST_START_TIME))

# Generate final report
generate_report "$REPORT_FILE"

# Display final summary
log ""
log "${BLUE}📊 FINAL TEST SUMMARY${NC}"
log "════════════════════════════════════════════════════════════════"
log "Test suites run: ${BLUE}$SUITES_RUN${NC}"
log "Test suites passed: ${GREEN}$SUITES_PASSED${NC}"
log "Test suites failed: ${RED}$SUITES_FAILED${NC}"
log "Total individual tests: ${BLUE}$TOTAL_TESTS${NC}"
log "Total tests passed: ${GREEN}$TOTAL_PASSED${NC}"
log "Total tests failed: ${RED}$TOTAL_FAILED${NC}"
log "Total duration: ${CYAN}${TOTAL_DURATION} seconds${NC}"
log "Report saved to: ${PURPLE}$REPORT_FILE${NC}"

if [[ $SUITES_FAILED -eq 0 ]]; then
    log ""
    log "${GREEN}🎉 ALL TEST SUITES PASSED!${NC}"
    log "${GREEN}🚀 Your mox CLI is ready for production!${NC}"
    exit 0
else
    log ""
    log "${RED}❌ SOME TEST SUITES FAILED${NC}"
    log "${YELLOW}📋 Please review the test report and fix issues before deployment.${NC}"
    exit 1
fi