#!/bin/bash
# Script to run asitop from virtual environment with sudo
# This ensures the virtual environment is activated before running

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating..."
    make -C "$SCRIPT_DIR" venv install
fi

# Check if dependencies are installed
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment Python not found"
    exit 1
fi

echo "Running asitop with sudo..."
echo "You may be prompted for your password"
echo "Press Ctrl+C to stop asitop"
echo ""

# Run asitop with sudo, using the virtual environment Python
sudo "$VENV_PYTHON" -m asitop.asitop "$@"
