# Developer instructions

When making changes to the python scripts, install the project in editable mode

```bash
# in the repo root dir
uv pip install -e .
```

Code linting, formatting, and sort imports.

```bash
ruff format . && ruff check . --fix
```

To update the json/yaml file caches, edit the path in `server.py`:

```python
# Read in container and metadata snapshots when server starts
JSON_PATH = Path("/home/ubuntu/bio-mcp/data/scrnaseq_galaxy_cvmfs.json")
YAML_PATH = Path("/home/ubuntu/bio-mcp/data/scrnaseq_biotools.yaml")
```

