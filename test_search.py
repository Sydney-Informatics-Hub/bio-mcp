import pytest

from biofinder_server import BioFinderIndex

# Sample tool metadata for testing search functionality of BioFinderIndex.
TOOL_INDEX = [
    {
        "id": "star",
        "name": "STAR",
        "description": "Ultrafast universal RNA-seq data aligner",
        "edam-operations": ["Sequence alignment"],
        "edam-topics": ["RNA-Seq", "Transcriptomics"],
        "edam-inputs": ["FASTQ"],
        "edam-outputs": ["SAM", "BAM", "Gene expression matrix"],
    },
    {
        "id": "kallisto",
        "name": "Kallisto",
        "description": (
            "Pseudoalignment-based quantification of RNA-Seq transcripts "
            "for gene expression profiling"
        ),
        "edam-operations": ["Gene expression profiling"],
        "edam-topics": ["RNA-Seq", "Transcriptomics", "Gene expression"],
        "edam-inputs": ["FASTQ"],
        "edam-outputs": ["Transcript abundance estimates"],
    },
    {
        "id": "vcftools",
        "name": "VCFTools",
        "description": "Utilities for working with genetic variation data in VCF format",
        "edam-operations": [
            "Data handling",
            "Variant filtering",
            "Genetic variation analysis",
        ],
        "edam-topics": ["Genetic variation"],
        "edam-inputs": ["VCF"],
        "edam-outputs": ["VCF"],
    },
    {
        "id": "bcftools",
        "name": "BCFtools",
        "description": (
            "Utilities for manipulating and analysing VCF and BCF variant files, "
            "including variant calling and filtering"
        ),
        "edam-operations": ["Variant calling", "Data handling"],
        "edam-topics": [
            "Genetic variation",
            "DNA polymorphism",
            "GWAS study",
            "Genotyping experiment",
        ],
        "edam-inputs": ["VCF", "BCF"],
        "edam-outputs": ["VCF", "BCF"],
    },
    {
        "id": "samtools",
        "name": "SAMtools",
        "description": (
            "Tools for processing, filtering, sorting and analysing "
            "SAM, BAM and CRAM sequencing alignment files"
        ),
        "edam-operations": [
            "Data filtering",
            "Indexing",
            "Data sorting",
            "Data formatting",
        ],
        "edam-topics": ["Mapping", "Sequence analysis", "Sequencing"],
        "edam-inputs": ["SAM", "BAM", "CRAM"],
        "edam-outputs": ["SAM", "BAM", "CRAM"],
    },
    {
        "id": "plink",
        "name": "PLINK",
        "description": (
            "Whole genome association and genetic variation analysis toolkit "
            "for GWAS and population genetics"
        ),
        "edam-operations": ["Genetic variation analysis"],
        "edam-topics": ["GWAS study", "Genomics"],
        "edam-inputs": ["VCF", "BED"],
        "edam-outputs": ["Association statistics"],
    },
    {
        "id": "canu",
        "name": "Canu",
        "description": (
            "De novo genome assembler optimised for long-read sequencing "
            "such as PacBio and Oxford Nanopore"
        ),
        "edam-operations": ["De-novo assembly"],
        "edam-topics": ["Genomics"],
        "edam-inputs": ["FASTQ"],
        "edam-outputs": ["Assembled genome"],
    },
]

@pytest.fixture
def test_index():
    # Create a reusable BioFinderIndex instance with the sample TOOL_INDEX metadata for testing.
    index = BioFinderIndex()
    index.metadata = TOOL_INDEX
    return index

@pytest.mark.parametrize(
    "query",
    [
        "rna",
        "RNA",
        "rna-seq",
        "RNA-SEQ",
        "rnaseq",
    ],
)
def test_search_rna(query, test_index):
    expect = ['STAR', 'Kallisto']
    get = test_index._search_metadata(query)
    assert get == expect

@pytest.mark.parametrize(
    "query",
    [
        "gwas",
        "GWAS",
    ],
)
def test_search_gwas(query, test_index):
    expect = ['BCFtools', 'PLINK']
    results = test_index._search_metadata(query)
    assert expect == results

@pytest.mark.parametrize(
    "query",
    [
        "variant calling",
    ],
)
def test_search_variant_calling(query, test_index):
    expect = ['VCFTools', 'BCFtools']
    results = test_index._search_metadata(query)
    assert expect == results