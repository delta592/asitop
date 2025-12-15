# VSCode Setup for asitop Development

This guide helps you configure VSCode for optimal asitop development with Python 3.12+ features.

## Why This Guide?

asitop uses modern Python 3.12+ features including:
- Type aliases with `type` statement (PEP 695)
- Pattern matching with `match-case` (PEP 636)
- Union types with `X | Y` syntax (PEP 604)

Pylance (VSCode's Python type checker) may show errors if not properly configured, even though mypy and all tests pass.

## Quick Setup

### 1. Select the Correct Python Interpreter

In VSCode:
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from `.venv` (should show Python 3.14.2)

**Path should be**: `./venv/bin/python` or similar

### 2. Verify Configuration Files

The repository includes:
- [`.vscode/settings.json`](../.vscode/settings.json) - VSCode Python settings
- [`pyrightconfig.json`](../pyrightconfig.json) - Pylance type checker configuration

These files configure Pylance to:
- Use Python 3.14
- Recognize modern type syntax
- Use the `.venv` virtual environment
- Disable false-positive errors

### 3. Reload VSCode Window

After setup:
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type "Developer: Reload Window"
3. Wait for Pylance to re-analyze the workspace

## Troubleshooting

### Still Seeing Type Errors?

**Problem**: Pylance shows errors on `type` statements or modern syntax

**Solutions**:

1. **Verify Python version in VSCode status bar** (bottom right)
   - Should show "3.14.2 ('.venv': venv)"
   - If not, select the correct interpreter

2. **Check Pylance is using the right Python**
   ```bash
   # In terminal
   .venv/bin/python --version
   # Should show: Python 3.14.2
   ```

3. **Manually reload Pylance**
   - `Cmd+Shift+P` → "Pylance: Restart Server"

4. **Check pyrightconfig.json is being used**
   - VSCode should show "Using pyrightconfig.json" in the output panel
   - Open: View → Output → Select "Pylance" from dropdown

### Errors on `type PowermetricsDict = dict[str, Any]`

This is the modern type alias syntax from Python 3.12 (PEP 695).

**If Pylance shows an error**:
1. Verify `pyrightconfig.json` has `"pythonVersion": "3.14"`
2. Check VSCode is using `.venv/bin/python` (Python 3.14.2)
3. Restart Pylance server

**Why it works in mypy but not Pylance**:
- Mypy reads `pyproject.toml` which specifies Python 3.12
- Pylance needs explicit configuration via `pyrightconfig.json`

### Errors on `match-case` Statements

Pattern matching was added in Python 3.10 (PEP 636).

**If Pylance shows an error**:
- Ensure `pythonVersion` in `pyrightconfig.json` is at least `"3.10"`
- We use `"3.14"` which supports all modern features

### Import Errors for `psutil` or `dashing`

**This is expected!** These packages don't have complete type stubs.

**Solution**: We've configured Pylance to ignore missing type stubs:
```json
"reportMissingTypeStubs": false
```

You can also see in `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = ["psutil.*", "dashing.*"]
ignore_missing_imports = true
```

## Recommended VSCode Extensions

For the best development experience:

### Required
- **Python** (ms-python.python) - Python language support
- **Pylance** (ms-python.vscode-pylance) - Fast Python type checker

### Recommended
- **Black Formatter** (ms-python.black-formatter) - Auto-format on save
- **Ruff** (charliermarsh.ruff) - Fast linting
- **Even Better TOML** (tamasfe.even-better-toml) - TOML syntax support

### Optional
- **GitHub Copilot** - AI code completion
- **GitLens** - Enhanced Git integration

## Configuration Files Explained

### `.vscode/settings.json`

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportGeneralTypeIssues": "none"
  }
}
```

- Uses basic type checking (not strict)
- Points to `.venv` Python interpreter
- Reduces false-positive type errors

### `pyrightconfig.json`

```json
{
  "pythonVersion": "3.14",
  "venv": ".venv",
  "typeCheckingMode": "basic",
  "reportGeneralTypeIssues": "none"
}
```

- Explicitly sets Python 3.14
- Tells Pylance about virtual environment
- Disables overly strict type checking

## Why Tests Pass But Pylance Shows Errors

Different tools use different type checkers:

| Tool | Type Checker | Configuration |
|------|--------------|---------------|
| **make test** | Uses runtime Python | `.venv/bin/python` (3.14.2) |
| **make type-check** | Uses mypy | `pyproject.toml` → `python_version = "3.12"` |
| **VSCode/Pylance** | Uses Pyright | `pyrightconfig.json` → `pythonVersion = "3.14"` |

All three need proper configuration to support Python 3.12+ features.

## Verifying Everything Works

Run these commands to verify your setup:

```bash
# 1. Check Python version
.venv/bin/python --version
# Expected: Python 3.14.2

# 2. Run mypy (should pass)
make type-check
# Expected: Success: no issues found in 4 source files

# 3. Run tests (should pass)
make test
# Expected: 85 passed in 0.18s

# 4. Check Ruff (should pass)
make lint
# Expected: All checks passed!
```

If all four pass, your environment is correct. Any Pylance errors in VSCode are configuration issues.

## Manual Pylance Configuration

If the provided config files don't work, manually configure Pylance:

1. Open VSCode Settings (`Cmd+,`)
2. Search for "Python > Analysis: Type Checking Mode"
3. Set to "basic" (not "off" or "strict")
4. Search for "Python: Default Interpreter Path"
5. Set to `${workspaceFolder}/.venv/bin/python`
6. Restart VSCode

## Getting Help

If you still see errors after following this guide:

1. **Check the Output Panel**
   - View → Output → Select "Pylance"
   - Look for error messages or warnings

2. **Verify File Detection**
   - Pylance should show "Using pyrightconfig.json"
   - If not, check the file is in the project root

3. **Try Strict Type Checking** (to see all issues)
   ```json
   "python.analysis.typeCheckingMode": "strict"
   ```
   This will show all potential issues, not just errors

4. **Check VSCode Version**
   - Ensure you're running the latest VSCode
   - Update Pylance extension to latest version

## References

- [PEP 695 - Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 636 - Structural Pattern Matching](https://peps.python.org/pep-0636/)
- [PEP 604 - Union Type Syntax](https://peps.python.org/pep-0604/)
- [Pylance Documentation](https://github.com/microsoft/pylance-release)
- [Pyright Configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)

---

**Summary**: Pylance errors while tests pass usually means the IDE isn't configured for Python 3.12+. The provided config files fix this.
