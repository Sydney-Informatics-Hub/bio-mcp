from typing import List, Dict, Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from bio_mcp.globals import CACHE_PATH
from bio_mcp.cache.load import load_cache
import logging

# Initialize FastMCP server
mcp = FastMCP("bio-mcp")

@mcp.tool()
def get_entry_cache() -> List[str]:
    """
    List available entry names (e.g. containers, data) from cache.
    """
    cache = load_cache(CACHE_PATH)
    return sorted(cache["tool_names"])

if __name__ == "__main__":
# Initialise and run the server
    mcp.run(transport="stdio")