# 🧬 BioFinder MCP

Find bioinformatics tools available as Singularity containers on Galaxy CVMFS -
and get ready-to-copy `singularity` commands from your terminal.

⚠️ Warning: This project is under active development. The tool returns results based on **availability**. Independent research is advised to identify the best tool for your data and needs.

## What does it do?

BioFinder is a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP)
server + CLI client. It indexes two data sources:

| Data source | Contents |
|---|---|
| `toolfinder_meta.yaml` | 714 tool records with descriptions, operations, and homepage links. [Source (`AustralianBioCommons/finder-service-metadata`) ↗](https://github.com/AustralianBioCommons/finder-service-metadata) |
| `galaxy_singularity_cache.json.gz` | 118,594 Singularity container images on Galaxy CVMFS (snapshot: 2026-01-28) |

Given a tool name or a description of what you want to do, BioFinder returns the
latest container path and a copy-pastable `singularity` command.

## Example output

```bash
biofinder> find fastqc

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

To get started, clone and move into the repository.

```bash
git clone https://github.com/Sydney-Informatics-Hub/bio-finder.git
cd bio-finder
```

Install Python and the required libraries. Dependencies are listed in `requirements.txt`.

```bash
chmod +x setup.sh
./setup.sh
```

### Example usage 

This mini-tutorial demonstrates an example of starting the tool, displaying the supported commands, and a recommended flow of finding available software that can be used for sequence alignment. 

Once a (sequence alignment) tool is chosen, you can display more information about the available versions on the file system.

```bash
# Enter interactive mode
./biofinder

# Display help message
biofinder> help

# Search for tools related to sequence alignment
biofinder> search sequence alignment

# Find a specific tool with more information
biofinder> find clustalo

# Display all available versions
biofinder> versions clustalo
```

⚠️ Warning: The tool returns results based on **availability**. Independent research is advised to identify the best tool for your data and needs.

## Next steps

For an overview of all available options, examples, and tips for using BioFinder effectively, see the guide on [how to query](docs/HOW_TO_QUERY.md).

If you prefer the command-line version (e.g. for scripting and reproducibility), see the [command reference](docs/COMMAND_REFERENCE.md).

BioFinder is in active development with plans to improve functionality, the accuracy of search results, and implementation. See [Future Improvements](docs/DEVELOPER_REFERENCE.md#future-improvements).

## Links

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Galaxy Project CVMFS](https://galaxyproject.org/admin/reference-data-repo/)
- [finder-service-metadata](https://github.com/AustralianBioCommons/finder-service-metadata)
- [CERN VM-FS](https://cernvm.cern.ch/fs/)
