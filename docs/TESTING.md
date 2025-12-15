# Testing Guide for asitop

This document provides a comprehensive guide for testing the asitop project.

## Quick Start

```bash
# Install test dependencies using uv (recommended)
make install-dev

# Or install manually with uv
uv sync --extra test

# Or install with pip (slower)
pip install -e ".[test]"

# Run all tests
make test
# or directly: uv run pytest

# Run with coverage
make test-coverage
# or directly: uv run pytest --cov=asitop --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Commands Reference

### Basic Test Execution

```bash
# Run all tests with uv
make test
# or directly:
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_parsers.py

# Run specific test class
uv run pytest tests/test_parsers.py::TestParseCPUMetrics

# Run specific test method
uv run pytest tests/test_parsers.py::TestParseCPUMetrics::test_parse_cpu_metrics_m1_ultra
```

### Coverage Reports

```bash
# Terminal coverage report
make test-coverage
# or directly:
uv run pytest --cov=asitop

# HTML coverage report
make coverage-html
# or directly:
uv run pytest --cov=asitop --cov-report=html

# XML coverage report (for CI)
uv run pytest --cov=asitop --cov-report=xml

# Show missing lines
uv run pytest --cov=asitop --cov-report=term-missing

# Fail if coverage below threshold
uv run pytest --cov=asitop --cov-fail-under=75
```

Current Coverage (as of 2025 modernization):
- **Total**: **93%** (up from 77%)
- **asitop.py**: **93%** (up from 57.95%)
- **parsers.py**: **93%** (stable from 90.35%)
- **utils.py**: **95%** (stable)

### Filtering Tests

```bash
# Run only unit tests (if marked)
uv run pytest -m unit

# Run all except slow tests
uv run pytest -m "not slow"

# Run tests matching pattern
uv run pytest -k "cpu"

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l
```

### Debugging Tests

```bash
# Print output (disable capture)
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show detailed traceback
pytest --tb=long

# Show summary of all tests
pytest --tb=line
```

## Test Structure

### Module Coverage

| Module | Test File | Coverage Focus |
|--------|-----------|----------------|
| parsers.py | test_parsers.py | Powermetrics parsing logic |
| utils.py | test_utils.py | System info and utilities |
| asitop.py | test_asitop.py | Main application logic |

### Test Categories

1. **Unit Tests**: Test individual functions in isolation
2. **Integration Tests**: Test interactions between components
3. **Edge Case Tests**: Test boundary conditions and error handling

## Writing Tests

### Test Template

```python
"""
Unit tests for module_name.

Brief description of what this test module covers.
"""

import unittest
from typing import Any, Dict
from unittest.mock import patch, MagicMock


class TestClassName(unittest.TestCase):
    """Test cases for specific_function."""

    def test_basic_functionality(self) -> None:
        """
        Test basic operation of the function.

        Detailed description of what this test validates and why
        it's important.
        """
        # Arrange
        input_data: Dict[str, Any] = {"key": "value"}

        # Act
        result = function_under_test(input_data)

        # Assert
        self.assertEqual(result, expected_value)

    def test_edge_case(self) -> None:
        """
        Test edge case handling.

        Edge case: Description of the edge case being tested.
        """
        # Test implementation


if __name__ == '__main__':
    unittest.main()
```

### Best Practices

1. **One assertion per test**: Each test should verify one specific behavior
2. **Clear test names**: Use descriptive names that explain what is being tested
3. **Comprehensive docstrings**: Follow PEP 257 conventions
4. **Type hints**: Use typing module for all parameters and returns
5. **Mock external dependencies**: Isolate tests from system state
6. **Test edge cases**: Empty inputs, zero values, max values, errors
7. **AAA pattern**: Arrange, Act, Assert structure

### Mocking Examples

```python
# Mock system command
@patch('os.popen')
def test_with_system_mock(self, mock_popen: MagicMock) -> None:
    """Test with mocked system call."""
    mock_popen.return_value.read.return_value = "output"
    result = function_that_calls_popen()
    self.assertEqual(result, expected_value)

# Mock file operations
@patch('builtins.open', mock_open(read_data='data'))
def test_with_file_mock(self) -> None:
    """Test with mocked file read."""
    result = function_that_reads_file()
    self.assertIsNotNone(result)

# Mock multiple dependencies
@patch('module.dependency2')
@patch('module.dependency1')
def test_multiple_mocks(self, mock1: MagicMock, mock2: MagicMock) -> None:
    """Test with multiple mocked dependencies."""
    # Configure mocks
    mock1.return_value = value1
    mock2.return_value = value2
    # Test implementation
```

## Code Coverage

### Coverage Goals

- **Line Coverage**: Target 80%+ (**currently 93%** - EXCEEDED!)
- **Branch Coverage**: Target 75%+ (achieved)
- **Function Coverage**: Target 90%+ (achieved)

Current Achievement (2025 Modernization):
- **asitop.py: 93%** (excellent - improved from 57.95%)
- **parsers.py: 93%** (excellent - stable from 90.35%)
- **utils.py: 95%** (excellent - stable)
- **Total: 93%** (excellent - up from 77.40%)

### Viewing Coverage

After running tests with coverage:

```bash
pytest --cov=asitop --cov-report=html
```

Open the HTML report:

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

The report shows:
- Overall coverage percentage
- Per-file coverage breakdown
- Line-by-line coverage highlighting
- Missing coverage areas

### Improving Coverage

1. Identify uncovered lines in the HTML report
2. Write tests for uncovered code paths
3. Focus on edge cases and error handling
4. Test both success and failure scenarios

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          pytest --cov=asitop --cov-report=xml --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with import errors
```bash
# Solution: Run from project root
cd /path/to/asitop
pytest
```

**Issue**: Mocks not working
```bash
# Solution: Check mock patch path matches import path
# If code does: from module import func
# Then patch: @patch('current_module.func')
# If code does: import module; module.func()
# Then patch: @patch('module.func')
```

**Issue**: Coverage not generated
```bash
# Solution: Install pytest-cov
pip install pytest-cov
```

**Issue**: Tests are slow
```bash
# Solution: Run in parallel
pip install pytest-xdist
pytest -n auto
```

## Test Data

### Sample Powermetrics Data

For testing, use realistic plist structures:

```python
mock_powermetrics = {
    "timestamp": 1234567890,
    "thermal_pressure": "Nominal",
    "processor": {
        "clusters": [
            {
                "name": "E-Cluster",
                "freq_hz": 2064000000,
                "idle_ratio": 0.5,
                "cpus": [
                    {"cpu": 0, "freq_hz": 2064000000, "idle_ratio": 0.6}
                ]
            }
        ],
        "ane_energy": 1000,
        "cpu_energy": 5000,
        "gpu_energy": 3000,
        "combined_power": 9000
    },
    "gpu": {
        "freq_hz": 1296000000,
        "idle_ratio": 0.3
    }
}
```

## Code Quality Configuration

The project uses modern, strict best practices for code quality as of 2025:

### Ruff (Linter and Formatter)
- **Comprehensive rule set**: ALL rules enabled by default with strategic ignores
- **Preview mode**: Enabled for modern best practices
- **Per-file ignores**: Customized for __init__.py, tests, and main module
- **Complexity limits**: max-args=7, max-branches=15, max-statements=50
- **Modern import sorting**: isort configuration with sections
- **Format compatibility**: Aligned with Black formatting

### Black (Code Formatter)
- **Target versions**: Python 3.10-3.14
- **Line length**: 100 characters (consistent with Ruff)
- **String normalization**: Enabled (enforce double quotes)
- **Trailing comma**: Respected (skip-magic-trailing-comma = false)
- **Comprehensive excludes**: 12 common cache/build directories

### Mypy (Type Checker)
- **Strict mode**: disallow_untyped_defs = true
- **Enhanced checks**: disallow_any_generics, disallow_untyped_calls, no_implicit_reexport
- **Module overrides**: Ignore missing imports for psutil and dashing only
- **Error detection**: warn_unreachable, warn_redundant_casts

All configuration is centralized in [pyproject.toml](../pyproject.toml#L108-L305).

## Recent Enhancements (2025)

### Modernization Updates
Since commit f393344, the project has received major quality enhancements:

1. **Ruff Configuration** (commit 1416641)
   - Upgraded to comprehensive ALL rules selection
   - Strategic ignores for practical development
   - Enhanced per-file ignore patterns
   - Modern formatter configuration

2. **Mypy Configuration** (commit 4dbd578)
   - Strict type checking enabled
   - All code refactored to pass strict mypy
   - Module-specific overrides for third-party libraries

3. **Black Configuration** (current)
   - Modern best practices with explicit settings
   - Support for Python 3.10-3.14
   - Comprehensive exclusion patterns
   - Aligned with Ruff formatter

### Code Refactoring
All code has been refactored to comply with:
- Strict type annotations
- Modern linting rules
- Consistent formatting
- Best practice patterns

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Documentation](https://black.readthedocs.io/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 Docstring Conventions](https://peps.python.org/pep-0257/)

## Getting Help

If you encounter issues with tests:

1. Check this documentation
2. Review test examples in the test files
3. Read the error messages carefully
4. Use `pytest -vv` for detailed output
5. Run `make check` to see all quality checks
6. Open an issue on GitHub with test output
