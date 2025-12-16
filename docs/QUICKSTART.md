# Quick Start Guide for asitop Development

Get up and running with asitop development in 3 simple steps!

## Prerequisites

- macOS with Apple Silicon (M1, M2, M3, M4 and their Pro/Max/Ultra variants)
- **Python 3.12 or higher** (required - modernized for 2025)
- uv (fast Python package manager)
- make (comes with Xcode Command Line Tools)

Install uv:
```bash
brew install uv
# or
pip install uv
```

## Quick Start

### 1. Set Up Development Environment

```bash
# Install development dependencies with uv
make install-dev
```

This runs `uv sync --extra test`, which:
- Creates a virtual environment at `./.venv/`
- Installs all production dependencies (dashing, psutil)
- Installs all test dependencies (pytest, coverage, Ruff, Black, Mypy)
- Uses `uv.lock` for reproducible builds
- Is 10-100x faster than traditional pip

### 2. Run Tests

```bash
# Run all 99 tests
make test
```

Expected output:
```
Running tests...
========================= 99 passed in 0.19s =========================

---------- coverage: platform darwin, python 3.14.2 -----------
Name                Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------
asitop/asitop.py      177     15     26      4    92%
asitop/parsers.py      86      2     32      2    98%
asitop/utils.py       112      6     22      0    95%
-----------------------------------------------------
TOTAL                 375     23     80      6    94%
```

Current coverage: **94%** total (asitop: 92%, parsers: 98%, utils: 95%)

### 3. Run asitop

```bash
# Run asitop (requires sudo password)
make run

# Press 'q' or Ctrl+C to quit
```

That's it! You're ready to develop.

## Common Commands

```bash
# Run tests with coverage report
make test-coverage

# Run tests in watch mode (auto-runs on file changes)
make test-watch

# Run asitop with custom options
./run_asitop.sh --interval 5 --color 3

# Check code quality before committing
make check

# Clean up generated files
make clean-test
```

## Development Workflow

### Writing Tests

1. Create test in appropriate file:
   - `tests/test_parsers.py` - Parser functions
   - `tests/test_utils.py` - Utility functions
   - `tests/test_asitop.py` - Main application

2. Run tests in watch mode:
   ```bash
   make test-watch
   ```

3. Write code, save, tests run automatically

4. Check coverage:
   ```bash
   make coverage-html
   open htmlcov/index.html
   ```

### Making Changes

1. Make your changes to the code
2. Run tests: `make test`
3. Check quality: `make check`
4. Clean up: `make clean-pyc`
5. Commit your changes

## Available Make Commands

See all commands:
```bash
make help
```

Most useful commands:
- `make install-dev` - Set up development environment
- `make test` - Run all tests
- `make test-coverage` - Run tests with coverage
- `make run` - Run asitop with sudo
- `make lint` - Run Ruff linter
- `make fix` - Auto-fix linting issues
- `make format` - Format code with Black
- `make type-check` - Run Mypy type checker
- `make check` - Run all quality checks (lint, format, type, tests)
- `make clean` - Clean everything

## Project Structure

```
asitop/
├── asitop/                    # Source code
│   ├── asitop.py              # Main application
│   ├── utils.py               # Utility functions
│   └── parsers.py             # Parsing functions
├── tests/                     # Test suite (99 tests)
│   ├── test_asitop.py         # Main app tests (35 tests)
│   ├── test_utils.py          # Utils tests (30 tests)
│   ├── test_parsers.py        # Parser tests (20 tests)
│   └── test_type_contracts.py # Type contract tests (14 tests)
├── .venv/                     # Virtual environment (auto-created by uv)
├── pyproject.toml             # Project config (replaces setup.py)
├── uv.lock                    # Lock file (replaces requirements.txt)
├── Makefile                   # Build automation (uses uv)
└── run_asitop.sh              # Script to run asitop
```

## Testing Guide

All tests follow Python best practices from `python_instructions.md`:
- Type hints on all functions
- Comprehensive docstrings (PEP 257)
- Edge case testing
- Proper mocking of system calls

Run specific tests:
```bash
# Run one test file
make test ARGS="tests/test_parsers.py"

# Run one test class
python3 venv/bin/pytest tests/test_parsers.py::TestParseCPUMetrics -v

# Run one test method
python3 venv/bin/pytest tests/test_parsers.py::TestParseCPUMetrics::test_parse_cpu_metrics_m1_ultra -v
```

## Troubleshooting

**Tests fail with import errors**
```bash
make clean
make install-dev
```

**Virtual environment issues**
```bash
rm -rf venv
make venv
make install-dev
```

**asitop won't run**
```bash
# Make sure you're using make run (with sudo)
make run
```

## Documentation

- **[MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md)** - Complete Makefile documentation
- **[TESTING.md](TESTING.md)** - Testing guide and reference
- **[tests/README.md](tests/README.md)** - Test suite documentation
- **[TEST_SUMMARY.md](TEST_SUMMARY.md)** - Test suite summary

## Getting Help

```bash
# Show all Makefile commands
make help

# Run tests to verify setup
make test

# Check the guides
cat MAKEFILE_GUIDE.md
cat TESTING.md
```

## Next Steps

1. Read [MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md) for detailed Makefile usage
2. Read [TESTING.md](TESTING.md) for testing guidelines
3. Run `make test-watch` and start developing!
4. Before committing, run `make check`

Happy coding!
