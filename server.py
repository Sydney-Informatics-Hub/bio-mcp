from typing import Any
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP

# Constants
CVMFS_SINGULARITY_DATA = Path("/cvmfs/data.galaxyproject.org")
CVMFS_SINGULARITY_GALAXY = Path("/cvmfs/singularity.galaxyproject.org")

# Initialize FastMCP server
mcp = FastMCP("bio-mcp")

@mcp.tool()
def list_containers() -> list[dict]:
    """
    List canonical container images from the CVMFS container depot on Galaxy.
    """
    containers = []

    for entry in CVMFS_ALL.iterdir():
        stat = entry.stat()
        containers.append({
            "name": entry.name,
            "path": str(entry),
            "size_bytes": stat.st_size,
            "mtime": st.st_mtime,
            "kind": "executable",
        })

    return containers

if __name__ == "__main__":
    # Initialise and run the server
    mcp.run(transport="stdio")