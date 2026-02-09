#!/usr/bin/env python3
"""
Test script for BioFinder MCP

Demonstrates the functionality without needing the full MCP client-server setup.
"""

import sys
import json
import gzip
import yaml
from pathlib import Path
from collections import defaultdict
import re


# Data paths
DATA_DIR = Path(__file__).resolve().parent
METADATA_FILE = DATA_DIR / "toolfinder_meta.yaml"
SINGULARITY_CACHE_FILE = DATA_DIR / "galaxy_singularity_cache.json.gz"


class BioContainerIndex:
    """Index of container metadata and singularity images."""
    
    def __init__(self):
        self.metadata = []
        self.singularity_entries = []
        self.container_index = defaultdict(list)
        self.cache_info = {}
        
    def load_data(self):
        """Load metadata and singularity cache."""
        print(f"Loading metadata from {METADATA_FILE}...")
        with open(METADATA_FILE, 'r') as f:
            self.metadata = yaml.safe_load(f)
        print(f"✓ Loaded {len(self.metadata)} tool metadata entries")
        
        print(f"Loading singularity cache from {SINGULARITY_CACHE_FILE}...")
        with gzip.open(SINGULARITY_CACHE_FILE, 'rt') as f:
            cache_data = json.load(f)
            self.cache_info = {
                'generated_at': cache_data['generated_at'],
                'cvmfs_root': cache_data['cvmfs_root'],
                'entry_count': cache_data['entry_count']
            }
            self.singularity_entries = cache_data['entries']
        print(f"✓ Loaded {len(self.singularity_entries)} singularity entries")
        
        self._build_indexes()
        
    def _build_indexes(self):
        """Build search indexes."""
        for entry in self.singularity_entries:
            tool_name = entry['tool_name'].lower()
            self.container_index[tool_name].append(entry)
            
    def _parse_version(self, tag):
        """Parse version from tag for sorting."""
        match = re.match(r'^(\d+(?:\.\d+)*)', tag)
        if match:
            version_str = match.group(1)
            version_parts = [int(x) for x in version_str.split('.')]
            return (version_parts, tag)
        return ([0], tag)
        
    def search_tool(self, query):
        """Search for a tool."""
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
        
        # Get containers
        containers = []
        search_variations = [
            query_lower,
            query_lower.replace('-', '_'),
            query_lower.replace('_', '-'),
        ]
        
        if tool_meta and tool_meta.get('biocontainers'):
            search_variations.append(tool_meta['biocontainers'].lower())
        
        for variation in search_variations:
            if variation in self.container_index:
                containers = self.container_index[variation]
                break
        
        # Sort containers by version
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
    
    def search_by_description(self, query, limit=10):
        """Search tools by description."""
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        results = []
        
        for entry in self.metadata:
            score = 0
            
            description = (entry.get('description') or '').lower()
            if description:
                desc_terms = set(description.split())
                matches = query_terms.intersection(desc_terms)
                score += len(matches) * 2
                
                if query_lower in description:
                    score += 5
            
            operations = entry.get('edam-operations', []) or []
            for op in operations:
                if op and query_lower in op.lower():
                    score += 3
            
            topics = entry.get('edam-topics', []) or []
            for topic in topics:
                if topic and query_lower in topic.lower():
                    score += 2
            
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
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]


def demo_find_tool(index, tool_name):
    """Demo: Find a specific tool."""
    result = index.search_tool(tool_name)
    
    response_parts = []

    if result['metadata']:
        meta = result['metadata']

        response_parts.append(f"\n{'='*70}\n")
        response_parts.append(f"🧬 {meta.get('name', tool_name.upper())}\n")
        response_parts.append(f"{'='*70}\n\n")

        if meta.get('description'):
            response_parts.append("📝 Description:\n")
            response_parts.append(f"   {meta['description']}\n\n")

        if meta.get('homepage'):
            response_parts.append(f"🌐 Homepage: {meta['homepage']}\n")

        if meta.get('edam-operations'):
            response_parts.append(f"⚙️  Operations: {', '.join(meta['edam-operations'])}\n")
    else:
        response_parts.append(f"\n{'='*70}\n")
        response_parts.append(f"🧬 {tool_name.upper()}\n")
        response_parts.append(f"{'='*70}\n\n")
        response_parts.append("ℹ️  No metadata available for this tool\n")
    
    if result['containers']:
        response_parts.append(f"\n{'─'*70}\n")
        response_parts.append(f"📦 AVAILABLE CONTAINERS ({result['container_count']} versions)\n")
        response_parts.append(f"{'─'*70}\n\n")

        latest = result['containers'][0]
        response_parts.append(f"✨ Most Recent Version: {latest['tag']}\n\n")
        response_parts.append(f"   Path: {latest['path']}\n")
        response_parts.append(f"   Size: {latest['size_bytes'] / (1024**2):.1f} MB\n\n")

        response_parts.append(f"{'─'*70}\n")
        response_parts.append("💡 USAGE EXAMPLES\n")
        response_parts.append(f"{'─'*70}\n\n")
        response_parts.append("# Execute a command in the container\n")
        response_parts.append(f"singularity exec {latest['path']} \\\n")
        response_parts.append(f"  {tool_name} --help\n\n")
        response_parts.append("# Run interactively\n")
        response_parts.append(f"singularity shell {latest['path']}\n")

        if len(result['containers']) > 1:
            response_parts.append(f"\n{'─'*70}\n")
            response_parts.append("📚 OTHER VERSIONS\n")
            response_parts.append(f"{'─'*70}\n\n")
            for i, container in enumerate(result['containers'][:3], 1):
                response_parts.append(
                    f"  {i:2}. {container['tag']}\n"
                    f"      {container['path']}\n"
                )
            if len(result['containers']) > 3:
                response_parts.append(
                    f"   ... and {len(result['containers']) - 3} more versions\n"
                )
    else:
        response_parts.append("\n⚠️  WARNING: No containers found in CVMFS for this tool\n")
        response_parts.append("   The tool may be available through other means or under a different name.\n")

    response_parts.append(f"\n{'='*70}\n")

    print("".join(response_parts))


def demo_search_function(index, description):
    """Demo: Search by function."""
    results = index.search_by_description(description, limit=5)
    
    if not results:
        print(f"No tools found matching '{description}'. Try different keywords or browse available tools.")
        return
    
    response_parts = [f"# Tools for: {description}\n\n"]
    response_parts.append(f"Found {len(results)} matching tools:\n\n")
    
    for i, result_item in enumerate(results, 1):
        tool = result_item['tool']
        
        response_parts.append(f"## {i}. {tool.get('name', tool.get('id', 'Unknown'))}\n")
        response_parts.append(f"ID: {tool.get('id', 'N/A')}\n")

        if tool.get('description'):
            response_parts.append(f"Description: {tool['description']}\n")

        if tool.get('edam-operations'):
            response_parts.append(f"Operations: {', '.join(tool['edam-operations'])}\n")
        
        # Check if containers available
        tool_search = index.search_tool(tool.get('id', ''))
        if tool_search['containers']:
            latest = tool_search['containers'][0]
            response_parts.append(f"Latest Container: `{latest['tag']}`\n")
            response_parts.append(
                f"Quick Start: `singularity exec {latest['path']} {tool.get('id', '')} --help`\n"
            )

        response_parts.append("\n")

    print("".join(response_parts))


def main():
    """Run demo tests."""
    print("BioContainer Finder MCP - Demo Script")
    print("=" * 70)
    
    # Initialize index
    index = BioContainerIndex()
    index.load_data()
    
    print(f"\nCache Info:")
    print(f"  Generated: {index.cache_info['generated_at']}")
    print(f"  CVMFS Root: {index.cache_info['cvmfs_root']}")
    print(f"  Total Entries: {index.cache_info['entry_count']:,}")
    
    # Demo 1: Find FastQC
    demo_find_tool(index, "fastqc")
    
    # Demo 2: Find IQTree
    demo_find_tool(index, "iqtree")
    
    # Demo 3: Search for quality control tools
    demo_search_function(index, "quality control")
    
    # Demo 4: Search for RNA-seq count tools
    demo_search_function(index, "count data")
    
    # Demo 5: Find samtools
    demo_find_tool(index, "samtools")
    
    print(f"\n{'='*70}")
    print("Demo complete!")
    print("=" * 70)
    print("\nTo use the full MCP client-server:")
    print("  ./biocontainer_client.py find fastqc")
    print("  ./biocontainer_client.py search 'quality control'")
    print("  ./biocontainer_client.py interactive")


if __name__ == "__main__":
    main()
