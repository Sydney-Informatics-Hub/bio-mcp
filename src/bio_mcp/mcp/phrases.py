import re

_COMMON_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "it",
        "i",
        "me",
        "you",
        "can",
        "do",
        "does",
        "what",
        "where",
        "to",
        "of",
        "for",
        "are",
        "be",
        "used",
        "use",
        "tool",
        "generating",
        "generate",
        "from"
    }
)

_SEARCH_PHRASES = (
    "is installed",
    "is it installed",
    "installed?",
    "where can i use",
    "where do i use",
    "where can i run",
    "where is",
    "available version",
    "what versions are available",
    "latest version",
    "latest",
    "are available?",
)

_DESCRIBE_PHRASES = (
    "what does",
    "what is",
    "purpose of",
    "describe",
)

_RECOMMEND_PHRASES = (
    "what tool can be used",
    "what tool should i use",
    "what can i use to",
    "can be used to",
    "can be used for",
    "tool for",
    "used to generate",
    "used to build",
)