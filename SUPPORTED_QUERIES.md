# Supported Queries - BioContainer Finder MCP

## Overview

This document details what types of queries the BioContainer Finder MCP can handle and how to use them effectively.

## Query Categories

### 1. Direct Tool Lookup

**Use when:** You know the tool name and want to find it

**Examples:**
- "Where can I find fastqc?"
- "How do I use iqtree?"
- "Give me information about samtools"
- "I need to use bwa"

**Command:** `find <tool_name>`

**What you get:**
- Tool description and metadata
- Homepage and license
- Latest container version
- CVMFS path
- Copy-pastable singularity commands
- List of all available versions

**Example:**
```bash
./biocontainer_client.py find fastqc
```

---

### 2. Functional Search

**Use when:** You know what you want to do but not which tool to use

**Examples:**
- "What can I use to generate count data from scRNA fastqs?"
- "What tools do quality control?"
- "Find me tools for variant calling"
- "What can align sequences?"
- "Tools for genome assembly"

**Command:** `search <description>`

**What you get:**
- Ranked list of matching tools
- Relevance scores (more keywords = higher rank)
- Tool descriptions
- Latest versions
- Quick start commands

**Example:**
```bash
./biocontainer_client.py search "quality control"
./biocontainer_client.py search "count data scRNA"
```

**Search Keywords That Work Well:**
- Operation types: "alignment", "assembly", "annotation", "quality control"
- Data types: "RNA-seq", "ChIP-seq", "scRNA", "variants"
- Tasks: "trimming", "mapping", "counting", "visualization"
- Technologies: "nanopore", "illumina", "pacbio"

---

### 3. Version History

**Use when:** You need to see all available versions of a tool

**Examples:**
- "What versions of samtools are available?"
- "Show me all fastqc versions"
- "I need an older version of bwa"

**Command:** `versions <tool_name>`

**What you get:**
- Complete version history
- CVMFS paths for each version
- File sizes
- Modification dates

**Example:**
```bash
./biocontainer_client.py versions samtools
```

**Use cases:**
- Reproducibility (using exact version from a paper)
- Testing different versions
- Finding newest features

---

### 4. Tool Discovery

**Use when:** You want to explore what's available

**Examples:**
- "What tools are available?"
- "List all bioinformatics tools"
- "Show me the tool catalog"

**Command:** `list [limit]`

**What you get:**
- Alphabetical list of tool names
- Up to specified limit (default 50)

**Example:**
```bash
./biocontainer_client.py list 100
```

---

## How Search Works

### Exact Tool Search
The system looks for tools matching your query in:
1. Tool ID (primary identifier)
2. Tool name (display name)
3. BioTools ID
4. BioContainers ID

**Variations handled:**
- Case insensitive: "FastQC" = "fastqc" = "FASTQC"
- Hyphen/underscore: "bwa-mem" = "bwa_mem"

### Functional Search
The system scores tools based on keyword matches in:
1. **Description** (2x weight for matches, 5x if substring match)
2. **EDAM Operations** (3x weight) - what the tool does
3. **EDAM Topics** (2x weight) - scientific domain
4. **Tool name** (4x weight)
5. **Tool ID** (4x weight)

Results are ranked by total score.

---

## Real-World Query Examples

### Quality Control
```bash
# General QC
./biocontainer_client.py search "quality control"

# Specific for RNA-seq
./biocontainer_client.py search "RNA-seq quality"

# FastQ specific
./biocontainer_client.py search "fastq quality"
```

**Expected tools:** fastqc, falco, multiqc, qualimap

---

### Alignment/Mapping
```bash
# General alignment
./biocontainer_client.py search "sequence alignment"

# Short read alignment
./biocontainer_client.py search "read mapping"

# Specific aligners
./biocontainer_client.py find bwa
./biocontainer_client.py find bowtie2
./biocontainer_client.py find hisat2
```

**Expected tools:** bwa, bowtie2, hisat2, star, minimap2

---

### RNA-seq Analysis
```bash
# Counting
./biocontainer_client.py search "count data"
./biocontainer_client.py search "RNA-seq quantification"

# Differential expression
./biocontainer_client.py search "differential expression"

# Specific tools
./biocontainer_client.py find featurecounts
./biocontainer_client.py find salmon
./biocontainer_client.py find deseq2
```

**Expected tools:** featurecounts, htseq, salmon, kallisto, deseq2, edger

---

### Single-Cell RNA-seq
```bash
# General scRNA
./biocontainer_client.py search "single cell"
./biocontainer_client.py search "scRNA"

# Specific tasks
./biocontainer_client.py search "cell counting"
./biocontainer_client.py search "droplet"
```

**Expected tools:** scanpy, seurat, dropletutils, cellranger

---

### Variant Calling
```bash
# General variant calling
./biocontainer_client.py search "variant calling"

# SNP/indel
./biocontainer_client.py search "SNP detection"

# Specific tools
./biocontainer_client.py find gatk
./biocontainer_client.py find bcftools
./biocontainer_client.py find freebayes
```

**Expected tools:** gatk, bcftools, freebayes, varscan, mutect2

---

### Assembly
```bash
# Genome assembly
./biocontainer_client.py search "genome assembly"

# De novo assembly
./biocontainer_client.py search "de novo assembly"

# Specific tools
./biocontainer_client.py find spades
./biocontainer_client.py find flye
```

**Expected tools:** spades, megahit, flye, canu, unicycler

---

## Tips for Better Results

### 1. Start Broad, Then Narrow
```bash
# Start broad
./biocontainer_client.py search "alignment"

# Then narrow
./biocontainer_client.py search "RNA alignment"
./biocontainer_client.py search "splice-aware alignment"
```

### 2. Use Domain Terminology
Better: `search "variant calling"`
Not: `search "find mutations"`

Better: `search "quality control"`
Not: `search "check if data is good"`

### 3. Check Multiple Variations
```bash
# Try different phrasings
./biocontainer_client.py search "read counting"
./biocontainer_client.py search "quantification"
./biocontainer_client.py search "gene expression"
```

### 4. Use Interactive Mode for Exploration
```bash
./biocontainer_client.py interactive

biocontainer> search alignment
# See results, then refine...
biocontainer> find bwa
biocontainer> versions bwa
```

---

## Limitations

### What Works
✓ Finding tools by name
✓ Searching by function/description
✓ Getting version history
✓ Browsing available tools
✓ Copy-pastable singularity commands

### What Doesn't Work
✗ Natural language questions (use keywords instead)
✗ Workflow creation (discovery only)
✗ Performance comparisons
✗ Installation instructions (containers are pre-built)
✗ Parameter recommendations
✗ Semantic similarity (uses keyword matching)

---

## Query Optimization

### For Best Results

**DO:**
- Use specific technical terms
- Include data type (RNA-seq, ChIP-seq, etc.)
- Mention the operation (alignment, assembly, etc.)
- Try both singular and plural
- Check spelling

**DON'T:**
- Use long natural language sentences
- Include unnecessary words ("please", "I want to")
- Assume exact tool name spelling
- Give up if first search doesn't work - try synonyms!

---

## Common Query Patterns

| Task | Good Query | Better Query |
|------|------------|--------------|
| Find QC tool | "quality" | "quality control" |
| Find aligner | "align" | "sequence alignment" |
| Find assembler | "assembly" | "de novo assembly" |
| Find counter | "count" | "read counting" OR "quantification" |
| Find trimmer | "trim" | "adapter trimming" |
| Find variant caller | "variants" | "variant calling" |

---

## Interactive vs Command Line

### Use Interactive Mode When:
- Exploring unfamiliar tools
- Comparing multiple tools
- Learning what's available
- Testing different search terms

### Use Command Line When:
- You know exactly what you want
- Scripting/automation
- Quick lookups
- Integration with other tools

---

## Integration Ideas

The MCP can be integrated into:
- LLM assistants (Claude, GPT-4)
- Jupyter notebooks
- Nextflow/Snakemake workflows
- Custom bioinformatics pipelines
- Teaching materials
- Documentation generation

---

## Summary

**4 Query Types:**
1. `find <tool>` - Direct lookup
2. `search <description>` - Functional search
3. `versions <tool>` - Version history
4. `list [limit]` - Browse catalog

**Best Practices:**
- Use technical terminology
- Start broad, refine as needed
- Try interactive mode for exploration
- Check multiple search terms if needed

**Remember:** The system has 714 tools with metadata and 118,594+ container versions!
