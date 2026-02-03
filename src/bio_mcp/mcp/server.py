import difflib
from typing import List, Dict, Any, Optional

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
    tool_names: str | List[str],
    registry: dict,
    max_matches: int = 2,
    cutoff: float = 0.7,
) -> list[object]:
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
    results: List[Any] = []
    available_names = list(registry.keys())

    if isinstance(tool_names, str):
        tool_names = [tool_names]

    for tool in tool_names:
        # Exact match first 
        if tool in available_names:
            match = registry.get(tool)
            results.append(match)
            continue

        # Fuzzy match if no exact matches are found
        matches = difflib.get_close_matches(tool, available_names, n=max_matches, cutoff=cutoff
        )

        for name in matches:
            results.append(registry[name])

    # Return empty list if no matches
    return results

def describe_container(
    cvmfs_registry: Dict[str, List[Dict[str, Any]]],
    biotools_registry: Dict[str, Dict[str, Any]],
    tool_names: List[str] | str,
) -> List[Dict[str, Any]]:
    """
    Describe containers by joining CVMFS inventory with bio.tools metadata

    Args:
       cvmfs_registry:
           Mapping of tool_name -> list of CVMFS container entries
       biotools_registry:
           Mapping of tool id -> bio.tools metadata record
       container_names:
           List of container (tool) names to describe

    Returns:
        List of container descriptions with metadata
    """
    results: List[Dict[str, Any]] = []

    if isinstance(tool_names, str):
        tool_names = [tool_names]

    for tool in tool_names:
        cvmfs_versions = cvmfs_registry.get(tool)

        metadata: Optional[Dict[str, Any]] = biotools_registry.get(tool)

        results.append(
            {
                "container": tool,
                "versions": cvmfs_versions,
                "metadata": metadata,
            }
        )

    return results

@mcp.tool()
def search_containers_tool(tool_names: str) -> List[Any]:
    """
    Search available containers on the CVMFS by name.

    Returns all container registroy entries, such as versions, tags and the path on the CVMFS
    """
    return search_containers(tool_names = tool_names, registry = cvmfs_galaxy_simg)

@mcp.tool()
def describe_container_tool(tool_names: str) -> List[Any]:
    """
    Describe available containers by joining CVMFS inventory with bio.tools metadata.

    - Returns all available versions per container
    - Metadata is included when available, otherwise null
    - No inference or fuzzy matching is performed
    """
    return describe_container(cvmfs_registry = cvmfs_galaxy_simg, biotools_registry = biotools, tool_names = tool_names)

if __name__ == "__main__":
    # Initialise and run the server
    mcp.run(transport="stdio")
