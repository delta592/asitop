# Testing Guide for asitop

This document provides a comprehensive guide for testing the asitop project.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=asitop --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Commands Reference

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parsers.py

# Run specific test class
pytest tests/test_parsers.py::TestParseCPUMetrics

# Run specific test method
pytest tests/test_parsers.py::TestParseCPUMetrics::test_parse_cpu_metrics_m1_ultra
```

### Coverage Reports

```bash
# Terminal coverage report
pytest --cov=asitop

# HTML coverage report
pytest --cov=asitop --cov-report=html

# XML coverage report (for CI)
pytest --cov=asitop --cov-report=xml

# Show missing lines
pytest --cov=asitop --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=asitop --cov-fail-under=80
```

### Filtering Tests

```bash
# Run only unit tests (if marked)
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run tests matching pattern
pytest -k "cpu"

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l
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

- **Line Coverage**: Minimum 80%
- **Branch Coverage**: Minimum 75%
- **Function Coverage**: Minimum 90%

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

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 Docstring Conventions](https://peps.python.org/pep-0257/)

## Getting Help

If you encounter issues with tests:

1. Check this documentation
2. Review test examples in the test files
3. Read the error messages carefully
4. Use `pytest -vv` for detailed output
5. Open an issue on GitHub with test output
