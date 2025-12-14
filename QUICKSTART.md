# Quick Start Guide for asitop Development

Get up and running with asitop development in 3 simple steps!

## Prerequisites

- macOS with Apple Silicon (M1, M1 Pro, M1 Max, M1 Ultra, or M2)
- Python 3.8 or higher
- make (comes with Xcode Command Line Tools)

## Quick Start

### 1. Set Up Development Environment

```bash
# Install development dependencies in a virtual environment
make install-dev
```

This creates a virtual environment at `./venv/` and installs all dependencies.

### 2. Run Tests

```bash
# Run all 67 tests
make test
```

Expected output:
```
Running tests...
========================= 67 passed in 0.5s =========================
```

### 3. Run asitop

```bash
# Run asitop (requires sudo password)
make run
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
- `make check` - Run tests and linters
- `make clean` - Clean everything

## Project Structure

```
asitop/
├── asitop/              # Source code
│   ├── asitop.py        # Main application
│   ├── utils.py         # Utility functions
│   └── parsers.py       # Parsing functions
├── tests/               # Test suite (67 tests)
│   ├── test_asitop.py   # Main app tests
│   ├── test_utils.py    # Utils tests
│   └── test_parsers.py  # Parser tests
├── venv/                # Virtual environment (auto-created)
├── Makefile             # Build automation
└── run_asitop.sh        # Script to run asitop
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
