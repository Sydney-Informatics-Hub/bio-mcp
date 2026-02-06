import pytest
from bio_mcp.mcp.client import route_query


@pytest.mark.parametrize(
    "query, expected",
    [
        # --- SEARCH ---
        ("Where can I use the latest version of fastqc?", "search"),
        ("Is bcftools installed?", "search"),
        ("Where can I use the latest version of fakebot?", "search"),
        ("Is geneforge installed?", "search"),
        ("What versions of samtools are available?", "search"),

        # --- DESCRIBE ---
        ("What does samtools do?", "describe"),
        ("What is multiqc used for?", "describe"),
        ("What does fakebot do?", "describe"),
        ("What is geneforge used for?", "describe"),
        ("Explain the purpose of ggplot", "describe"),

        # --- RECOMMEND ---
        (
            "What tool can be used for generating transcript counts for single-cell RNA sequencing?",
            "recommend",
        ),
        (
            "What can I use to build a phylogenetic tree from a multiple sequence alignment (.fasta)?",
            "recommend",
        ),

        # --- NONE / FALLBACK ---
        ("Hello", "none"),
        ("Thanks!", "none"),
        ("Can you help me?", "none"),
    ],
)
def test_route_query(query, expected):
    assert route_query(query) == expected

