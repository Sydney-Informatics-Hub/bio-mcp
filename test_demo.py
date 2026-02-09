#!/usr/bin/env python3
"""
Test script for BioContainer Finder MCP

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
DATA_DIR = Path("/mnt/user-data/uploads")
METADATA_FILE = DATA_DIR / "toolfinder_meta.yaml"
SINGULARITY_CACHE_FILE = DATA_DIR / "galaxy_singularity_cache_json.gz"


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
    print(f"\n{'='*70}")
    print(f"DEMO: Finding tool '{tool_name}'")
    print(f"{'='*70}\n")
    
    result = index.search_tool(tool_name)
    
    if result['metadata']:
        meta = result['metadata']
        print(f"# {meta.get('name', tool_name.upper())}\n")
        
        if meta.get('description'):
            print(f"Description: {meta['description']}\n")
        
        if meta.get('homepage'):
            print(f"Homepage: {meta['homepage']}")
        
        if meta.get('license'):
            print(f"License: {meta['license']}")
        
        if meta.get('edam-operations'):
            print(f"Operations: {', '.join(meta['edam-operations'])}")
    
    if result['containers']:
        print(f"\nAvailable Containers: {result['container_count']} versions\n")
        
        latest = result['containers'][0]
        print(f"Most Recent Version: {latest['tag']}")
        print(f"Path: {latest['path']}")
        print(f"Size: {latest['size_bytes'] / (1024**2):.1f} MB\n")
        
        print("Usage Example:")
        print(f"  singularity exec {latest['path']} {tool_name} --help\n")
        
        if len(result['containers']) > 1:
            print(f"Other versions available: {len(result['containers']) - 1} more")
            print(f"  Latest 5:")
            for container in result['containers'][1:6]:
                print(f"    - {container['tag']}")
    else:
        print("\n⚠️  No containers found in CVMFS for this tool.")


def demo_search_function(index, description):
    """Demo: Search by function."""
    print(f"\n{'='*70}")
    print(f"DEMO: Searching for tools related to '{description}'")
    print(f"{'='*70}\n")
    
    results = index.search_by_description(description, limit=5)
    
    if not results:
        print(f"No tools found matching '{description}'")
        return
    
    print(f"Found {len(results)} matching tools:\n")
    
    for i, result_item in enumerate(results, 1):
        tool = result_item['tool']
        
        print(f"{i}. {tool.get('name', tool.get('id', 'Unknown'))}")
        print(f"   ID: {tool.get('id', 'N/A')}")
        
        if tool.get('description'):
            desc = tool['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            print(f"   Description: {desc}")
        
        if tool.get('edam-operations'):
            print(f"   Operations: {', '.join(tool['edam-operations'][:3])}")
        
        # Check if containers available
        tool_search = index.search_tool(tool.get('id', ''))
        if tool_search['containers']:
            latest = tool_search['containers'][0]
            print(f"   Latest: {latest['tag']}")
        
        print()


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
