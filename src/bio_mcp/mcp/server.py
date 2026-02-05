import difflib
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from bio_mcp.cache.load import load_biotools, load_galaxy_singularity

# Read in container and metadata snapshots when server starts
JSON_PATH = Path("/home/ubuntu/bio-mcp/data/galaxy_singularity_cache.json")
YAML_PATH = Path("/home/ubuntu/bio-mcp/data/toolfinder_meta.yaml")

cvmfs_galaxy_simg = load_galaxy_singularity(JSON_PATH)
biotools = load_biotools(YAML_PATH)

# Initialize FastMCP server
mcp = FastMCP("bio-mcp")


def _search_containers(
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
        matches = difflib.get_close_matches(
            tool, available_names, n=max_matches, cutoff=cutoff
        )

        for name in matches:
            results.append(registry[name])

    # Return empty list if no matches
    return results


def _describe_container(
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


def recommend_containers(keywords: List[str], biotools_registry: dict[Any]):
    return


@mcp.tool()
def search_containers(tool_names: str) -> List[Any]:
    """
    Search for existing containers in the Galaxy container registry by name.

    Use this for fast existence/version lookups when you only need registry data
    (versions, tags, paths). This does not contain metadata, perform
    inference, or expand results beyond exact names. For metadata-enriched
    results, use describe_container.
    """
    return _search_containers(tool_names=tool_names, registry=cvmfs_galaxy_simg)


@mcp.tool()
def describe_container(tool_names: str) -> List[Any]:
    """
    Describe available containers by exact name(s) and enrich with bio.tools metadata.

    Use this when you need richer context (bio.tools metadata) in addition to
    registry details (versions, tags, paths). This joins CVMFS inventory with
    bio.tools; it does not infer, fuzzy-match, or recommend. For fast existence/
    version checks without metadata, use search_containers. Future tools may
    perform discovery or recommendations; this one is exact-name only.
    """
    return _describe_container(
        cvmfs_registry=cvmfs_galaxy_simg,
        biotools_registry=biotools,
        tool_names=tool_names,
    )


if __name__ == "__main__":
    # Initialise and run the server
    mcp.run(transport="stdio")
