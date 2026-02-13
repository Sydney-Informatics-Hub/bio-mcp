#!/bin/bash
# Setup script for BioFinder MCP
set -e

echo "=== BioFinder MCP Setup ==="
echo

# Check Python 3.8+
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but not installed." >&2; exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "Error: Python 3.8+ is required." >&2; exit 1
fi
if ! command -v pip >/dev/null 2>&1; then
  echo "Error: pip is required but not installed." >&2; exit 1
fi

echo "Python version: $(python3 --version)"
echo

# Install dependencies
echo "Installing dependencies..."
echo
echo "NOTE: sentence-transformers pulls in PyTorch (~1-2 GB on first install)."
echo "   This is a one-time download. Subsequent installs use the local cache."
echo "   If you want a lightweight install without semantic search, edit"
echo "   requirements.txt and remove the sentence-transformers line first."
echo
pip install -r requirements.txt

# Make scripts executable
chmod +x biofinder_server.py biofinder_client.py biofinder

echo
echo "Dependencies installed."
echo

# Pre-download and cache the embedding models so the first search is not slow.
# Models are stored in ~/.cache/huggingface/hub by default.
echo "Pre-downloading embedding models (one-time, requires internet)..."
echo "  - all-MiniLM-L6-v2      (~22 MB, general-purpose)"
echo "  - BiomedNLP-BiomedBERT  (~440 MB, biomedical domain)"
echo
python3 - <<'EOF'
import sys
try:
    from sentence_transformers import SentenceTransformer
    print("  Downloading all-MiniLM-L6-v2 ...")
    SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("  all-MiniLM-L6-v2 ready")
    print("  Downloading BiomedNLP-BiomedBERT ...")
    SentenceTransformer("microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-abstracted")
    print("  BiomedNLP-BiomedBERT ready")
except ImportError:
    print("  sentence-transformers not available -- search will use keyword fallback")
    sys.exit(0)
except Exception as e:
    print(f"  Model download failed: {e}")
    print("  Models will be downloaded on first use instead.")
    sys.exit(0)
EOF

echo
echo "Setup complete!"
echo
echo "Usage:"
echo "  ./biofinder                               # interactive mode"
echo "  ./biofinder_client.py find fastqc         # find a tool"
echo "  ./biofinder_client.py search 'RNA align'  # semantic search"
echo
echo "On first search, BioFinder pre-computes embeddings for all 714 tools"
echo "and caches them to disk. This takes ~10-30 s on CPU, once only."
echo
