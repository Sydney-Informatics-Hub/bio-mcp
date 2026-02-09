# BioContainer Finder MCP - Quick Start Guide

## What is this?

An MCP (Model Context Protocol) server that helps you find and use bioinformatics tools from the Galaxy CVMFS Singularity container repository.

## Quick Setup

```bash
# 1. Install dependencies
pip install --break-system-packages mcp pyyaml

# 2. Make scripts executable
chmod +x biocontainer_server.py biocontainer_client.py test_demo.py

# 3. Run demo to verify it works
python3 test_demo.py
```

## Usage Examples

### Command Line

```bash
# Find a tool
./biocontainer_client.py find fastqc

# Search by what it does
./biocontainer_client.py search "quality control"
./biocontainer_client.py search "variant calling"

# Get all versions
./biocontainer_client.py versions samtools

# List available tools
./biocontainer_client.py list 100
```

### Interactive Mode

```bash
./biocontainer_client.py interactive

# Then type commands:
biocontainer> find fastqc
biocontainer> search alignment
biocontainer> versions bwa
biocontainer> list
biocontainer> quit
```

## Supported Query Types

| Question Type | Example | Command |
|--------------|---------|---------|
| Where can I find X? | "Where can I find fastqc?" | `find fastqc` |
| How do I use X? | "How do I use iqtree?" | `find iqtree` |
| What can do X? | "What can generate count data?" | `search count data` |
| What versions exist? | "What versions of samtools?" | `versions samtools` |

## What You Get Back

For each tool, you get:
- ✓ Description and metadata
- ✓ Homepage and license
- ✓ Latest version with CVMFS path
- ✓ Copy-pastable singularity commands
- ✓ All available versions
- ✓ File sizes and dates

## Example Output

```
# FASTQC

Description: Quality control tool for high throughput sequence data
Homepage: http://www.bioinformatics.babraham.ac.uk/projects/fastqc/
License: GPL-3.0

Available Containers: 27 versions

Most Recent Version: 0.12.1--hdfd78af_0
Path: /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0
Size: 279.8 MB

Usage Example:
  singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0 fastqc --help
```

## Common Workflows

### 1. Quality Control Pipeline

```bash
# Find QC tools
./biocontainer_client.py search "quality control"

# Get specific tool
./biocontainer_client.py find fastqc

# Use in your script
singularity exec /cvmfs/singularity.galaxyproject.org/all/fastqc:0.12.1--hdfd78af_0 \
  fastqc sample.fastq.gz -o results/
```

### 2. Find Tool for Task

```bash
# What can align sequences?
./biocontainer_client.py search "sequence alignment"

# What can call variants?
./biocontainer_client.py search "variant calling"

# What can assemble genomes?
./biocontainer_client.py search "genome assembly"
```

### 3. Version Management

```bash
# See all versions
./biocontainer_client.py versions samtools

# Pick specific version for reproducibility
singularity exec /cvmfs/singularity.galaxyproject.org/all/samtools:1.17--h00cdaf9_0 \
  samtools --version
```

## Data Sources

- **toolfinder_meta.yaml**: Tool metadata (714 tools)
- **galaxy_singularity_cache_json.gz**: Container catalog (118,594 images)

## MCP Server Details

The server provides 4 MCP tools:
1. `find_tool` - Find specific tool
2. `search_by_function` - Search by description
3. `get_container_versions` - List all versions
4. `list_available_tools` - Browse tools

## Troubleshooting

**"No containers found"**
- Tool may be spelled differently
- Try searching: `./biocontainer_client.py search toolname`

**"Server script not found"**
- Ensure scripts are in same directory
- Check permissions: `chmod +x *.py`

**Import errors**
- Install: `pip install --break-system-packages mcp pyyaml`

## Next Steps

- Read full README.md for details
- Run test_demo.py to see examples
- Try interactive mode for exploration
- Use in your bioinformatics pipelines!
