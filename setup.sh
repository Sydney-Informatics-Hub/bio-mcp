#!/bin/bash
# Setup script for BioFinder MCP

set -e

echo "=== BioFinder MCP Setup ==="
echo

# Check Python version, and pip availability
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but not installed." >&2
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "Error: Python 3.8+ is required." >&2
  exit 1
fi

if ! command -v pip >/dev/null 2>&1; then
  echo "Error: pip is required but not installed." >&2
  exit 1
fi

echo "Checking Python version..."
python3 --version

# Install dependencies

echo "Installing dependencies..."
pip install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x biofinder_server.py
chmod +x biofinder_client.py
chmod +x biofinder

echo
echo "✓ Setup complete!"
echo
echo "Usage examples:"
echo "  ./biofinder # interactive mode"
echo "  ./biofinder_client.py find fastqc"
echo "  ./biofinder_client.py search 'quality control'"
echo "  ./biofinder_client.py interactive"
echo
