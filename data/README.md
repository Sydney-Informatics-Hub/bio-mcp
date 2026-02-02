# Data

Data for testing and development.

**`galaxy_singularity_cache.json.gz`**

- List of all Galaxy singularity containers from the CVMFS 
- See [How to build a cache](running.md/#how-to-build-a-cache)                                                          
**`scrnaseq_biotools.yaml`** 

- Manual selection of scrnaseq workflow tools from https://github.com/AustralianBioCommons/finder-service-metadata/blob/main/data/data.yaml
- fastqc, cellbender, cellranger, multiqc, seurat, scanpy

**`scrnaseq_galaxy_cvmfs.json`**

- Subset of `galaxy_singularity_cache.json.gz` to include the tools from `scrnaseq_biotools.yaml`
- Nice range of test cases, such as:
    - cellranger entry available, none in biotools, not in galaxy = useful negative control
    - seurat and scanpy packages have a lot of different entries named differently
    - fastqc, multiqc, cellbender stable positive controls with different versions
