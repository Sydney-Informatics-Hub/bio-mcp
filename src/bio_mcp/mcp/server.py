import difflib
import json
from typing import List, Dict

from mcp.server.fastmcp import FastMCP

from bio_mcp.cache.load import load_cache
from bio_mcp.globals import CACHE_PATH
from pathlib import Path

# Initialize FastMCP server
mcp = FastMCP("bio-mcp")

def fuzzy_search_entries(entry_names: List[str], cache_path: Path = CACHE_PATH) -> Dict[str, object]:
    """
    Fuzzy match a list of entry names against the cached tool names
    """
    cache = load_cache(cache_path)
    known_list = cache["tool_names"]
    known_lower_list = [name.lower() for name in known_list]
    known_lower = set(known_lower_list)
    entries = cache.get("entries", [])
    found = []
    missing = []
    suggestions: Dict[str, List[str]] = {}
    for name in entry_names:
        name_lower = name.lower()
        if name_lower in known_lower:
            found.append(name)
        else:
            # Fuzzy match to provide suggestions, e.g. typos, close matches
            missing.append(name)
            matches = difflib.get_close_matches(
                name_lower,
                known_lower_list,
                n=5,
                cutoff=0.7,
            )
            if matches:
                suggestions[name] = matches

    found_lower = {name.lower() for name in found}
    matched_entries = [
        entry for entry in entries if entry.get("tool_name", "").lower() in found_lower
    ]

    return {
        "found": found,
        "missing": missing,
        "count": len(entry_names),
        "suggestions": suggestions,
        "entries": matched_entries,
    }

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
