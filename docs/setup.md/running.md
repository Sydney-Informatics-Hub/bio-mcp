## How to run the MCP client

```bash
# Run CLI client
uv run python -m bio_mcp.mcp.client src/bio_mcp/mcp/server.py
```

## How to build a cache

Temporary implementation for Galaxy containers only. This outputs the `data/galaxy_singularity_cache.json`.

```bash
# ensure probes are accessible and mounted on the VM
cvmfs_config probe

# build cache
uv run python -m bio_mcp.cache.build_cache
```

json is compressed for GitHub upload.

```bash
gzip galaxy_singularity_cache.json
```

To reuse, run

```bash
gzip -d galaxy_singualrity_cache.json.gz
```