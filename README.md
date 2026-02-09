# BioFinder MCP

A Model Context Protocol (MCP) server and client for discovering and using bioinformatics tools available in the Galaxy CVMFS Singularity container repository.

## Overview

This MCP provides:
- **Container Discovery**: Find bioinformatics tools and their available container versions
- **Metadata Search**: Search by tool name, function, or description
- **Usage Examples**: Get copy-pastable Singularity commands
- **Version Management**: View all available versions with paths and metadata

## Data Sources

The MCP uses two authoritative data sources:
1. **toolfinder_meta.yaml** - Tool metadata including descriptions, operations, and publications. [Sourced from `finder-service-metadata`](https://github.com/AustralianBioCommons/finder-service-metadata/blob/main/data/data.yaml)
2. **galaxy_singularity_cache.json.gz** - Complete CVMFS container catalog (118,000+ entries)

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
chmod +x biofinder_server.py
chmod +x biofinder_client.py
```

## Usage

### Command Line Interface

```bash
# Find a specific tool
./biofinder_client.py find fastqc

# Search by function/description
./biofinder_client.py search "quality control"
./biofinder_client.py search "count data from scrna"

# Get all versions of a tool
./biofinder_client.py versions samtools

# List available tools
./biofinder_client.py list 50

# Interactive mode
./biofinder_client.py interactive
```

### Interactive Mode

```bash
./biofinder_client.py interactive
```

Then use commands:
```
biofinder> find fastqc
biofinder> search alignment
biofinder> versions bwa
biofinder> list 100
biofinder> help
biofinder> quit
```

## Example Outputs

### Finding a Tool

```bash
$ ./biofinder_client.py find fastqc


======================================================================
🧬 FASTQC
======================================================================

📝 Description:
   This tool aims to provide a QC report which can spot problems or biases which originate either in the sequencer or in the starting library material. It can be run in one of two modes. It can either run as a stand alone interactive application for the immediate analysis of small numbers of FastQ files, or it can be run in a non-interactive mode where it would be suitable for integrating into a larger analysis pipeline for the systematic processing of large numbers of files.

🌐 Homepage: http://www.bioinformatics.babraham.ac.uk/projects/fastqc/
⚙️  Operations: Sequence composition calculation, Sequencing quality control, Statistical calculation

──────────────────────────────────────────────────────────────────────
📦 AVAILABLE CONTAINERS (27 versions)
──────────────────────────────────────────────────────────────────────

✨ Most Recent Version: 0.12.1--hdfd78af_0

   Path: /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0
   Size: 279.8 MB

──────────────────────────────────────────────────────────────────────
💡 USAGE EXAMPLES
──────────────────────────────────────────────────────────────────────

# Execute a command in the container
singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0 \
  fastqc --help

# Run interactively
singularity shell /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0

──────────────────────────────────────────────────────────────────────
📚 OTHER VERSIONS
──────────────────────────────────────────────────────────────────────

   1. 0.12.1--hdfd78af_0
      /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0
   2. 0.11.9--hdfd78af_1
      /cvmfs/singularity.galaxyproject.org/all/fastqc:0.11.9--hdfd78af_1
   3. 0.11.9--0
      /cvmfs/singularity.galaxyproject.org/all/fastqc:0.11.9--0
   ... and 24 more versions

======================================================================
```

## Architecture

### Server (`biofinder_server.py`)
- Loads and indexes both data sources on startup
- Provides 4 MCP tools for container discovery
- Implements search with version parsing and ranking
- Exposes resources for cache metadata

### Client (`biofinder_client.py`)
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
   ./biofinder_client.py search "quality control"
   
   # Get specific tool
   ./biofinder_client.py find fastqc
   
   # Use in your workflow
   singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_2 \
     fastqc sample.fastq.gz -o results/
   ```

2. **Tool Discovery**
   ```bash
   # What can do variant calling?
   ./biofinder_client.py search "variant calling"
   
   # What can assemble genomes?
   ./biofinder_client.py search "genome assembly"
   ```

3. **Version Management**
   ```bash
   # Check what versions are available
   ./biofinder_client.py versions samtools
   
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

- Metadata is incomplete for many tools
- Container availability depends on CVMFS being mounted
- Search is keyword-based (no semantic search yet)
- No execution or workflow management (discovery only)

## Future Enhancements

Potential improvements:
- Use LLM for NLP and improved/accurate resposnes
- Semantic search using embeddings
- Container testing and validation
- Usage statistics and popularity rankings
- Direct CVMFS path verification
- API connections to CVMFS resources and 

## Data Updates

TODO: docs for creating `galaxy_singularity_cache.json.gz`

To update the data sources:
1. Replace `toolfinder_meta.yaml` with the latest version
2. Replace `galaxy_singularity_cache.json.gz` with current cache
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

## Contributing

Suggestions for improvements:
- Additional query types
- Better search algorithms
- Integration with other registries

## Contact

For questions about:
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Galaxy Containers**: https://galaxyproject.org/
- **CVMFS**: https://cernvm.cern.ch/fs/
