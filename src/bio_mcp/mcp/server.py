import difflib
import json
from typing import List, Dict

from mcp.server.fastmcp import FastMCP

from bio_mcp.cache.load import load_galaxy_singularity, load_biotools
from pathlib import Path

# Read in container and metadata snapshots when server starts
JSON_PATH = Path("/home/ubuntu/bio-mcp/data/scrnaseq_galaxy_cvmfs.json")
YAML_PATH = Path("/home/ubuntu/bio-mcp/data/scrnaseq_biotools.yaml")

cvmfs_galaxy_simg = load_galaxy_singularity(JSON_PATH)
biotools = load_biotools(YAML_PATH)

# Initialize FastMCP server
mcp = FastMCP("bio-mcp")

def search_containers(
    tool_name: str,
    registry: dict,
    max_matches: int = 2,
    cutoff: float = 0.7,
) -> list[object] | dict | None:
    """
    Search for containers available in the CVMFS registry by name.
    
    Args:
        registry: CVMFS container registry, keyed by lowercased container name
        tool_name: Tool name to search in registry
        max_matches: Max number of fuzzy matches to return
        cutoff: Similarity threshold for fuzzy matching

    Returns:
        List of full registry entries (one per matched container name)
    """
    # Exact match first 
    available_names = list(registry.keys())
    if tool_name in available_names:
        return registry.get(tool_name)
    
    # Fuzzy match if no exact matches are found
    matches = difflib.get_close_matches(tool_name, available_names, n=max_matches, cutoff=cutoff
    )

    if matches:
        return [registry[name] for name in matches]

    # Return empty list of nothing found
    return [None]

@mcp.tool()
def search_entry_name(entry_names: List[str]) -> str:
    """
    List results from match
    """
    matched_results = fuzzy_search_entries(entry_names)
    return json.dumps(matched_results)

if __name__ == "__main__":
    # Initialise and run the server
    mcp.run(transport="stdio")
