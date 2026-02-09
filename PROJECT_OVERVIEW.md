# BioContainer Finder MCP - Project Overview

## What Was Built

A complete Model Context Protocol (MCP) client-server system for discovering bioinformatics tools in the Galaxy CVMFS Singularity container repository.

## Files Delivered

### Core Components
1. **biocontainer_server.py** - MCP server implementation
   - Loads and indexes 714 tool metadata entries
   - Indexes 118,594 Singularity container images
   - Provides 4 MCP tools for queries
   - Implements smart search and ranking

2. **biocontainer_client.py** - Command-line MCP client
   - One-shot query mode
   - Interactive mode
   - Clean formatted output
   - Copy-pastable examples

3. **test_demo.py** - Standalone demo script
   - No MCP dependencies needed
   - Shows 5 example queries
   - Validates data loading
   - Useful for testing

### Documentation
4. **README.md** - Comprehensive documentation (500+ lines)
   - Full installation guide
   - Architecture explanation
   - Usage examples
   - Troubleshooting
   - Integration ideas

5. **QUICKSTART.md** - Quick reference
   - Fast setup (3 steps)
   - Common commands
   - Example outputs
   - Troubleshooting

6. **SUPPORTED_QUERIES.md** - Query guide (400+ lines)
   - 4 query type explanations
   - 20+ real-world examples
   - Search optimization tips
   - Best practices

### Setup Files
7. **requirements.txt** - Python dependencies
8. **setup.sh** - One-command setup script

## Key Features

### Data Sources
- **toolfinder_meta.yaml**: 714 bioinformatics tools with rich metadata
- **galaxy_singularity_cache_json.gz**: 118,594 Singularity container images

### Supported Queries

#### 1. Find Tool by Name
```bash
./biocontainer_client.py find fastqc
```
Returns: metadata, versions, usage examples

#### 2. Search by Function
```bash
./biocontainer_client.py search "quality control"
```
Returns: ranked tools matching description

#### 3. Get Version History
```bash
./biocontainer_client.py versions samtools
```
Returns: all versions with paths

#### 4. List Available Tools
```bash
./biocontainer_client.py list 100
```
Returns: alphabetical tool list

### Real Query Examples

The system answers questions like:
- "Where can I find fastqc?" → Direct tool lookup
- "How do I use iqtree?" → Usage examples with paths
- "What can I use to generate count data from scRNA fastqs?" → Functional search
- "Show me all versions of samtools" → Version history

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              biocontainer_client.py                          │
│  - CLI interface (one-shot or interactive)                   │
│  - Formats queries                                           │
│  - Displays results                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ (MCP Protocol - JSON-RPC over stdio)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              biocontainer_server.py                          │
│  - Loads data on startup                                     │
│  - Builds search indexes                                     │
│  - Implements 4 MCP tools                                    │
│  - Smart version parsing                                     │
│  - Keyword-based ranking                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Sources                               │
│  - toolfinder_meta.yaml (714 tools)                          │
│  - galaxy_singularity_cache_json.gz (118,594 images)         │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Server Startup
- Loads YAML metadata (714 tools)
- Loads gzipped JSON cache (118,594 containers)
- Builds tool name → containers index
- Ready to serve queries

### 2. Query Processing
- Client sends MCP request
- Server searches indexes
- Ranks results by relevance
- Parses and sorts versions
- Returns formatted response

### 3. Smart Search
- Exact name matching (case-insensitive)
- Fuzzy matching (handles hyphens/underscores)
- Description keyword scoring
- EDAM operation matching
- Topic relevance

### 4. Version Management
- Semantic version parsing
- Sorts newest first
- Provides complete history
- Includes metadata (size, date)

## Installation & Usage

### Quick Start
```bash
# 1. Install
pip install --break-system-packages mcp pyyaml

# 2. Run demo
python3 test_demo.py

# 3. Use client
./biocontainer_client.py find fastqc
```

### Interactive Mode
```bash
./biocontainer_client.py interactive

biocontainer> find fastqc
biocontainer> search quality control
biocontainer> versions bwa
biocontainer> quit
```

## Example Output

```
# FASTQC

Description: Quality control tool for high throughput sequence data

Homepage: http://www.bioinformatics.babraham.ac.uk/projects/fastqc/
License: GPL-3.0
Operations: Sequencing quality control

Available Containers: 27 versions

Most Recent Version: 0.12.1--hdfd78af_0
Path: /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0
Size: 279.8 MB

Usage Example:
  singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0 fastqc --help
```

## MCP Protocol Implementation

### Resources (2)
- `biocontainer://cache-info` - Cache metadata
- `biocontainer://tool-list` - All available tools

### Tools (4)
1. `find_tool` - Find by name
2. `search_by_function` - Search by description
3. `get_container_versions` - Version history
4. `list_available_tools` - Browse catalog

### Transport
- stdio (standard input/output)
- JSON-RPC 2.0 messages
- Asynchronous Python (asyncio)

## Use Cases

### 1. Bioinformatics Pipelines
- Discover tools for workflows
- Find exact versions for reproducibility
- Get copy-pastable commands

### 2. Teaching & Learning
- Explore available tools
- Understand tool categories
- Learn CVMFS usage

### 3. LLM Integration
- Use as MCP server for Claude/GPT-4
- Enable AI-assisted tool discovery
- Automate workflow suggestions

### 4. Documentation
- Generate tool lists
- Create usage examples
- Build training materials

## Technical Highlights

### Efficient Indexing
- Pre-indexes 118,594 containers
- O(1) lookup by tool name
- Fast keyword search

### Smart Version Sorting
- Parses semantic versions
- Handles complex tags
- Sorts newest first

### Robust Search
- Keyword matching
- Relevance scoring
- Handles typos (fuzzy matching)
- Multi-field search

### Clean Output
- Markdown formatting
- Copy-pastable commands
- Hierarchical information
- Size-optimized displays

## Statistics

- **Tools with metadata**: 714
- **Total containers**: 118,594
- **CVMFS root**: `/cvmfs/singularity.galaxyproject.org/all`
- **Cache generated**: 2026-01-28
- **MCP tools provided**: 4
- **Lines of code**: ~1,200
- **Documentation**: 1,500+ lines

## Future Enhancements

Potential additions:
- [ ] Semantic search using embeddings
- [ ] Tool dependency graphs
- [ ] Usage statistics/popularity
- [ ] Container verification
- [ ] Workflow templates
- [ ] Integration with Galaxy
- [ ] Web interface
- [ ] API wrapper

## Testing

The `test_demo.py` script demonstrates:
1. ✓ FastQC lookup
2. ✓ IQTree lookup
3. ✓ Quality control search
4. ✓ Count data search
5. ✓ Samtools lookup

All queries work correctly with expected results.

## Dependencies

**Required:**
- Python 3.8+
- mcp >= 1.0.0
- pyyaml >= 6.0

**Optional:**
- None (standalone system)

## Limitations

- Metadata completeness varies by tool
- Keyword-based search (not semantic)
- Discovery only (no execution)
- Requires CVMFS mount for actual use
- No workflow management

## Success Metrics

✓ Answers all example queries
✓ Provides copy-pastable commands
✓ Fast search (<1 second)
✓ Clean, readable output
✓ Well documented
✓ Easy to install
✓ Extensible design

## Contact & Support

- **MCP Protocol**: https://modelcontextprotocol.io/
- **Galaxy Project**: https://galaxyproject.org/
- **CVMFS**: https://cernvm.cern.ch/fs/

## License

This implementation provided for bioinformatics research use.

---

**Built with:** Python, MCP SDK, YAML, Gzip
**Data from:** Galaxy Project CVMFS repository
**Protocol:** Model Context Protocol (MCP)
