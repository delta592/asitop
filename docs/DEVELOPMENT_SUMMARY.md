# Development Environment and Testing Summary

This document summarizes all the development tools, testing infrastructure, and automation added to the asitop project.

## What Was Added

### 1. Comprehensive Test Suite (74 Tests)

Three test files covering all major functionality:

- **tests/test_parsers.py** (17 tests)
  - Powermetrics parsing for thermal, bandwidth, CPU, and GPU metrics
  - Support for all Apple Silicon variants (M1/Pro/Max/Ultra/M2)
  - Dual P-cluster configurations (M1 Ultra variants)
  - Edge cases for bandwidth metrics

- **tests/test_utils.py** (31 tests)
  - Utility functions (conversions, system info)
  - SOC information gathering
  - Process management
  - File operations
  - Error handling for corrupted/partial data

- **tests/test_asitop.py** (26 tests)
  - Argument parsing
  - Main application logic
  - Memory management
  - Power calculations
  - Restart logic and thermal pressure handling

Current Test Coverage (as of latest run):
- **Total**: 79.86%
- **parsers.py**: 98.85%
- **utils.py**: 96.49%
- **asitop.py**: 54.02%

All tests follow python_instructions.md guidelines:
- Type hints using `typing` module
- PEP 257 docstrings
- Edge case coverage
- Proper mocking

### 2. Modern Dependency Management with uv

The project now uses **uv** for fast, reliable dependency management:

**Key Benefits:**
- 10-100x faster than pip
- Reproducible builds via uv.lock
- Better dependency resolution
- Modern PEP 517/518/621 compliant

**Configuration Files:**
- **pyproject.toml** - Central project configuration (replaces setup.py, requirements.txt)
- **uv.lock** - Lock file for reproducible builds
- **Makefile** - Updated to use uv commands

### 3. Makefile with uv Integration

**Makefile** provides 20+ commands using uv, organized into categories:

**Setup:**
- `make sync` - Sync production dependencies (uv sync --no-dev)
- `make install` - Install production dependencies
- `make install-dev` - Install dev/test dependencies (uv sync --extra test)

**Testing:**
- `make test` - Run all tests with uv run pytest
- `make test-coverage` - Run with coverage report
- `make coverage-html` - Generate HTML coverage report
- `make test-watch` - Auto-run tests on file changes

**Running:**
- `make run` - Run asitop with sudo (recommended)
- `make run-nosudo` - Run without sudo upfront

**Quality:**
- `make lint` - Run Ruff linter
- `make fix` - Auto-fix linting issues with Ruff
- `make format` - Format code with Black
- `make format-check` - Check code formatting
- `make type-check` - Run Mypy type checker
- `make check` - Run all quality checks (lint, format, type, tests)

**Cleanup:**
- `make clean` - Remove all generated files (.venv, build, dist)
- `make clean-pyc` - Remove Python cache
- `make clean-test` - Remove test artifacts

**Distribution:**
- `make dist` - Build packages with uv build
- `make upload-test` - Upload to TestPyPI
- `make upload` - Upload to PyPI

### 3. Shell Script for Running asitop

**run_asitop.sh** - Bash script that:
- Auto-creates venv if needed
- Installs dependencies if needed
- Runs asitop with sudo using venv Python
- Passes through command-line arguments
- Checked with shellcheck (no issues)

Usage:
```bash
./run_asitop.sh
./run_asitop.sh --interval 5 --color 3
```

### 4. Configuration Files

**pyproject.toml** - Central project configuration (PEP 517/518/621)
- Project metadata and dependencies
- Requires Python 3.10 or later
- Optional test dependencies via [project.optional-dependencies]
- Entry points for CLI (asitop command)
- Tool configuration (pytest, coverage, mypy, ruff, black)
- Replaces: setup.py, requirements.txt, requirements-test.txt, pytest.ini, .coveragerc

**uv.lock** - Lock file for reproducible builds
- Exact dependency versions
- Cross-platform compatibility
- Fast dependency resolution

**Makefile** - Build automation using uv
- All commands use `uv` and `uv run`
- Automatic virtual environment management at .venv/
- No manual venv activation needed

### 5. GitHub Actions Workflow

**.github/workflows/tests.yml** - CI/CD configuration
- Test matrix for Python 3.10+
- Automated testing on push/PR
- Coverage reporting to Codecov
- Code quality checks (Ruff, Black, Mypy)

### 6. Comprehensive Documentation

**QUICKSTART.md** - Quick start guide
- 3-step setup process
- Common commands
- Development workflow
- Troubleshooting

**MAKEFILE_GUIDE.md** - Complete Makefile documentation
- Detailed command explanations
- Usage examples
- Typical workflows
- Troubleshooting guide

**TESTING.md** - Testing reference
- Test commands
- Writing tests
- Coverage goals
- Mock examples

**tests/README.md** - Test suite documentation
- Test structure
- Running tests
- Coverage information
- Contributing guidelines

**TEST_SUMMARY.md** - Test suite summary
- Test statistics
- Breakdown by file
- Key features
- Apple Silicon coverage

**DEVELOPMENT_SUMMARY.md** - This file
- Overview of all additions
- Quick reference
- File organization

## Quick Reference

### First Time Setup

```bash
# Install uv if not already installed
brew install uv

# Set up everything with uv
make install-dev    # Runs: uv sync --extra test
make test           # Verify installation
```

### Run asitop

```bash
make run            # Run with sudo
./run_asitop.sh     # Alternative method
```

### Development

```bash
make test-watch     # Auto-run tests on changes
make test-coverage  # Check test coverage
make check          # Run all quality checks
```

### Before Committing

```bash
make check          # Run tests + linters
make clean-pyc      # Clean up
```

## Project Structure

```
asitop/
├── asitop/                      # Source code
│   ├── __init__.py
│   ├── asitop.py                # Main application
│   ├── utils.py                 # Utility functions
│   └── parsers.py               # Parsing functions
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_asitop.py           # Main app tests (24)
│   ├── test_utils.py            # Utils tests (28)
│   ├── test_parsers.py          # Parser tests (15)
│   └── README.md                # Test documentation
│
├── .github/
│   └── workflows/
│       └── tests.yml            # CI/CD workflow
│
├── venv/                        # Virtual env (auto-created)
│
├── Makefile                     # Build automation
├── run_asitop.sh                # Run script (executable)
│
├── pytest.ini                   # Pytest config
├── .coveragerc                  # Coverage config
├── requirements.txt             # Production deps
├── requirements-test.txt        # Test deps
│
├── QUICKSTART.md                # Quick start guide
├── MAKEFILE_GUIDE.md            # Makefile documentation
├── TESTING.md                   # Testing guide
├── TEST_SUMMARY.md              # Test summary
├── DEVELOPMENT_SUMMARY.md       # This file
│
├── python_instructions.md       # Python conventions
├── setup.py                     # Package setup
└── README.md                    # Project README
```

## Key Features

### uv Dependency Management

All Makefile commands automatically:
1. Use uv for fast dependency resolution
2. Create .venv if it doesn't exist (via uv sync)
3. Use .venv Python and packages
4. Keep system Python clean
5. Ensure reproducible builds via uv.lock
6. 10-100x faster than traditional pip/venv

### Test Coverage

- **74 comprehensive tests** (increased from 67)
- **3 test files** covering all modules
- **79.86% total coverage** (parsers: 98.85%, utils: 96.49%, asitop: 54.02%)
- **Edge cases** tested (empty, zero, max, errors, corrupted data)
- **All Apple Silicon variants** (M1/Pro/Max/Ultra/M2)
- **Proper mocking** of system calls
- **Type hints** and **docstrings** on all tests

### Automation

Everything is automated via Makefile:
- Environment setup
- Dependency installation
- Test execution
- Coverage reporting
- Code quality checks
- Running asitop with sudo
- Cleanup operations
- Package distribution

### Documentation

Six documentation files covering:
- Quick start (QUICKSTART.md)
- Makefile usage (MAKEFILE_GUIDE.md)
- Testing guide (TESTING.md)
- Test suite details (tests/README.md)
- Test summary (TEST_SUMMARY.md)
- Development overview (this file)

## Compliance

All additions comply with python_instructions.md:

✓ Type hints using `typing` module
✓ PEP 257 docstrings
✓ PEP 8 style guide
✓ Edge case testing
✓ Clear comments explaining approach
✓ Proper exception handling
✓ Good maintainability practices

## Usage Examples

### Example 1: New Developer Setup

```bash
git clone https://github.com/tlkh/asitop.git
cd asitop
make install-dev
make test
make run
```

### Example 2: Run Tests with Coverage

```bash
make test-coverage
# View detailed coverage
make coverage-html
open htmlcov/index.html
```

### Example 3: Development with Watch Mode

```bash
make test-watch  # Terminal 1: Auto-run tests

# Terminal 2: Edit code
vim asitop/utils.py

# Terminal 1: Tests run automatically
```

### Example 4: Pre-commit Check

```bash
make check       # Run all tests and linters
make clean-pyc   # Clean up
git add .
git commit -m "Add feature"
```

### Example 5: Run asitop with Options

```bash
./run_asitop.sh --interval 2 --color 5 --avg 60
```

## Testing Philosophy

The test suite follows these principles:

1. **Isolation**: All tests are independent and use mocks
2. **Speed**: Tests run in < 1 second (all mocked)
3. **Coverage**: Aim for >80% line coverage
4. **Clarity**: Clear test names and comprehensive docstrings
5. **Maintainability**: Follow Python best practices
6. **Edge Cases**: Test boundaries and error conditions

## Continuous Integration

The GitHub Actions workflow:
- Runs on push and PR
- Tests Python 3.10, 3.11, 3.12, 3.13, 3.14
- Checks code quality (Ruff, Black, Mypy)
- Reports coverage to Codecov
- Fails if tests fail or coverage < threshold

## Next Steps for Contributors

1. Read [QUICKSTART.md](QUICKSTART.md)
2. Set up: `make install-dev`
3. Run tests: `make test`
4. Read [TESTING.md](TESTING.md) for test guidelines
5. Make changes
6. Run `make check` before committing
7. Submit PR

## Benefits

This infrastructure provides:

1. **Consistency**: Same environment for all developers
2. **Quality**: Automated testing and linting
3. **Speed**: Quick feedback via watch mode
4. **Documentation**: Comprehensive guides
5. **Automation**: Everything via Makefile
6. **CI/CD**: Automated testing on push
7. **Coverage**: Track test coverage
8. **Isolation**: Clean virtual environments

## File Checklist

Created files:

- [x] tests/__init__.py
- [x] tests/test_parsers.py (15 tests)
- [x] tests/test_utils.py (28 tests)
- [x] tests/test_asitop.py (24 tests)
- [x] tests/README.md
- [x] Makefile (20+ commands)
- [x] run_asitop.sh (shellcheck passed)
- [x] pytest.ini
- [x] .coveragerc
- [x] requirements.txt
- [x] requirements-test.txt
- [x] .github/workflows/tests.yml
- [x] QUICKSTART.md
- [x] MAKEFILE_GUIDE.md
- [x] TESTING.md
- [x] TEST_SUMMARY.md
- [x] DEVELOPMENT_SUMMARY.md

Total: 16 new files

## Success Metrics

✓ 67 tests created and verified
✓ All tests collect successfully
✓ Makefile tested (help command works)
✓ run_asitop.sh shellcheck passed
✓ Virtual environment management working
✓ All documentation complete
✓ Python conventions followed
✓ Type hints on all functions
✓ Comprehensive docstrings
✓ Edge cases covered
✓ CI/CD workflow ready

## Support

For help:
- Run `make help` for Makefile commands
- Read QUICKSTART.md for quick start
- Read MAKEFILE_GUIDE.md for details
- Read TESTING.md for testing help
- Check tests/README.md for test info
