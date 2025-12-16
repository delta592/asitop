# Makefile Guide for asitop

This guide explains how to use the Makefile to manage the asitop project with automatic virtual environment handling.

## Quick Start

```bash
# Set up everything and run tests
make install-dev
make test

# Run asitop
make run
```

## Overview

The Makefile provides a convenient way to:
- Use **uv** for fast, modern dependency management
- Automatically manage a Python virtual environment at `.venv/`
- Install dependencies with reproducible builds (via uv.lock)
- Run tests with coverage
- Run asitop with proper sudo permissions
- Perform code quality checks
- Build and distribute packages

All commands use **uv** and automatically manage the virtual environment.

## What is uv?

[uv](https://github.com/astral-sh/uv) is a modern Python package manager that is:
- 10-100x faster than pip
- Built in Rust for performance
- Compatible with existing Python tooling
- PEP 517/518/621 compliant

This project uses uv via `pyproject.toml` instead of traditional `requirements.txt` and `setup.py`.

## Prerequisites

Before using the Makefile, install uv:

```bash
# macOS/Linux
brew install uv

# Alternative: pip
pip install uv

# Verify installation
uv --version
```

## Setup Commands

### Sync Production Dependencies

```bash
make sync
```

- Syncs production dependencies only using `uv sync --no-dev`
- Creates `.venv/` if it doesn't exist
- Installs dashing and psutil
- Does NOT install test dependencies
- Uses `uv.lock` for reproducible builds

### Install Production Dependencies

```bash
make install
```

Alias for `make sync`.

### Install Development Dependencies

```bash
make install-dev
```

- Syncs all dependencies using `uv sync --extra test`
- Creates `.venv/` if it doesn't exist
- Installs production dependencies
- Installs test dependencies (pytest, coverage, linters)
- **Use this for development and testing**
- Uses `uv.lock` for reproducible builds

## Testing Commands

### Run All Tests

```bash
make test
```

Runs all tests with verbose output using `uv run pytest`.

Example output:
```
tests/test_parsers.py::TestParseCPUMetrics::test_parse_cpu_metrics_m1 PASSED
tests/test_utils.py::TestGetSOCInfo::test_get_soc_info_m1_max PASSED
...
========================= 81 passed in 0.24s =========================

---------- coverage: platform darwin, python 3.14.2 -----------
Name                Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------
asitop/asitop.py      169     64     26      4  57.95%
asitop/parsers.py      82      7     32      2  90.35%
asitop/utils.py       107      6     22      0  95.35%
-----------------------------------------------------
TOTAL                 358     77     80      6  77.40%
```

### Run Tests with Verbose Output

```bash
make test-verbose
```

Runs tests with extra verbose output (shows all test details).

### Run Tests with Coverage

```bash
make test-coverage
```

Runs tests and displays coverage report in terminal:

```
---------- coverage: platform darwin, python 3.9.6 -----------
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
asitop/asitop.py      144     12   92%   45-48, 152-155
asitop/parsers.py      59      3   95%   78-80
asitop/utils.py       131      8   94%   156-159, 189-192
-------------------------------------------------
TOTAL                 334     23   93%
```

### Generate HTML Coverage Report

```bash
make coverage-html
```

Generates an HTML coverage report and opens it:

```bash
# After running, open the report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Generate Coverage Report (Terminal + HTML)

```bash
make coverage-report
```

Displays coverage in terminal and generates HTML report.

### Watch Mode (Run Tests on File Changes)

```bash
make test-watch
```

Automatically runs tests whenever you save a file. Great for TDD!

## Running asitop

### Run with Sudo (Recommended)

```bash
make run
```

- Installs dependencies if needed
- Runs asitop with sudo
- Prompts for password once at the start
- Press 'q' or Ctrl+C to stop

Example:
```bash
$ make run
Running asitop with sudo (password required)...
Press Ctrl+C or 'q' to stop
Password: [enter your password]

ASITOP - Performance monitoring CLI tool for Apple Silicon
...
```

### Run without Sudo (Will Prompt Later)

```bash
make run-nosudo
```

- Runs asitop without sudo initially
- Will prompt for password when needed
- Press 'q' or Ctrl+C to stop
- Less convenient but works the same

### Using the Shell Script

Alternatively, use the provided shell script:

```bash
./run_asitop.sh
```

This script:
- Automatically creates venv if needed
- Installs dependencies if needed
- Runs asitop with sudo using the venv Python

You can also pass arguments:

```bash
./run_asitop.sh --interval 5 --color 3
```

## Code Quality Commands

### Run Linter (Ruff)

```bash
make lint
```

Runs Ruff to check code quality:
- Fast Python linter (10-100x faster than flake8/pylint)
- Checks for syntax errors, PEP 8 violations, and code smells
- Includes rules from flake8, pylint, isort, and more

### Auto-Fix Linting Issues

```bash
make fix
```

Automatically fixes linting issues that Ruff can safely correct:
- Import sorting
- Unused imports
- Code style issues
- Many PEP 8 violations

### Format Code (Black)

```bash
make format
```

Formats code using Black, the uncompromising Python formatter:
- Consistent code style across the project
- Line length: 100 characters
- Automatic formatting

### Check Code Formatting

```bash
make format-check
```

Checks if code is formatted correctly without making changes.
Use before committing to ensure code passes CI checks.

### Run Type Checker (Mypy)

```bash
make type-check
```

Runs Mypy to check type annotations and catch type errors.

### Run Type Checker (Pyright)

```bash
make type-check-pyright
```

Runs Pyright to check type annotations. Pyright is an alternative type checker that:
- Often catches different issues than mypy
- Uses the same engine as VS Code's Pylance
- Provides additional type safety coverage

### Run All Quality Checks

```bash
make check
```

Runs complete quality check suite:
1. Ruff linter
2. Black format check
3. Mypy type check
4. Pyright type check
5. All tests with coverage

**Use this before committing code!**

## Cleanup Commands

### Clean Everything

```bash
make clean
```

Removes:
- Virtual environment (`venv/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info`)
- Python cache files
- Test/coverage files

**Warning**: This removes the virtual environment, so you'll need to run `make install-dev` again.

### Clean Python Cache

```bash
make clean-pyc
```

Removes:
- `*.pyc` files
- `__pycache__/` directories
- `*.egg-info` directories

### Clean Test Files

```bash
make clean-test
```

Removes:
- `.pytest_cache/`
- `htmlcov/`
- `.coverage`
- `coverage.xml`
- Temporary powermetrics files

## Distribution Commands

### Build Distribution

```bash
make dist
```

Creates distribution packages in `dist/`:
- Source distribution (`.tar.gz`)
- Wheel distribution (`.whl`)

### Upload to TestPyPI

```bash
make upload-test
```

Uploads the package to TestPyPI for testing before production release.

### Upload to PyPI

```bash
make upload
```

Uploads the package to PyPI (production). **Use with caution!**

You'll be prompted for confirmation before uploading.

## Typical Workflows

### Setting Up for Development

```bash
# Clone the repository
git clone https://github.com/tlkh/asitop.git
cd asitop

# Set up development environment
make install-dev

# Run tests to verify everything works
make test
```

### Running asitop

```bash
# Quick run
make run

# Or use the script with custom options
./run_asitop.sh --interval 2 --color 5
```

### Before Committing Changes

```bash
# Run all quality checks
make check

# If tests fail, fix issues and re-run
make test

# Clean up before committing
make clean-test clean-pyc
```

### Testing Workflow (TDD)

```bash
# Install dev dependencies
make install-dev

# Run tests in watch mode
make test-watch

# In another terminal, edit code
# Tests automatically re-run when you save

# When done, check coverage
make coverage-html
open htmlcov/index.html
```

### Release Workflow

```bash
# Update version in setup.py
vim setup.py

# Run all checks
make check

# Build distribution
make dist

# Test on TestPyPI first
make upload-test

# If everything works, upload to PyPI
make upload
```

## Troubleshooting

### uv Not Found

**Problem**: `make: uv: command not found`

**Solution**: Install uv
```bash
# macOS
brew install uv

# Alternative
pip install uv

# Verify
uv --version
```

### Virtual Environment Issues

**Problem**: Dependencies not installing correctly

**Solution**: Clean and reinstall
```bash
make clean
make install-dev
```

### Permission Issues

**Problem**: Cannot create venv or install packages

**Solution**: Check directory permissions
```bash
ls -la
chmod u+w .
```

### Sudo Password Required Multiple Times

**Problem**: asitop keeps asking for password

**Solution**: Use `make run` instead of `make run-nosudo`, which asks for sudo once upfront.

### Tests Fail to Import asitop

**Problem**: `ModuleNotFoundError: No module named 'asitop'`

**Solution**: Make sure you're running from the project root:
```bash
cd /path/to/asitop
make test
```

### Missing Dependencies

**Problem**: Tests fail due to missing modules

**Solution**: Reinstall dependencies
```bash
make clean
make install-dev
make test
```

### Makefile Not Found

**Problem**: `make: *** No targets specified and no makefile found.`

**Solution**: You're not in the project directory
```bash
cd /path/to/asitop
make help
```

## Environment Variables

The Makefile uses these variables:

```makefile
UV := uv              # uv command
UV_RUN := $(UV) run   # uv run prefix for commands
VENV := .venv         # Virtual environment location
```

These are configured in the Makefile and generally don't need to be changed.

## Tips and Best Practices

1. **Always use `make install-dev`** for development
2. **Run `make test`** before committing changes
3. **Use `make test-watch`** for active development
4. **Run `make clean-test`** periodically to free disk space
5. **Use `make check`** before pushing to remote
6. **Run asitop with `make run`** for convenience
7. **Check coverage** with `make coverage-html` regularly

## uv and Virtual Environment Details

The Makefile uses uv to create and manage a virtual environment at `./.venv/`:

```
asitop/
├── .venv/                   # Virtual environment (auto-created by uv)
│   ├── bin/
│   │   ├── python          # Isolated Python interpreter
│   │   ├── pip             # Isolated pip
│   │   └── pytest          # Test runner
│   └── lib/
│       └── python3.x/
│           └── site-packages/  # Isolated packages
├── pyproject.toml          # Project config (replaces setup.py)
├── uv.lock                 # Lock file (replaces requirements.txt)
├── Makefile
└── ...
```

Benefits:
- **Speed**: 10-100x faster than pip for dependency resolution
- **Isolation**: Packages don't affect system Python
- **Reproducibility**: uv.lock ensures exact same versions across machines
- **Convenience**: Automatic activation in Makefile commands via `uv run`
- **Safety**: Can delete `.venv/` and recreate anytime with `make install-dev`
- **Modern**: Uses pyproject.toml (PEP 517/518/621) instead of setup.py

## Getting Help

```bash
# Show all available commands
make help

# Or just run make without arguments
make
```

## Examples

### Example 1: Fresh Setup and Test

```bash
$ git clone https://github.com/tlkh/asitop.git
$ cd asitop
$ make install-dev
Creating virtual environment...
Installing development dependencies...
Done.

$ make test
Running tests...
========================= 67 passed in 0.52s =========================
```

### Example 2: Run asitop

```bash
$ make run
Running asitop with sudo (password required)...
Password: ****
ASITOP - Performance monitoring CLI tool for Apple Silicon
...
```

### Example 3: Development Workflow

```bash
$ make install-dev
$ make test-watch  # Start watch mode

# In another terminal
$ vim asitop/utils.py  # Edit code

# Back in first terminal - tests run automatically
# Fix any failures, save again, repeat
```

### Example 4: Check Code Quality

```bash
$ make check
=== Running Ruff linter ===
All checks passed!

=== Checking code formatting with Black ===
All done! ✨ 🍰 ✨
8 files would be left unchanged.

=== Running Mypy type checker ===
Success: no issues found in 4 source files

=== Running Pyright type checker ===
0 errors, 0 warnings, 0 informations

=== Running tests with coverage ===
========================= 81 passed in 0.24s =========================

Quality checks complete
```

## Additional Resources

- [Makefile Documentation](https://www.gnu.org/software/make/manual/)
- [Python venv Documentation](https://docs.python.org/3/library/venv.html)
- [pytest Documentation](https://docs.pytest.org/)
- [asitop GitHub Repository](https://github.com/tlkh/asitop)
