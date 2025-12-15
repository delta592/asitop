# Type Safety in asitop: Tests vs Static Type Checkers

This document explains the difference between runtime type checking (tests) and static type checking (Pylance/mypy), and how to improve type safety in the codebase.

## The Issue We Discovered

**What happened:**
- All 85 tests passed ✅
- Mypy type checking passed ✅
- But Pylance showed type errors about `HGauge.value` expecting `int` but receiving `float | int | None`

**Why this matters:**
This is a **type contract violation** - the `dashing` library's `HGauge.value` is typed to accept only `int`, but we were passing values that could be `float` or `None`.

## Why Tests Didn't Catch This

### Runtime vs Static Type Checking

Python has **two different type systems**:

1. **Runtime Type System** (what tests use)
   - Types are checked when code actually runs
   - Python is dynamically typed - it doesn't enforce type hints at runtime
   - Libraries like `dashing` may or may not validate types when you assign values

2. **Static Type System** (what Pylance/mypy use)
   - Types are checked without running the code
   - Analyzes code structure and type annotations
   - Catches type mismatches before runtime

### Example

```python
# This code RUNS fine in Python (runtime):
gauge = HGauge()
gauge.value = 3.14  # Python allows this even though HGauge expects int

# But Pylance/mypy will complain (static):
# Error: Type "float" is not assignable to "int"
```

### Why Our Tests Passed

1. **Mocked objects** - Tests often use `MagicMock` which accepts any assignment
2. **No runtime validation** - The `dashing` library likely doesn't validate types at runtime
3. **Type hints are optional** - Python ignores type hints during execution

## Why Mypy Didn't Catch This Initially

Mypy missed the issue because of **`Any` types**:

```python
type CPUMetrics = dict[str, Any]  # "Any" disables type checking
```

When we use `Any`, we're telling mypy "I don't know/care about the types here", which turns off type checking for dictionary values.

**Why we use `Any` for CPUMetrics:**

The CPU metrics dictionary contains heterogeneous types:
- `"E-Cluster_active"`: `int` (percentage)
- `"E-Cluster_freq_Mhz"`: `int` (frequency)
- `"cpu_W"`: `float` (power in watts)
- `"e_core"`: `list[int]` (core IDs)

To properly type this without `Any`, we'd need a complex `TypedDict`:

```python
from typing import TypedDict

class CPUMetricsDict(TypedDict, total=False):
    E_Cluster_active: int
    E_Cluster_freq_Mhz: int
    P_Cluster_active: int
    P_Cluster_freq_Mhz: int
    cpu_W: float
    gpu_W: float
    ane_W: float
    package_W: float
    e_core: list[int]
    p_core: list[int]
    # ... and 50+ more dynamic keys like "E-Cluster0_active", etc.
```

This is impractical because:
- The keys are dynamic (e.g., `f"P-Cluster{i}_active"`)
- Different M-series chips have different numbers of cores
- It would require maintaining a complex type definition

**Trade-off:** Using `Any` is a pragmatic choice for flexibility, but it reduces type safety.

## How to Improve Type Safety

### Approach 1: Use Pyright/Pylance in CI (Recommended)

Add Pyright to your GitHub Actions workflow:

```yaml
# .github/workflows/tests.yml
- name: Type check with Pyright
  run: |
    uv pip install pyright
    uv run pyright asitop/
```

**Benefits:**
- Catches type issues that mypy misses
- Pylance and Pyright use the same type checker
- Better library stub support

### Approach 2: Enable Stricter Mypy Settings

Update `pyproject.toml`:

```toml
[tool.mypy]
# Stricter settings
disallow_any_explicit = true  # Warn when using Any
disallow_any_generics = true  # Require type params for generics
warn_return_any = true        # Already enabled
```

**Trade-off:** This will generate many warnings for `CPUMetrics` and `PowermetricsDict`.

### Approach 3: Add Runtime Type Validation Tests ✅ IMPLEMENTED

Create tests that validate types at runtime.

**Status**: ✅ **Implemented in `tests/test_type_contracts.py`**

We've added comprehensive runtime type validation tests with 14 test cases across 4 test classes:

1. **TestGaugeValueTypes** - Validates all gauge values are `int`
   - RAM gauge values (with and without swap)
   - CPU gauge values (all `*_active` and `*_freq_Mhz` fields)
   - GPU gauge values (`active` and `freq_MHz`)
   - `calculate_gpu_usage()` return values

2. **TestNumericValueRanges** - Validates values are in reasonable ranges
   - RAM metrics (GB values, percentages 0-100)
   - CPU metrics (frequencies, power values, core lists)
   - GPU metrics (frequencies, active percentages)

3. **TestTypeConsistency** - Validates types across different code paths
   - GPU with zero frequency
   - GPU with DVFM states
   - RAM with edge cases (zero available, all available)

4. **TestReturnValueStructure** - Validates dictionary structure and keys
   - RAM metrics dictionary structure and types
   - GPU metrics dictionary structure and types
   - CPU metrics required keys

**Benefits:**
- ✅ Explicitly validates types at runtime
- ✅ Catches type contract violations that static checkers find
- ✅ Documents expected types for future developers
- ✅ Validates edge cases maintain type consistency
- ✅ Ensures values are in reasonable ranges for the domain

**Test Results:**
```bash
$ make test
99 passed in 0.19s  # 14 new type contract tests added
Coverage: 94% (up from 93%)
```

### Approach 4: Use Type Guards (Python 3.10+)

Add type narrowing in the code:

```python
def ensure_int(value: int | float | None) -> int:
    """Type guard to ensure value is int."""
    if value is None:
        return 0
    if isinstance(value, float):
        return int(value)
    return value

# Usage
ram_gauge.value = ensure_int(ram_metrics_dict["free_percent"])
```

**Benefits:**
- Makes type conversions explicit
- Type checkers understand the narrowing
- Clear intent in the code

### Approach 5: Add Type Stubs for `dashing` Library

If the `dashing` library lacks type stubs, create them:

```python
# typings/dashing.pyi
class HGauge:
    value: int
    title: str
    def __init__(self, val: int = 0, title: str = "", **kwargs) -> None: ...

class VGauge:
    value: int
    title: str
    def __init__(self, val: int = 0, title: str = "", **kwargs) -> None: ...
```

**Benefits:**
- Provides type information for external libraries
- Helps both Pylance and mypy
- No changes to runtime code needed

## Recommended Solution

For asitop, the best approach is a **combination**:

1. ✅ **Keep explicit `int()` conversions** ✅ DONE
   - Makes intent clear
   - Works with both runtime and static checkers
   - No performance impact

2. ✅ **Add runtime type validation tests** ✅ DONE
   - Validates type contracts
   - Catches regressions
   - Documents expected types
   - **14 new tests added in `tests/test_type_contracts.py`**

3. ✅ **Consider Pyright in CI** (optional)
   - Additional safety net
   - Catches issues early
   - Low maintenance overhead

4. ❌ **Don't replace `Any` with complex unions**
   - Too much maintenance burden
   - Makes code harder to work with
   - Pragmatic trade-off for flexibility

## Implementation Summary

We've successfully implemented runtime type validation tests! See `tests/test_type_contracts.py` for the complete implementation with 14 comprehensive test cases covering:

- All gauge value types (RAM, CPU, GPU, ANE)
- Numeric value ranges and reasonableness
- Type consistency across edge cases
- Return value structure validation

Run the tests with:
```bash
make test
# or specifically:
pytest tests/test_type_contracts.py -v
```

## Summary

**Key Insights:**

1. **Tests check runtime behavior** - They don't enforce type contracts
2. **Static type checkers (Pylance/mypy) check type contracts** - They catch mismatches before runtime
3. **Using `Any` disables static type checking** - Pragmatic for complex heterogeneous dicts
4. **Explicit type conversions** are the best solution for gauge values
5. **Runtime type tests** can supplement static checking

**Best Practices:**

- Use explicit `int()` conversions when assigning to typed properties
- Document why `Any` is used in type aliases
- Consider adding runtime type validation tests for critical contracts
- Keep type hints even if using `Any` - they document intent
- Balance type safety with code maintainability

**For asitop specifically:**

The current approach (explicit `int()` conversions + `Any` for complex dicts) is the right pragmatic balance between type safety and maintainability. Adding runtime type validation tests would provide additional safety without the maintenance burden of complex `TypedDict` definitions.

## References

- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Python Type Checking Guide](https://realpython.com/python-type-checking/)
