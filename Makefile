# Makefile for asitop
# Provides commands for testing, running, and managing the project
# Uses uv for dependency management

.PHONY: help sync install install-dev test test-verbose test-coverage \
        test-watch clean clean-pyc clean-test run lint format check \
        coverage-html coverage-report dist upload-test upload

# uv configuration
UV := uv
UV_RUN := $(UV) run
VENV := .venv

# Default target
help:
	@echo "asitop Makefile commands:"
	@echo ""
	@echo "Setup commands:"
	@echo "  make sync           Sync all dependencies (uv sync)"
	@echo "  make install        Install production dependencies only"
	@echo "  make install-dev    Install production and test dependencies"
	@echo ""
	@echo "Testing commands:"
	@echo "  make test           Run all tests"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo "  make test-coverage  Run tests with coverage report"
	@echo "  make coverage-html  Generate HTML coverage report"
	@echo "  make test-watch     Run tests on file changes (requires pytest-watch)"
	@echo ""
	@echo "Running commands:"
	@echo "  make run            Run asitop with sudo (requires password)"
	@echo "  make run-nosudo     Run asitop without sudo (will prompt later)"
	@echo ""
	@echo "Code quality commands:"
	@echo "  make lint           Run linters (flake8, pylint)"
	@echo "  make format         Format code with autopep8"
	@echo "  make check          Run all quality checks"
	@echo ""
	@echo "Cleanup commands:"
	@echo "  make clean          Remove all generated files"
	@echo "  make clean-pyc      Remove Python cache files"
	@echo "  make clean-test     Remove test and coverage files"
	@echo ""
	@echo "Distribution commands:"
	@echo "  make dist           Build distribution packages"
	@echo "  make upload-test    Upload to TestPyPI"
	@echo "  make upload         Upload to PyPI"

# Sync all dependencies (production only)
sync:
	@echo "Syncing production dependencies with uv..."
	$(UV) sync --no-dev
	@echo "Production dependencies synced"

# Install production dependencies (same as sync)
install: sync
	@echo "Production dependencies installed"

# Install development and test dependencies
install-dev:
	@echo "Syncing all dependencies (including test) with uv..."
	$(UV) sync --extra test
	@echo "All dependencies installed"

# Run all tests
test: install-dev
	@echo "Running tests..."
	$(UV_RUN) pytest tests/ -v

# Run tests with verbose output
test-verbose: install-dev
	@echo "Running tests with verbose output..."
	$(UV_RUN) pytest tests/ -vv

# Run tests with coverage
test-coverage: install-dev
	@echo "Running tests with coverage..."
	$(UV_RUN) pytest --cov=asitop --cov-report=term-missing tests/

# Generate HTML coverage report
coverage-html: install-dev
	@echo "Generating HTML coverage report..."
	$(UV_RUN) pytest --cov=asitop --cov-report=html tests/
	@echo "Coverage report generated at htmlcov/index.html"
	@echo "Open with: open htmlcov/index.html (macOS) or xdg-open htmlcov/index.html (Linux)"

# Generate terminal coverage report
coverage-report: install-dev
	@echo "Generating coverage report..."
	$(UV_RUN) pytest --cov=asitop --cov-report=term --cov-report=html tests/
	@echo ""
	@echo "HTML report available at htmlcov/index.html"

# Run tests on file changes (requires pytest-watch)
test-watch: install-dev
	@echo "Running tests in watch mode..."
	@echo "Install pytest-watch if not available: uv add --dev pytest-watch"
	@$(UV_RUN) ptw tests/ -- -v || \
		(echo "pytest-watch not installed. Installing..." && \
		$(UV) add --dev pytest-watch && \
		$(UV_RUN) ptw tests/ -- -v)

# Run asitop with sudo
run: install
	@echo "Running asitop with sudo (password required)..."
	@echo "Press Ctrl+C to stop"
	@sudo $(UV_RUN) asitop

# Run asitop without sudo (will prompt when needed)
run-nosudo: install
	@echo "Running asitop (will prompt for sudo password)..."
	@echo "Press Ctrl+C to stop"
	@$(UV_RUN) asitop

# Run linters
lint: install-dev
	@echo "Running flake8..."
	-$(UV_RUN) flake8 asitop --count --select=E9,F63,F7,F82 --show-source --statistics
	-$(UV_RUN) flake8 asitop --count --max-line-length=79 --statistics
	@echo ""
	@echo "Running pylint..."
	-$(UV_RUN) pylint asitop --max-line-length=79

# Format code
format: install-dev
	@echo "Formatting code with autopep8..."
	@$(UV) add --dev autopep8 2>/dev/null || true
	-$(UV_RUN) autopep8 --in-place --aggressive --aggressive -r asitop/
	@echo "Code formatted"

# Run all quality checks
check: install-dev
	@echo "Running all quality checks..."
	@echo ""
	@echo "=== Running tests ==="
	@$(MAKE) test-coverage
	@echo ""
	@echo "=== Running linters ==="
	@$(MAKE) lint
	@echo ""
	@echo "Quality checks complete"

# Clean all generated files
clean: clean-pyc clean-test
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Removing build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .eggs/
	@echo "Clean complete"

# Clean Python cache files
clean-pyc:
	@echo "Removing Python cache files..."
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "Python cache cleaned"

# Clean test and coverage files
clean-test:
	@echo "Removing test and coverage files..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf /tmp/asitop_powermetrics*
	@echo "Test files cleaned"

# Build distribution packages
dist: install-dev clean
	@echo "Building distribution packages..."
	$(UV) build
	@echo "Distribution packages built in dist/"

# Upload to TestPyPI
upload-test: dist
	@echo "Uploading to TestPyPI..."
	@$(UV) tool install twine 2>/dev/null || true
	$(UV) tool run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Upload to PyPI
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
