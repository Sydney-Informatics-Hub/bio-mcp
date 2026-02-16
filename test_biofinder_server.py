import pytest

from biofinder_server import BioFinderIndex

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
        "id": "plink",
        "name": "PLINK",
        "description": "Whole genome association and genetic variation analysis toolkit",
        "edam-operations": ["Genetic variation analysis"],
        "edam-topics": ["GWAS study", "Genomics"],
        "edam-inputs": ["VCF", "BED"],
        "edam-outputs": ["Association statistics"],
    },
]

@pytest.fixture
def test_index():
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
def test_rna_queries_match_rnaseq(query, test_index):
    results = test_index._search_metadata(query)

    assert ["STAR", "Kallisto"] in results
    assert ["PLINK"] not in results
