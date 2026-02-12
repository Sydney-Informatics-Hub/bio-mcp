# 🧬 BioFinder MCP

Find bioinformatics tools available as Singularity containers on Galaxy CVMFS -
and get ready-to-copy `shpc` commands from your terminal.

## What does it do?

BioFinder is a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP)
server + CLI client. It indexes two data sources:

| Data source | Contents |
|---|---|
| `toolfinder_meta.yaml` | 714 tool records with descriptions, operations, and homepage links. [Source (`AustralianBioCommons/finder-service-metadata`) ↗](https://github.com/AustralianBioCommons/finder-service-metadata) |
| `galaxy_singularity_cache.json.gz` | 118,594 Singularity container images on Galaxy CVMFS (snapshot: 2026-01-28) |

Given a tool name or a description of what you want to do, BioFinder returns the
latest container path and a copy-pastable `shpc` command.

## Example output

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

## Quick start

### Setup

To get started, install Python and the required libraries.

```bash
chmod +x setup.sh
./setup.sh
```

### Example usage

This demonstrates an example of starting the tool, displaying the supported commands, and a flow of finding available software that can be used for sequence alignment. 

One located, you can display more information about the available versions on the file system.

```bash
# Enter interactive mode
./biofinder_client.py 

# Display help message
biofinder> help

# Search for tools related to sequence alignment
biofinder> search sequence alignment

# Find a specific tool with more information
biofinder> find clustalo

# Display all available versions
biofinder> versions clustalo
```

## Limitations

- **Keyword search only** — no semantic/embedding-based search yet.
- **Metadata is incomplete** for many tools; descriptions and EDAM operations are
  missing for a portion of the catalog.
- **Container paths are not validated** at query time — they require CVMFS to be
  mounted.
- **Cache is a point-in-time snapshot** — new containers added to CVMFS after the
  snapshot date won't appear until the cache is regenerated.

See [DEVELOPER_REFERENCE.md → Future improvements](docs/DEVELOPER_REFERENCE.md#future-improvements)
for the roadmap.

---

## Links

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Galaxy Project CVMFS](https://galaxyproject.org/admin/reference-data-repo/)
- [finder-service-metadata](https://github.com/AustralianBioCommons/finder-service-metadata)
- [CERN VM-FS](https://cernvm.cern.ch/fs/)


## Features

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
