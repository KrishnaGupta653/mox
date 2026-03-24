# Mox CLI Test Suite

This directory contains a comprehensive test suite for the mox CLI music player. The test suite is designed to ensure reliability, security, and performance across all functionality.

## 🧪 Test Suites Overview

### 1. Basic Tests (`test.sh`)
- **Purpose**: Quick smoke tests for essential functionality
- **Speed**: Fast (~10 seconds)
- **Coverage**: File existence, syntax validation, basic commands

### 2. Comprehensive Tests (`test-comprehensive.sh`)
- **Purpose**: Thorough validation of all components
- **Speed**: Medium (~60 seconds)
- **Coverage**: File structure, syntax, configuration, dependencies, documentation

### 3. Integration Tests (`test-integration.sh`)
- **Purpose**: End-to-end functionality testing
- **Speed**: Medium (~90 seconds)
- **Coverage**: Core workflows, environment setup, command interactions

### 4. Command Tests (`test-commands.sh`)
- **Purpose**: Individual command functionality validation
- **Speed**: Medium (~120 seconds)
- **Coverage**: Every CLI command, argument validation, error handling

### 5. Edge Case Tests (`test-edge-cases.sh`)
- **Purpose**: Boundary conditions and error scenarios
- **Speed**: Medium (~90 seconds)
- **Coverage**: Invalid inputs, malformed files, resource constraints

### 6. Performance Tests (`test-performance.sh`)
- **Purpose**: Performance benchmarking and load testing
- **Speed**: Slow (~300 seconds)
- **Coverage**: Response times, memory usage, concurrent operations

### 7. Security Tests (`test-security.sh`)
- **Purpose**: Security vulnerability assessment
- **Speed**: Medium (~150 seconds)
- **Coverage**: Injection attacks, path traversal, privilege escalation

### 8. API Tests (`test-api.py`)
- **Purpose**: Python server API endpoint testing
- **Speed**: Medium (~60 seconds)
- **Coverage**: HTTP endpoints, authentication, error handling

## 🚀 Quick Start

### Run All Tests
```bash
cd tests
./run-all-tests.sh
```

### Run Specific Test Suites
```bash
# Basic validation only
./run-all-tests.sh basic

# Security and performance
./run-all-tests.sh security performance

# Quick mode (skip slow tests)
./run-all-tests.sh --quick

# Verbose output
./run-all-tests.sh --verbose
```

### Run Individual Test Suites
```bash
# Run basic smoke tests
./test.sh

# Run comprehensive tests
./test-comprehensive.sh

# Run security tests
./test-security.sh

# Run API tests
python3 test-api.py
```

## 📊 Test Results and Reporting

### Automatic Reporting
The master test runner generates detailed reports:
- **Console Output**: Real-time test progress
- **Report File**: Comprehensive results saved to `test-report-YYYYMMDD-HHMMSS.txt`

### Success Criteria
- **Green (✅)**: All tests passed
- **Yellow (⚠️)**: Some tests failed but system is functional
- **Red (❌)**: Critical failures detected

### Metrics Tracked
- Test suite success rate
- Individual test success rate
- Performance benchmarks
- Security assessment score

## ⚙️ Configuration Options

### Environment Variables
```bash
export VERBOSE=1          # Enable verbose output
export QUICK_MODE=1       # Skip slow tests
export SKIP_SLOW=1        # Skip slow test suites
export PARALLEL=1         # Enable parallel execution
export SKIP_HUGE_TESTS=1  # Skip huge dataset tests
```

### Command Line Options
```bash
./run-all-tests.sh [OPTIONS] [SUITES...]

OPTIONS:
  -v, --verbose       Verbose output
  -q, --quick         Quick mode
  -s, --skip-slow     Skip slow tests
  -p, --parallel      Parallel execution
  -r, --report FILE   Custom report file
  -h, --help          Show help
```

## 🔧 Dependencies

### Required
- **bash**: Shell script execution
- **python3**: API tests and utilities
- **timeout**: Command timeouts
- **grep/awk/sed**: Text processing

### Optional (Recommended)
- **jq**: JSON processing
- **bc**: Mathematical calculations
- **curl**: Network requests
- **socat**: Socket communication
- **yt-dlp**: YouTube functionality
- **mpv**: Media player backend

### Installation
```bash
# macOS
brew install jq bc curl socat yt-dlp mpv

# Ubuntu/Debian
sudo apt install jq bc curl socat yt-dlp mpv

# Fedora/RHEL
sudo dnf install jq bc curl socat yt-dlp mpv
```

## 🎯 Test Categories

### Functional Testing
- ✅ Command execution
- ✅ Argument validation
- ✅ Error handling
- ✅ Configuration loading
- ✅ File operations

### Integration Testing
- ✅ End-to-end workflows
- ✅ Component interactions
- ✅ Environment setup
- ✅ Dependency handling

### Performance Testing
- ✅ Response time benchmarks
- ✅ Memory usage validation
- ✅ Load testing
- ✅ Concurrent operations
- ✅ Large dataset handling

### Security Testing
- ✅ Command injection prevention
- ✅ Path traversal protection
- ✅ Input sanitization
- ✅ File access controls
- ✅ Privilege escalation prevention
- ✅ Network security
- ✅ Data validation

### Edge Case Testing
- ✅ Boundary values
- ✅ Invalid inputs
- ✅ Resource exhaustion
- ✅ Malformed data
- ✅ Concurrent access

## 🚨 Troubleshooting

### Common Issues

#### Permission Errors
```bash
chmod +x tests/*.sh
chmod +x tests/*.py
```

#### Missing Dependencies
```bash
# Check what's missing
./run-all-tests.sh basic

# Install missing tools
brew install missing-tool  # macOS
sudo apt install missing-tool  # Ubuntu
```

#### Test Timeouts
```bash
# Increase timeout for slow systems
export TIMEOUT_MULTIPLIER=2
./run-all-tests.sh
```

#### Network Issues
```bash
# Skip network-dependent tests
export SKIP_NETWORK_TESTS=1
./run-all-tests.sh
```

### Debug Mode
```bash
# Run with maximum verbosity
VERBOSE=1 bash -x ./test-comprehensive.sh
```

## 📈 Continuous Integration

### GitHub Actions Example
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: |
          sudo apt update
          sudo apt install -y jq bc curl socat python3
      - name: Run tests
        run: |
          cd tests
          ./run-all-tests.sh --quick
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
cd tests && ./run-all-tests.sh basic comprehensive
```

## 📋 Test Maintenance

### Adding New Tests
1. Choose appropriate test suite
2. Follow existing patterns
3. Add to `run-all-tests.sh` if needed
4. Update documentation

### Test Suite Guidelines
- **Fast tests**: < 1 second per test
- **Medium tests**: < 5 seconds per test
- **Slow tests**: < 30 seconds per test
- **Descriptive names**: Clear test purposes
- **Proper cleanup**: No test artifacts left behind

### Best Practices
- ✅ Test one thing at a time
- ✅ Use descriptive test names
- ✅ Clean up after tests
- ✅ Handle missing dependencies gracefully
- ✅ Provide meaningful error messages
- ✅ Use consistent output formatting

## 🔄 Release Testing

### Pre-release Checklist
```bash
# Full test suite
./run-all-tests.sh

# Performance regression check
./run-all-tests.sh performance

# Security audit
./run-all-tests.sh security

# Cross-platform testing
./run-all-tests.sh --quick  # On each target platform
```

### Quality Gates
- **All basic tests**: Must pass
- **95%+ comprehensive tests**: Must pass
- **Security tests**: Must pass
- **Performance**: No significant regression

## 📚 Resources

- [Testing Best Practices](https://github.com/KrishnaGupta653/mox/docs/TESTING.md)
- [Contributing Guidelines](https://github.com/KrishnaGupta653/mox/CONTRIBUTING.md)
- [Security Policy](https://github.com/KrishnaGupta653/mox/SECURITY.md)
- [Performance Benchmarks](https://github.com/KrishnaGupta653/mox/docs/PERFORMANCE.md)

---

**Note**: This test suite is designed to be comprehensive yet efficient. Run the full suite before major releases, and use quick mode for regular development testing.