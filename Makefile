# Makefile for asitop
# Provides commands for testing, running, and managing the project
# Uses uv for dependency management

.DEFAULT_GOAL := help

# uv configuration
UV := uv
UV_RUN := $(UV) run
VENV := .venv

## Show this help
.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@awk '/^## /{desc=substr($$0,4)} /^[a-zA-Z_-]+:/{if(desc){printf "  %-22s %s\n",$$1,desc; desc=""}}' $(MAKEFILE_LIST) | sed 's/://' | sort
	@echo ""

## Sync production dependencies (uv sync --no-dev)
.PHONY: sync
sync:
	@echo "Syncing production dependencies with uv..."
	$(UV) sync --no-dev
	@echo "Production dependencies synced"

## Install production dependencies (alias for sync)
.PHONY: install
install: sync
	@echo "Production dependencies installed"

## Install production and test dependencies (uv sync --extra test)
.PHONY: install-dev
install-dev:
	@echo "Syncing all dependencies (including test) with uv..."
	$(UV) sync --extra test
	@echo "All dependencies installed"

## Run all tests
.PHONY: test
test: install-dev
	@echo "Running tests..."
	$(UV_RUN) pytest tests/ -v

## Run tests with verbose output
.PHONY: test-verbose
test-verbose: install-dev
	@echo "Running tests with verbose output..."
	$(UV_RUN) pytest tests/ -vv

## Run tests with coverage report
.PHONY: test-coverage
test-coverage: install-dev
	@echo "Running tests with coverage..."
	$(UV_RUN) pytest --cov=asitop --cov-report=term-missing tests/

## Generate HTML coverage report
.PHONY: coverage-html
coverage-html: install-dev
	@echo "Generating HTML coverage report..."
	$(UV_RUN) pytest --cov=asitop --cov-report=html tests/
	@echo "Coverage report generated at htmlcov/index.html"
	@echo "Open with: open htmlcov/index.html (macOS) or xdg-open htmlcov/index.html (Linux)"

## Generate terminal and HTML coverage reports
.PHONY: coverage-report
coverage-report: install-dev
	@echo "Generating coverage report..."
	$(UV_RUN) pytest --cov=asitop --cov-report=term --cov-report=html tests/
	@echo ""
	@echo "HTML report available at htmlcov/index.html"

## Run tests on file changes (requires pytest-watch)
.PHONY: test-watch
test-watch: install-dev
	@echo "Running tests in watch mode..."
	@echo "Install pytest-watch if not available: uv add --dev pytest-watch"
	@$(UV_RUN) ptw tests/ -- -v || \
		(echo "pytest-watch not installed. Installing..." && \
		$(UV) add --dev pytest-watch && \
		$(UV_RUN) ptw tests/ -- -v)

## Run asitop with sudo (password required)
.PHONY: run
run: install
	@echo "Running asitop with sudo (password required)..."
	@echo "Press Ctrl+C or 'q' to stop"
	@sudo $(UV_RUN) python -m asitop

## Run asitop with sudo and --extended powermetrics samplers
.PHONY: run-extended
run-extended: install
	@echo "Running asitop with sudo and --extended (password required)..."
	@echo "Press Ctrl+C or 'q' to stop"
	@sudo $(UV_RUN) python -m asitop --extended

## Run asitop without sudo (will prompt when needed)
.PHONY: run-nosudo
run-nosudo: install
	@echo "Running asitop (will prompt for sudo password)..."
	@echo "Press Ctrl+C or 'q' to stop"
	@$(UV_RUN) python -m asitop

## Run linter (Ruff)
.PHONY: lint
lint: install-dev
	@echo "Running Ruff linter..."
	$(UV_RUN) ruff check asitop/ tests/

## Auto-fix linting issues with Ruff
.PHONY: fix
fix: install-dev
	@echo "Auto-fixing linting issues with Ruff..."
	$(UV_RUN) ruff check --fix asitop/ tests/
	@echo "Linting issues fixed"

## Format code with Black
.PHONY: format
format: install-dev
	@echo "Formatting code with Black..."
	$(UV_RUN) black asitop/ tests/
	@echo "Code formatted"

## Check if code is formatted correctly (Black)
.PHONY: format-check
format-check: install-dev
	@echo "Checking code formatting with Black..."
	$(UV_RUN) black --check asitop/ tests/

## Run type checker (Mypy)
.PHONY: type-check
type-check: install-dev
	@echo "Running Mypy type checker..."
	$(UV_RUN) mypy --native-parser asitop/

## Run type checker (Pyright)
.PHONY: type-check-pyright
type-check-pyright: install-dev
	@echo "Running Pyright type checker..."
	$(UV_RUN) pyright asitop/

## Run all quality checks (lint, format-check, type-check, tests)
.PHONY: check
check: install-dev
	@echo "Running all quality checks..."
	@echo ""
	@echo "=== Running Ruff linter ==="
	@$(MAKE) lint
	@echo ""
	@echo "=== Checking code formatting with Black ==="
	@$(MAKE) format-check
	@echo ""
	@echo "=== Running Mypy type checker ==="
	@$(MAKE) type-check
	@echo ""
	@echo "=== Running Pyright type checker ==="
	@$(MAKE) type-check-pyright
	@echo ""
	@echo "=== Running tests with coverage ==="
	@$(MAKE) test-coverage
	@echo ""
	@echo "Quality checks complete"

## Remove all generated files (venv, build artifacts, caches)
.PHONY: clean
clean: clean-pyc clean-test
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Removing build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .eggs/
	@echo "Clean complete"

## Remove Python cache files
.PHONY: clean-pyc
clean-pyc:
	@echo "Removing Python cache files..."
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "Python cache cleaned"

## Remove test and coverage files
.PHONY: clean-test
clean-test:
	@echo "Removing test and coverage files..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf /tmp/asitop_powermetrics*
	@echo "Test files cleaned"

## Build distribution packages
.PHONY: dist
dist: install-dev clean
	@echo "Building distribution packages..."
	$(UV) build
	@echo "Distribution packages built in dist/"

## Upload to TestPyPI
.PHONY: upload-test
upload-test: dist
	@echo "Uploading to TestPyPI..."
	@$(UV) tool install twine 2>/dev/null || true
	$(UV) tool run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

## Upload to PyPI (interactive confirmation)
.PHONY: upload
upload: dist
	@echo "Uploading to PyPI..."
	@echo "WARNING: This will upload to the production PyPI!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(UV) tool install twine 2>/dev/null || true; \
		$(UV) tool run twine upload dist/*; \
	else \
		echo "Upload cancelled"; \
	fi

## Run tests with coverage (CI mode, skip install)
.PHONY: ci-test
ci-test:
	@echo "Running tests with coverage (CI mode)..."
	$(UV_RUN) pytest --cov=asitop --cov-report=xml --cov-report=term-missing --cov-fail-under=85 -v

## Run quality checks (CI mode, skip install)
.PHONY: ci-quality
ci-quality:
	@echo "Running quality checks (CI mode)..."
	@echo ""
	@echo "=== Running Ruff linter ==="
	$(UV_RUN) ruff check asitop/ tests/
	@echo ""
	@echo "=== Checking Black formatting ==="
	$(UV_RUN) black --check asitop/ tests/
	@echo ""
	@echo "=== Running Mypy type checker ==="
	$(UV_RUN) mypy --native-parser asitop/
	@echo ""
	@echo "=== Running Pyright type checker ==="
	$(UV_RUN) pyright asitop/
	@echo ""
	@echo "Quality checks complete"

## Run all CI checks (quality + test)
.PHONY: ci-check
ci-check: ci-quality ci-test
	@echo ""
	@echo "All CI checks passed successfully"
