#!/usr/bin/env python3
"""
BioContainer Finder MCP Server

This MCP server provides bioinformatics container discovery for CVMFS-hosted
Singularity containers, helping users find and use containerized tools.
"""

import json
import gzip
import yaml
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import re

# MCP SDK imports
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio


# Data paths
DATA_DIR = Path("/mnt/user-data/uploads")
METADATA_FILE = DATA_DIR / "toolfinder_meta.yaml"
SINGULARITY_CACHE_FILE = DATA_DIR / "galaxy_singularity_cache_json.gz"


class BioContainerIndex:
    """Index of container metadata and singularity images."""
    
    def __init__(self):
        self.metadata: List[Dict[str, Any]] = []
        self.singularity_entries: List[Dict[str, Any]] = []
        self.tool_to_containers: Dict[str, List[Dict]] = defaultdict(list)
        self.container_index: Dict[str, List[Dict]] = defaultdict(list)
        self.cache_info: Dict[str, Any] = {}
        
    def load_data(self):
        """Load metadata and singularity cache."""
        # Load metadata YAML
        print(f"Loading metadata from {METADATA_FILE}...")
        with open(METADATA_FILE, 'r') as f:
            self.metadata = yaml.safe_load(f)
        print(f"Loaded {len(self.metadata)} tool metadata entries")
        
        # Load singularity cache
        print(f"Loading singularity cache from {SINGULARITY_CACHE_FILE}...")
        with gzip.open(SINGULARITY_CACHE_FILE, 'rt') as f:
            cache_data = json.load(f)
            self.cache_info = {
                'generated_at': cache_data['generated_at'],
                'cvmfs_root': cache_data['cvmfs_root'],
                'entry_count': cache_data['entry_count']
            }
            self.singularity_entries = cache_data['entries']
        print(f"Loaded {len(self.singularity_entries)} singularity entries")
        
        # Build indexes
        self._build_indexes()
        
    def _build_indexes(self):
        """Build search indexes."""
        # Index containers by tool name
        for entry in self.singularity_entries:
            tool_name = entry['tool_name'].lower()
            self.container_index[tool_name].append(entry)
            
    def _parse_version(self, tag: str) -> Tuple[List[int], str]:
        """Parse version from tag for sorting."""
        # Extract version number (e.g., "0.12.1" from "0.12.1--hdfd78af_1")
        match = re.match(r'^(\d+(?:\.\d+)*)', tag)
        if match:
            version_str = match.group(1)
            version_parts = [int(x) for x in version_str.split('.')]
            return (version_parts, tag)
        return ([0], tag)
        
    def search_tool(self, query: str) -> Dict[str, Any]:
        """
        Search for a tool and return metadata + available containers.
        
        Returns structured data about the tool including:
        - Tool metadata (description, homepage, publications)
        - Available containers with versions
        - Most recent version
        - Usage examples
        """
        query_lower = query.lower()
        
        # Find in metadata
        tool_meta = None
        for entry in self.metadata:
            entry_id = entry.get('id', '') or ''
            entry_name = entry.get('name', '') or ''
            entry_biotools = entry.get('biotools', '') or ''
            entry_biocontainers = entry.get('biocontainers', '') or ''
            
            if (entry_id.lower() == query_lower or 
                entry_name.lower() == query_lower or
                entry_biotools.lower() == query_lower or
                entry_biocontainers.lower() == query_lower):
                tool_meta = entry
                break
        
        # Search for partial matches if exact match not found
        if not tool_meta:
            for entry in self.metadata:
                entry_id = entry.get('id', '').lower()
                if query_lower in entry_id or entry_id in query_lower:
                    tool_meta = entry
                    break
        
        # Get containers - try exact match first, then variations
        containers = []
        search_variations = [
            query_lower,
            query_lower.replace('-', '_'),
            query_lower.replace('_', '-'),
        ]
        
        # Add biocontainers name if available
        if tool_meta and tool_meta.get('biocontainers'):
            search_variations.append(tool_meta['biocontainers'].lower())
        
        for variation in search_variations:
            if variation in self.container_index:
                containers = self.container_index[variation]
                break
        
        # Sort containers by version (newest first)
        if containers:
            containers_sorted = sorted(
                containers,
                key=lambda x: self._parse_version(x['tag']),
                reverse=True
            )
        else:
            containers_sorted = []
        
        return {
            'query': query,
            'metadata': tool_meta,
            'containers': containers_sorted,
            'container_count': len(containers_sorted)
        }
    
    def search_by_description(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search tools by description or functionality.
        Useful for queries like "What can I use to generate count data?"
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        results = []
        
        for entry in self.metadata:
            score = 0
            
            # Search in description
            description = (entry.get('description') or '').lower()
            if description:
                desc_terms = set(description.split())
                # Count matching terms
                matches = query_terms.intersection(desc_terms)
                score += len(matches) * 2
                
                # Boost if query is a substring of description
                if query_lower in description:
                    score += 5
            
            # Search in EDAM operations (what the tool does)
            operations = entry.get('edam-operations', []) or []
            for op in operations:
                if op and query_lower in op.lower():
                    score += 3
            
            # Search in EDAM topics
            topics = entry.get('edam-topics', []) or []
            for topic in topics:
                if topic and query_lower in topic.lower():
                    score += 2
            
            # Search in name and ID
            name = (entry.get('name') or '').lower()
            if query_lower in name:
                score += 4
            
            entry_id = (entry.get('id') or '').lower()
            if query_lower in entry_id:
                score += 4
                
            if score > 0:
                results.append({
                    'tool': entry,
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def list_all_tools(self, limit: int = 50) -> List[str]:
        """List all available tool names."""
        tools = set()
        
        # From metadata
        for entry in self.metadata:
            if entry.get('id'):
                tools.add(entry['id'])
        
        # From containers
        for tool_name in self.container_index.keys():
            tools.add(tool_name)
        
        return sorted(list(tools))[:limit]


# Initialize the index
index = BioContainerIndex()

# Create MCP server
app = Server("biocontainer-finder")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (the data sources)."""
    return [
        Resource(
            uri="biocontainer://cache-info",
            name="CVMFS Cache Information",
            mimeType="application/json",
            description="Information about the Singularity container cache"
        ),
        Resource(
            uri="biocontainer://tool-list",
            name="Available Tools List",
            mimeType="text/plain",
            description="List of all available bioinformatics tools"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    if uri == "biocontainer://cache-info":
        return json.dumps(index.cache_info, indent=2)
    elif uri == "biocontainer://tool-list":
        tools = index.list_all_tools(limit=1000)
        return "\n".join(tools)
    else:
        raise ValueError(f"Unknown resource: {uri}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="find_tool",
            description=(
                "Find a bioinformatics tool by name and get container information. "
                "Use this when the user asks 'Where can I find X?' or 'How do I use X?'. "
                "Returns the tool's metadata, available container versions, and usage examples."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool to search for (e.g., 'fastqc', 'iqtree', 'samtools')"
                    }
                },
                "required": ["tool_name"]
            }
        ),
        Tool(
            name="search_by_function",
            description=(
                "Search for tools by their function or description. "
                "Use this when the user asks 'What can I use to do X?' or describes a task. "
                "Examples: 'count data', 'quality control', 'alignment', 'assembly'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of what the user wants to do"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["description"]
            }
        ),
        Tool(
            name="get_container_versions",
            description=(
                "Get all available versions of a specific container. "
                "Returns a sorted list of versions with their CVMFS paths."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool"
                    }
                },
                "required": ["tool_name"]
            }
        ),
        Tool(
            name="list_available_tools",
            description=(
                "List all available bioinformatics tools. "
                "Use this when the user asks 'What tools are available?'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tools to list",
                        "default": 50
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "find_tool":
        tool_name = arguments["tool_name"]
        result = index.search_tool(tool_name)
        
        # Format response
        response_parts = []
        
        # Tool information
        if result['metadata']:
            meta = result['metadata']
            response_parts.append(f"# {meta.get('name', tool_name.upper())}\n")
            
            if meta.get('description'):
                response_parts.append(f"**Description:** {meta['description']}\n")
            
            if meta.get('homepage'):
                response_parts.append(f"**Homepage:** {meta['homepage']}\n")
            
            if meta.get('license'):
                response_parts.append(f"**License:** {meta['license']}\n")
            
            # Operations
            if meta.get('edam-operations'):
                response_parts.append(f"\n**Operations:** {', '.join(meta['edam-operations'])}\n")
        else:
            response_parts.append(f"# {tool_name}\n")
            response_parts.append("(No metadata available for this tool)\n")
        
        # Container information
        if result['containers']:
            response_parts.append(f"\n## Available Containers ({result['container_count']} versions)\n")
            
            # Most recent version
            latest = result['containers'][0]
            response_parts.append(f"\n### Most Recent Version: {latest['tag']}\n")
            response_parts.append(f"**Path:** `{latest['path']}`\n")
            response_parts.append(f"**Size:** {latest['size_bytes'] / (1024**2):.1f} MB\n")
            
            # Usage example
            response_parts.append(f"\n### Usage Example:\n")
            response_parts.append(f"```bash\n")
            response_parts.append(f"# Execute a command in the container\n")
            response_parts.append(f"singularity exec {latest['path']} {tool_name} --help\n\n")
            response_parts.append(f"# Run interactively\n")
            response_parts.append(f"singularity shell {latest['path']}\n")
            response_parts.append(f"```\n")
            
            # Show all versions
            if len(result['containers']) > 1:
                response_parts.append(f"\n### All Available Versions:\n")
                for container in result['containers'][:10]:  # Show top 10
                    response_parts.append(
                        f"- **{container['tag']}** - `{container['path']}`\n"
                    )
                if len(result['containers']) > 10:
                    response_parts.append(f"\n... and {len(result['containers']) - 10} more versions\n")
        else:
            response_parts.append("\n⚠️ **No containers found in CVMFS for this tool.**\n")
            response_parts.append("The tool may be available through other means or under a different name.\n")
        
        return [TextContent(type="text", text="".join(response_parts))]
    
    elif name == "search_by_function":
        description = arguments["description"]
        limit = arguments.get("limit", 10)
        
        results = index.search_by_description(description, limit)
        
        if not results:
            return [TextContent(
                type="text",
                text=f"No tools found matching '{description}'. Try different keywords or browse available tools."
            )]
        
        response_parts = [f"# Tools for: {description}\n\n"]
        response_parts.append(f"Found {len(results)} matching tools:\n\n")
        
        for i, result_item in enumerate(results, 1):
            tool = result_item['tool']
            score = result_item['score']
            
            response_parts.append(f"## {i}. {tool.get('name', tool.get('id', 'Unknown'))}\n")
            response_parts.append(f"**ID:** {tool.get('id', 'N/A')}\n")
            
            if tool.get('description'):
                response_parts.append(f"**Description:** {tool['description']}\n")
            
            if tool.get('edam-operations'):
                response_parts.append(f"**Operations:** {', '.join(tool['edam-operations'])}\n")
            
            # Check if containers available
            tool_search = index.search_tool(tool.get('id', ''))
            if tool_search['containers']:
                latest = tool_search['containers'][0]
                response_parts.append(f"**Latest Container:** `{latest['tag']}`\n")
                response_parts.append(f"**Quick Start:** `singularity exec {latest['path']} {tool.get('id', '')} --help`\n")
            
            response_parts.append("\n")
        
        return [TextContent(type="text", text="".join(response_parts))]
    
    elif name == "get_container_versions":
        tool_name = arguments["tool_name"]
        result = index.search_tool(tool_name)
        
        if not result['containers']:
            return [TextContent(
                type="text",
                text=f"No containers found for '{tool_name}'"
            )]
        
        response_parts = [f"# Container Versions for {tool_name}\n\n"]
        response_parts.append(f"Total versions: {len(result['containers'])}\n\n")
        
        for container in result['containers']:
            response_parts.append(f"## Version {container['tag']}\n")
            response_parts.append(f"- **Path:** `{container['path']}`\n")
            response_parts.append(f"- **Size:** {container['size_bytes'] / (1024**2):.1f} MB\n")
            response_parts.append(f"- **Modified:** {datetime.fromtimestamp(container['mtime']).strftime('%Y-%m-%d')}\n\n")
        
        return [TextContent(type="text", text="".join(response_parts))]
    
    elif name == "list_available_tools":
        limit = arguments.get("limit", 50)
        tools = index.list_all_tools(limit)
        
        response = f"# Available Bioinformatics Tools ({len(tools)} shown)\n\n"
        response += "\n".join(f"- {tool}" for tool in tools)
        
        return [TextContent(type="text", text=response)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    # Load data
    print("Initializing BioContainer Finder MCP Server...")
    index.load_data()
    print("Ready to serve requests!")
    
    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
