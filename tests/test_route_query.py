import pytest
from bio_mcp.mcp.client import route_query, extract_tool_names


QUERY_CASES = [
    # --- SEARCH ---
    (
        "Where can I use the latest version of fastqc?", # query
        "search", # expected route
        ["latest", "version", "fastqc"], # expected tool names extracted
    ),
    ("Is bcftools installed?", "search", ["bcftools", "installed"]),
    (
        "Where can I use the latest version of fakebot?",
        "search",
        ["latest", "version", "fakebot"],
    ),
    ("Is geneforge installed?", "search", ["geneforge", "installed"]),
    (
        "What versions of samtools are available?",
        "search",
        ["versions", "samtools", "available"],
    ),

    # --- DESCRIBE ---
    ("What does samtools do?", "describe", ["samtools"]),
    ("What is multiqc used for?", "describe", ["multiqc"]),
    ("What does fakebot do?", "describe", ["fakebot"]),
    ("What is geneforge used for?", "describe", ["geneforge"]),
    ("Explain the purpose of ggplot", "describe", ["explain", "purpose", "ggplot"]),

    # --- RECOMMEND ---
    (
        "What tool can be used for generating transcript counts for single-cell RNA sequencing?",
        "recommend",
        ["transcript", "counts", "single", "cell", "rna", "sequencing"],
    ),
    (
        "What can I use to build a phylogenetic tree from a multiple sequence alignment (.fasta)?",
        "recommend",
        ["build", "phylogenetic", "tree", "multiple", "sequence", "alignment", "fasta"],
    ),

    # --- NONE / FALLBACK ---
    ("Hello", "none", ["hello"]),
    ("Thanks!", "none", ["thanks"]),
    ("Can you help me?", "none", ["help"]),
]


@pytest.mark.parametrize("query, expected, _tool_names", QUERY_CASES)
def test_route_query(query, expected, _tool_names):
    assert route_query(query) == expected


@pytest.mark.parametrize("query, _expected, tool_names", QUERY_CASES)
def test_extract_tool_names(query, _expected, tool_names):
    assert extract_tool_names(query) == tool_names
