#!/bin/bash
# Setup script for BioContainer Finder MCP

set -e

echo "=== BioContainer Finder MCP Setup ==="
echo

# Check Python version
echo "Checking Python version..."
python3 --version

# Install dependencies
echo "Installing dependencies..."
pip install --break-system-packages -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x biocontainer_server.py
chmod +x biocontainer_client.py

echo
echo "✓ Setup complete!"
echo
echo "Usage examples:"
echo "  ./biocontainer_client.py find fastqc"
echo "  ./biocontainer_client.py search 'quality control'"
echo "  ./biocontainer_client.py interactive"
echo
