# BioContainer Finder MCP

A Model Context Protocol (MCP) server and client for discovering and using bioinformatics tools available in the Galaxy CVMFS Singularity container repository.

## Overview

This MCP provides:
- **Container Discovery**: Find bioinformatics tools and their available container versions
- **Metadata Search**: Search by tool name, function, or description
- **Usage Examples**: Get copy-pastable Singularity commands
- **Version Management**: View all available versions with paths and metadata

## Data Sources

The MCP uses two authoritative data sources:
1. **toolfinder_meta.yaml** - Tool metadata including descriptions, operations, and publications
2. **galaxy_singularity_cache_json.gz** - Complete CVMFS container catalog (118,000+ entries)

## Features

### Supported Queries

The MCP is designed to answer queries like:

- **"Where can I find fastqc?"** → Returns tool info, container versions, and usage examples
- **"How do I use iqtree?"** → Shows the latest version and copy-pastable singularity commands
- **"What can I use to generate count data from scRNA fastqs?"** → Searches by description/function
- **"Show me all versions of samtools"** → Lists all available container versions with paths

### Available Tools (MCP Functions)

1. **find_tool** - Find a specific tool by name
   - Returns: metadata, container versions, usage examples
   - Example: `find fastqc`

2. **search_by_function** - Search by description or operation
   - Returns: ranked list of matching tools
   - Example: `search quality control`

3. **get_container_versions** - List all versions of a tool
   - Returns: complete version history with CVMFS paths
   - Example: `versions samtools`

4. **list_available_tools** - Browse available tools
   - Returns: alphabetical list of tool names
   - Example: `list 100`

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Run the setup script
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
# Install dependencies
pip install --break-system-packages -r requirements.txt

# Make scripts executable
chmod +x biocontainer_server.py
chmod +x biocontainer_client.py
```

## Usage

### Command Line Interface

```bash
# Find a specific tool
./biocontainer_client.py find fastqc

# Search by function/description
./biocontainer_client.py search "quality control"
./biocontainer_client.py search "count data from scrna"

# Get all versions of a tool
./biocontainer_client.py versions samtools

# List available tools
./biocontainer_client.py list 50

# Interactive mode
./biocontainer_client.py interactive
```

### Interactive Mode

```bash
./biocontainer_client.py interactive
```

Then use commands:
```
biocontainer> find fastqc
biocontainer> search alignment
biocontainer> versions bwa
biocontainer> list 100
biocontainer> help
biocontainer> quit
```

## Example Outputs

### Finding a Tool

```bash
$ ./biocontainer_client.py find fastqc

# FASTQC

**Description:** A quality control tool for high throughput sequence data

**Homepage:** https://www.bioinformatics.babraham.ac.uk/projects/fastqc/

**License:** GPL-3.0

**Operations:** Sequencing quality control

## Available Containers (45 versions)

### Most Recent Version: 0.12.1--hdfd78af_2
**Path:** `/cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2`
**Size:** 245.3 MB

### Usage Example:
```bash
# Execute a command in the container
singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2 fastqc --help

# Run interactively
singularity shell /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2
```

### All Available Versions:
- **0.12.1--hdfd78af_2** - `/cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2`
- **0.12.1--hdfd78af_1** - `/cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_1`
- **0.11.9--hdfd78af_1** - `/cvmfs/singularity.galaxyproject.org/all/fastqc:0.11.9--hdfd78af_1`
...
```

### Searching by Function

```bash
$ ./biocontainer_client.py search "sequence alignment"

# Tools for: sequence alignment

Found 15 matching tools:

## 1. BWA
**ID:** bwa
**Description:** Burrows-Wheeler Aligner for mapping sequences against large genomes
**Operations:** Sequence alignment, Read mapping
**Latest Container:** `0.7.17--h5bf99c6_8`
**Quick Start:** `singularity exec /cvmfs/singularity.galaxyproject.org/all/bwa:0.7.17--h5bf99c6_8 bwa --help`

## 2. Bowtie2
**ID:** bowtie2
**Description:** Fast and memory-efficient aligner for short DNA sequences
**Operations:** Sequence alignment
...
```

## Architecture

### Server (`biocontainer_server.py`)
- Loads and indexes both data sources on startup
- Provides 4 MCP tools for container discovery
- Implements intelligent search with version parsing and ranking
- Exposes resources for cache metadata

### Client (`biocontainer_client.py`)
- Command-line interface with multiple modes
- Connects to server via stdio MCP transport
- Supports both one-shot and interactive queries
- Formats output for easy reading and copy-paste

### Data Flow
```
User Query → Client → MCP Protocol → Server → Index Search → Formatted Response
```

## MCP Protocol Details

This implementation follows the [Model Context Protocol](https://modelcontextprotocol.io/) specification:

- **Transport**: stdio (standard input/output)
- **Tools**: 4 callable functions
- **Resources**: 2 readable data sources
- **Message Format**: JSON-RPC 2.0

## Use Cases

### Bioinformatics Workflows

1. **Quality Control Pipeline**
   ```bash
   # Find QC tools
   ./biocontainer_client.py search "quality control"
   
   # Get specific tool
   ./biocontainer_client.py find fastqc
   
   # Use in your workflow
   singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2 \
     fastqc sample.fastq.gz -o results/
   ```

2. **Tool Discovery**
   ```bash
   # What can do variant calling?
   ./biocontainer_client.py search "variant calling"
   
   # What can assemble genomes?
   ./biocontainer_client.py search "genome assembly"
   ```

3. **Version Management**
   ```bash
   # Check what versions are available
   ./biocontainer_client.py versions samtools
   
   # Use a specific version in reproducible research
   singularity exec /cvmfs/singularity.galaxyproject.org/all/samtools:1.17--h00cdaf9_0 \
     samtools --version
   ```

### Integration with Other Tools

The MCP protocol allows this server to be used by:
- LLM assistants (Claude, GPT-4, etc.)
- Workflow management systems
- Custom bioinformatics pipelines
- Interactive computing environments

## Limitations

- Metadata may be incomplete for some tools (depends on source data)
- Container availability depends on CVMFS being mounted
- Search is keyword-based (no semantic search yet)
- No execution or workflow management (discovery only)

## Future Enhancements

Potential improvements:
- Semantic search using embeddings
- Container testing and validation
- Integration with workflow languages (Nextflow, Snakemake)
- Usage statistics and popularity rankings
- Direct CVMFS path verification
- Tool dependency graphs

## Data Updates

To update the data sources:
1. Replace `toolfinder_meta.yaml` with the latest version
2. Replace `galaxy_singularity_cache_json.gz` with current cache
3. Restart the server

The index is rebuilt on each server start, so changes are immediately available.

## Troubleshooting

### "No containers found"
- Check that the tool name is correct (case-insensitive)
- Try searching by function instead of exact name
- The tool may be in metadata but not have containers available

### "Server script not found"
- Ensure both server and client scripts are in the same directory
- Check file permissions (should be executable)

### Import errors
- Run `pip install --break-system-packages -r requirements.txt`
- Ensure Python 3.8+ is installed

## License

This MCP implementation is provided as-is for bioinformatics research use.

## Contributing

Suggestions for improvements:
- Additional query types
- Better search algorithms
- Integration with other registries
- Usage documentation generation

## Contact

For questions about:
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Galaxy Containers**: https://galaxyproject.org/
- **CVMFS**: https://cernvm.cern.ch/fs/
