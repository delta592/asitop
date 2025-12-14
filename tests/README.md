# asitop Test Suite

This directory contains comprehensive unit tests for the asitop project, following the Python coding conventions specified in python_instructions.md.

## Overview

The test suite provides comprehensive coverage of all core asitop modules:

- **test_parsers.py**: Tests for powermetrics data parsing functions
- **test_utils.py**: Tests for utility functions and system information gathering
- **test_asitop.py**: Tests for main application logic and integration

## Running Tests

### Install Test Dependencies

First, install the testing dependencies using uv (recommended):

```bash
# Using make (recommended)
make install-dev

# Or manually with uv
uv sync --extra test

# Or using pip (slower)
pip install -e ".[test]"
```

### Run All Tests

To run the complete test suite:

```bash
# Using make (recommended)
make test

# Or directly with uv
uv run pytest

# Or with pytest directly (requires activation)
pytest
```

### Run Specific Test Files

To run tests for a specific module:

```bash
# Using uv (recommended)
uv run pytest tests/test_parsers.py
uv run pytest tests/test_utils.py
uv run pytest tests/test_asitop.py

# Or with make
make test ARGS="tests/test_parsers.py"
```

### Run Specific Test Classes or Methods

To run a specific test class:

```bash
uv run pytest tests/test_parsers.py::TestParseCPUMetrics
```

To run a specific test method:

```bash
uv run pytest tests/test_parsers.py::TestParseCPUMetrics::test_parse_cpu_metrics_m1_ultra
```

### Run with Coverage Report

To generate a code coverage report:

```bash
# Using make (recommended)
make test-coverage

# Or directly with uv
uv run pytest --cov=asitop --cov-report=html

# View HTML report
open htmlcov/index.html
```

This will create an HTML coverage report in the `htmlcov/` directory.

Current Coverage (as of latest run):
- **Total**: 79.86%
- **parsers.py**: 98.85%
- **utils.py**: 96.49%
- **asitop.py**: 54.02%

### Run with Verbose Output

For more detailed test output:

```bash
# Using make
make test-verbose

# Or directly
uv run pytest -v
```

### Run Tests in Parallel

To speed up test execution using multiple CPU cores:

```bash
uv add --dev pytest-xdist
uv run pytest -n auto
```

## Test Structure

### test_parsers.py

Tests for parsing functions that extract metrics from powermetrics output:

- **TestParseThermalPressure**: Tests for thermal pressure status parsing
- **TestParseBandwidthMetrics**: Tests for memory bandwidth parsing and aggregation
- **TestParseCPUMetrics**: Tests for CPU frequency, utilization, and power parsing
- **TestParseGPUMetrics**: Tests for GPU frequency and utilization parsing

Key test scenarios:
- Normal operation with valid data
- M1 Ultra dual-cluster configurations
- Edge cases (idle, full load, empty data)
- Aggregation logic for multi-core systems

### test_utils.py

Tests for utility functions and system information gathering:

- **TestConvertToGB**: Byte to gigabyte conversion tests
- **TestClearConsole**: Console clearing functionality
- **TestParsePowermetrics**: Powermetrics file parsing with plist data
- **TestGetRamMetricsDict**: RAM and swap memory metric collection
- **TestGetCPUInfo**: CPU information extraction via sysctl
- **TestGetCoreCounts**: E-core and P-core count detection
- **TestGetGPUCores**: GPU core count detection via system_profiler
- **TestGetSOCInfo**: Complete SOC information gathering and spec lookup
- **TestRunPowermetricsProcess**: Powermetrics process management

Key test scenarios:
- All Apple Silicon variants (M1, M1 Pro, M1 Max, M1 Ultra, M2)
- Edge cases (no swap, missing data, unknown chips)
- File operations and cleanup
- System command mocking

### test_asitop.py

Tests for main application logic:

- **TestArgumentParsing**: Command-line argument validation
- **TestMainFunction**: Main loop initialization and execution
- **TestDequeMemoryManagement**: Memory leak prevention via bounded deques
- **TestGetAvgFunction**: Rolling average calculations
- **TestRestartLogic**: Powermetrics periodic restart logic
- **TestThermalThrottleDetection**: Thermal throttling detection
- **TestANEUtilizationCalculation**: ANE power to utilization conversion
- **TestTimestampHandling**: New data detection via timestamps

Key test scenarios:
- Argument parsing and defaults
- UI component initialization
- Memory management for long-running processes
- Thermal and power calculations
- Data freshness detection

## Test Coverage Goals

The test suite aims for:

- **Line coverage**: >80% (currently 79.86%, nearly met!)
- **Branch coverage**: >75%
- **Function coverage**: >90%

Current Achievement:
- **parsers.py**: 98.85% (excellent)
- **utils.py**: 96.49% (excellent)
- **asitop.py**: 54.02% (UI-heavy code, acceptable)

Current coverage can be checked by running:

```bash
make test-coverage
# or: uv run pytest --cov=asitop --cov-report=term-missing
```

## Writing New Tests

When adding new tests, follow these guidelines from python_instructions.md:

### Docstring Format

Each test function should have a comprehensive docstring:

```python
def test_example_function(self) -> None:
    """
    Brief description of what is being tested.

    Detailed explanation of the test scenario, including why
    this test is important and what edge cases it covers.
    """
    # Test implementation
```

### Type Hints

Use type hints for all test parameters and return types:

```python
from typing import Dict, Any, List
from unittest.mock import MagicMock

def test_with_types(self, mock_obj: MagicMock) -> None:
    """Test with proper type annotations."""
    test_data: Dict[str, Any] = {"key": "value"}
    # Test implementation
```

### Test Organization

1. Arrange: Set up test data and mocks
2. Act: Execute the function being tested
3. Assert: Verify the expected behavior

```python
def test_example(self) -> None:
    """Test example following AAA pattern."""
    # Arrange
    input_data = {"value": 42}

    # Act
    result = function_under_test(input_data)

    # Assert
    self.assertEqual(result, expected_value)
```

### Edge Cases

Always test edge cases:

- Empty inputs
- Zero values
- Maximum values
- Invalid data types
- Missing data
- Error conditions

### Mocking

Use mocks for:

- System calls (os.popen, subprocess.Popen)
- File I/O operations
- External dependencies (psutil)
- Time-dependent operations

Example:

```python
from unittest.mock import patch, MagicMock

@patch('module.external_dependency')
def test_with_mock(self, mock_dep: MagicMock) -> None:
    """Test using mock objects."""
    mock_dep.return_value = expected_value
    # Test implementation
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines using uv. Recommended workflow:

1. Install uv in CI environment
2. Run `uv sync --extra test` to install dependencies
3. Run tests with coverage
4. Enforce minimum coverage thresholds
5. Run linting (pylint, flake8)
6. Run type checking (mypy)

Example CI commands:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra test

# Run tests with coverage
uv run pytest --cov=asitop --cov-report=xml --cov-fail-under=75

# Or use make
make test-coverage
```

## Troubleshooting

### Tests Fail Due to Missing Mocks

If tests fail because they try to access real system resources, ensure you're properly mocking system calls. All tests should be isolated and not depend on the actual system state.

### Import Errors

If you encounter import errors, ensure you're running tests from the project root directory and that the asitop package is in your Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Coverage Not Generated

If coverage reports aren't generated, ensure pytest-cov is installed:

```bash
# Using uv (recommended)
uv sync --extra test

# Or pip
pip install pytest-cov
```

## Contributing

When contributing new features:

1. Write tests first (TDD approach recommended)
2. Ensure all tests pass
3. Maintain or improve code coverage
4. Follow the Python coding conventions in python_instructions.md
5. Add appropriate docstrings and type hints

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [coverage.py documentation](https://coverage.readthedocs.io/)
- [PEP 257: Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484: Type Hints](https://peps.python.org/pep-0484/)
