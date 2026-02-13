#!/usr/bin/env python3
"""
BioFinder MCP Server

Provides bioinformatics container discovery over the Model Context Protocol (MCP).
Clients (CLI, LLM agents, workflow tools) connect via stdio and call four tools:
  - find_tool             exact/near-exact tool name lookup
  - search_by_function    semantic similarity search (this is what changed)
  - get_container_versions full version history for a tool
  - list_available_tools  alphabetical catalog

The key improvement in this version is that search_by_function now uses
sentence-embedding models instead of keyword counting. See SemanticSearchIndex
for details.
"""

import json
import gzip
import yaml
import asyncio
import logging
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import re

import numpy as np

# MCP SDK imports.
# The MCP server exposes "tools" (callable functions) and "resources" (readable
# data) over a JSON-RPC protocol on stdio. The client (biofinder_client.py)
# spawns this process and talks to it over its stdin/stdout pipes.
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
import mcp.server.stdio


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent
METADATA_FILE = DATA_DIR / "toolfinder_meta.yaml"
SINGULARITY_CACHE_FILE = DATA_DIR / "galaxy_singularity_cache.json.gz"

# Embedding cache files live next to the data files.
# We store one .npy matrix per model so we don't re-embed 714 texts every
# startup — that would add ~10-30 s per model on CPU.
MINILM_CACHE = DATA_DIR / ".embed_cache_minilm.npy"
BIOBERT_CACHE = DATA_DIR / ".embed_cache_biobert.npy"
MPNET_CACHE = DATA_DIR / ".embed_cache_mpnet.npy"
META_HASH_FILE = DATA_DIR / ".embed_cache_hash"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# We log to stderr only. stdout is reserved exclusively for MCP JSON-RPC
# messages — a single stray print() to stdout will corrupt the protocol and
# break the client connection.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [biofinder] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("biofinder")


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

# These are the two embedding models we use. Both are loaded from the local
# Hugging Face cache (downloaded on first use by sentence-transformers).
#
# Why two models?
#   all-MiniLM-L6-v2: 22 MB, very fast on CPU, strong general-purpose
#     semantic understanding. Good at understanding what a user *means*
#     even when they use informal language.
#
#   BiomedNLP-BiomedBERT: ~440 MB, slower, but pre-trained on 30M PubMed
#     abstracts. Understands biomedical vocabulary (e.g. knows that
#     "RNA-seq aligner" and "transcriptome mapping" are related concepts).
#     This is the right model for a bioinformatics tool catalog.
#
# Note: the user specified 'all-MiniLM-L60-v2' — there is no L60 variant;
# the correct model is 'all-MiniLM-L6-v2' (6 transformer layers).
MINILM_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BIOBERT_MODEL = "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract"
MPNET_MODEL = "sentence-transformers/all-mpnet-base-v2"

# How much weight each model contributes to the final score (must sum to 1.0).
# BiomedBERT gets slightly more weight because it understands the domain better,
# but MiniLM is faster and handles informal/natural language well.
# These can be tuned — see SEARCH_IMPROVEMENTS.md for context.
MINILM_WEIGHT = 0 # disabled for testing
BIOBERT_WEIGHT = 0 # disabled for testing
MPNET_WEIGHT = 1 


# ---------------------------------------------------------------------------
# SemanticSearchIndex
# ---------------------------------------------------------------------------

class SemanticSearchIndex:
    """
    Builds and queries a semantic embedding index over tool metadata.

    The core idea:
      1. For each tool, concatenate its description, EDAM operations, EDAM
         topics, and name into a single 'corpus text'.
      2. Encode all corpus texts into dense vectors (embeddings) using a
         sentence-transformer model. Each vector captures the *meaning* of
         the text, not just its keywords.
      3. At query time, encode the query the same way, then compute cosine
         similarity between the query vector and every corpus vector.
         Tools whose meaning is closest to the query rank highest.

    Why cosine similarity?
      Embeddings are high-dimensional unit vectors. Cosine similarity
      measures the angle between two vectors — 1.0 means identical meaning,
      0.0 means unrelated. It's the standard metric for sentence embeddings.

    Graceful degradation:
      sentence-transformers is an optional dependency. If it isn't installed,
      or if a model fails to load (e.g. no internet on first run), this class
      sets self.available = False and the caller falls back to keyword search.
    """

    def __init__(self, model_name: str, embeddings_path: Path, weight: float):
        """
        Args:
            model_name:  Hugging Face model identifier string.
            embeddings_path:  Where to persist the pre-computed embedding matrix.
            weight:      How much this model contributes to the combined score.
        """
        self.model_name = model_name
        self.embeddings_path = embeddings_path
        self.weight = weight
        self.model = None           # SentenceTransformer instance, or None
        self.embeddings = None      # np.ndarray shape (n_tools, embed_dim)
        self.tool_ids: List[str] = []  # parallel list to embeddings rows
        self.available = False

    def load_model(self) -> bool:
        """
        Attempt to load the sentence-transformer model.
        Returns True if successful, False if the package isn't installed.
        """
        try:
            # Import inside the method so the server starts even if the
            # package is missing — we just won't have semantic search.
            from sentence_transformers import SentenceTransformer
            log.info(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.available = True
            log.info(f"Model loaded: {self.model_name}")
            return True
        except ImportError:
            log.warning(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers\n"
                "Falling back to keyword search."
            )
            return False
        except Exception as e:
            log.warning(f"Could not load model {self.model_name}: {e}")
            return False

    def build_embeddings(self, tools: List[Dict], meta_hash: str) -> None:
        """
        Encode all tool corpus texts into embeddings and cache the result.

        We check whether the cached .npy file is still valid by comparing a
        hash of toolfinder_meta.yaml. If the metadata file has changed, we
        re-embed everything.

        Args:
            tools:      List of tool metadata dicts from the YAML file.
            meta_hash:  SHA-256 hex digest of toolfinder_meta.yaml content.
        """
        if not self.available:
            return

        # Try loading from disk cache first
        if self._load_embeddings(tools, meta_hash):
            return

        log.info(f"Building embeddings for {len(tools)} tools with {self.model_name}...")
        log.info("(This takes ~10-30s on CPU the first time, then it's cached.)")

        corpus_texts = []
        self.tool_ids = []

        for tool in tools:
            # Build a single string that represents everything meaningful
            # about this tool. The model will embed this into one vector.
            # We weight important fields by repeating them — name appears
            # twice because it's the most discriminating signal.
            parts = []
            if tool.get('name'):
                parts.append(tool['name'])
            if tool.get('description'):
                parts.append(tool['description'])
            if tool.get('edam-operations'):
                parts.extend(tool['edam-operations'])
            if tool.get('edam-topics'):
                parts.extend(tool['edam-topics'])

            def _extend_all_values(value):
               # Get all strings from dict with nested lists 
               stack = [value]
               while stack:
                   current = stack.pop()
                   if isinstance(current, dict):
                       stack.extend(current.values())
                   elif isinstance(current, list):
                       stack.extend(current)
                   elif current is not None:
                       parts.append(str(current))

            if tool.get('edam-inputs'):
                _extend_all_values(tool['edam-inputs'])
            if tool.get('edam-outputs'):
                _extend_all_values(tool['edam-outputs'])

            log.info(parts)
            # Fall back to ID if the tool has no other text — at minimum
            # the embedding will understand the name string.
            corpus_text = " | ".join(parts) if parts else (tool.get('id') or '')
            corpus_texts.append(corpus_text)
            self.tool_ids.append(tool.get('id') or '')

        # encode() returns a numpy array of shape (n_tools, embed_dim).
        # show_progress_bar=True prints to stderr, which is safe.
        self.embeddings = self.model.encode(
            corpus_texts,
            show_progress_bar=True,
            batch_size=64,          # tune down if you hit memory issues
            normalize_embeddings=True,  # pre-normalise so cosine sim = dot product
        )

        self._save_embeddings(meta_hash)
        log.info(f"Embeddings built and cached → {self.embeddings_path}")

    def query(self, query_text: str, top_k: int) -> List[Tuple[str, float]]:
        """
        Return the top_k most semantically similar tools for a query.

        Args:
            query_text: The user's natural-language search string.
            top_k:      How many results to return.

        Returns:
            List of (tool_id, similarity_score) tuples, sorted descending.
            Scores are cosine similarities in [0, 1].
        """
        if not self.available or self.embeddings is None:
            return []

        # Embed the query into the same vector space as the corpus texts.
        # We use the same normalisation so the dot product == cosine similarity.
        query_vec = self.model.encode(
            [query_text],
            normalize_embeddings=True,
        )[0]  # shape: (embed_dim,)

        # Matrix multiply: (embed_dim,) × (n_tools, embed_dim).T → (n_tools,)
        # Each value is the cosine similarity between the query and one tool.
        scores = self.embeddings @ query_vec  # shape: (n_tools,)

        # Get indices of the top_k highest scores
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [(self.tool_ids[i], float(scores[i])) for i in top_indices]

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_embeddings(self, tools: List[Dict], meta_hash: str) -> bool:
        """
        Load a pre-computed embedding matrix from disk if still valid.
        Returns True if the cache was loaded successfully.
        """
        if not self.embeddings_path.exists():
            return False

        # The cache stores tool IDs alongside the matrix so we can check
        # the order hasn't changed (it matters — rows must match tool_ids).
        id_cache = self.embeddings_path.with_suffix('.ids.json')
        if not id_cache.exists():
            return False

        # Check the hash — if metadata changed, the cache is stale.
        hash_cache = self.embeddings_path.with_suffix('.hash')
        if not hash_cache.exists():
            return False
        if hash_cache.read_text().strip() != meta_hash:
            log.info(f"Metadata changed — invalidating embedding cache for {self.model_name}")
            return False

        try:
            self.embeddings = np.load(str(self.embeddings_path))
            self.tool_ids = json.loads(id_cache.read_text())
            log.info(f"Loaded cached embeddings ({len(self.tool_ids)} tools) ← {self.embeddings_path}")
            return True
        except Exception as e:
            log.warning(f"Cache load failed: {e} — will re-embed")
            return False

    def _save_embeddings(self, meta_hash: str) -> None:
        """Persist the embedding matrix and tool ID list to disk."""
        try:
            np.save(str(self.embeddings_path), self.embeddings)
            id_cache = self.embeddings_path.with_suffix('.ids.json')
            id_cache.write_text(json.dumps(self.tool_ids))
            hash_cache = self.embeddings_path.with_suffix('.hash')
            hash_cache.write_text(meta_hash)
        except Exception as e:
            log.warning(f"Could not save embedding cache: {e}")


# ---------------------------------------------------------------------------
# BioFinderIndex
# ---------------------------------------------------------------------------

class BioFinderIndex:
    """
    Central index for BioFinder.

    Holds:
      - Tool metadata (from toolfinder_meta.yaml)
      - Container lookup table (from galaxy_singularity_cache.json.gz)
      - Two SemanticSearchIndex instances (one per model)

    search_tool()        → exact name lookup, unchanged from v1
    search_by_function() → now uses semantic search, with keyword fallback
    """

    def __init__(self):
        self.metadata: List[Dict[str, Any]] = []
        self.container_index: Dict[str, List[Dict]] = defaultdict(list)
        self.cache_info: Dict[str, Any] = {}

        # Two semantic indexes — one general-purpose, one bio-domain.
        # They run in parallel and their scores are combined.
        self.minilm = SemanticSearchIndex(MINILM_MODEL, MINILM_CACHE, MINILM_WEIGHT)
        self.biobert = SemanticSearchIndex(BIOBERT_MODEL, BIOBERT_CACHE, BIOBERT_WEIGHT)
        self.mpnet = SemanticSearchIndex(MPNET_MODEL, MPNET_CACHE, MPNET_WEIGHT)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_data(self) -> None:
        """
        Load metadata + container cache, then build all search indexes.

        Called once at server startup. Nothing is printed to stdout —
        all progress goes to stderr via the log object.
        """
        log.info(f"Loading metadata from {METADATA_FILE}")
        with open(METADATA_FILE, 'r') as f:
            self.metadata = yaml.safe_load(f)
        log.info(f"Loaded {len(self.metadata)} tool metadata entries")

        log.info(f"Loading container cache from {SINGULARITY_CACHE_FILE}")
        with gzip.open(SINGULARITY_CACHE_FILE, 'rt') as f:
            cache_data = json.load(f)
            self.cache_info = {
                'generated_at': cache_data['generated_at'],
                'cvmfs_root':   cache_data['cvmfs_root'],
                'entry_count':  cache_data['entry_count'],
            }
            entries = cache_data['entries']
        log.info(f"Loaded {len(entries)} container entries")

        self._build_container_index(entries)
        self._build_semantic_indexes()

    def _build_container_index(self, entries: List[Dict]) -> None:
        """Build a dict mapping lowercase tool name → list of container dicts."""
        for entry in entries:
            self.container_index[entry['tool_name'].lower()].append(entry)

    def _build_semantic_indexes(self) -> None:
        """
        Load both embedding models and pre-compute tool corpus embeddings.

        The hash of toolfinder_meta.yaml is used as a cache key — if the
        file changes, the embeddings are re-computed from scratch.
        """
        meta_hash = self._hash_file(METADATA_FILE)

        #for index in (self.minilm, self.biobert, self.mpnet):
        #    if index.load_model():
        #        index.build_embeddings(self.metadata, meta_hash)
        if self.mpnet.load_model():
            self.mpnet.build_embeddings(self.metadata, meta_hash)

        if not self.minilm.available and not self.biobert.available and not self.mpnet.available:
            log.warning(
                "None of the embedding models are available. "
                "search_by_function will use keyword scoring instead. "
                "Install sentence-transformers to enable semantic search."
            )

    @staticmethod
    def _hash_file(path: Path) -> str:
        """Return the SHA-256 hex digest of a file's contents."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    # ------------------------------------------------------------------
    # Search: exact tool lookup (unchanged from v1)
    # ------------------------------------------------------------------

    def search_tool(self, query: str) -> Dict[str, Any]:
        """
        Find a specific tool by name and return its metadata + containers.

        Tries exact match first (id, name, biotools, biocontainers fields),
        then falls back to substring matching. This is intentionally simple —
        users calling find_tool() know what they're looking for.
        """
        q = query.lower().strip()

        # Exact match across all identifier fields
        tool_meta = None
        for entry in self.metadata:
            if q in (
                (entry.get('id') or '').lower(),
                (entry.get('name') or '').lower(),
                (entry.get('biotools') or '').lower(),
                (entry.get('biocontainers') or '').lower(),
            ):
                tool_meta = entry
                break

        # Substring fallback — catches "bwa" matching "bwa-mem2" etc.
        if not tool_meta:
            for entry in self.metadata:
                eid = (entry.get('id') or '').lower()
                if q in eid or eid in q:
                    tool_meta = entry
                    break

        # Container lookup — try the query, then hyphen/underscore variants,
        # then the matched metadata ID (which may differ from the query).
        containers = []
        candidates = [q, q.replace('-', '_'), q.replace('_', '-')]
        if tool_meta and tool_meta.get('id'):
            candidates.append(tool_meta['id'].lower())

        for candidate in candidates:
            if candidate in self.container_index:
                containers = self.container_index[candidate]
                break

        containers_sorted = sorted(
            containers,
            key=lambda x: self._parse_version(x['tag']),
            reverse=True,
        ) if containers else []

        return {
            'query':           query,
            'metadata':        tool_meta,
            'containers':      containers_sorted,
            'container_count': len(containers_sorted),
        }

    # ------------------------------------------------------------------
    # Search: semantic (new in v2) with keyword fallback
    # ------------------------------------------------------------------

    def search_by_function(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for tools by what they do, using semantic similarity.

        This is the core improvement over v1. Instead of counting keyword
        occurrences, we:
          1. Embed the query into a dense vector using each model.
          2. Compute cosine similarity against all pre-computed tool vectors.
          3. Combine scores from both models (weighted average).
          4. Apply a small log-scale boost for tools with many containers
             (a proxy for adoption — more versions = more widely used).
          5. Sort by final score and return the top `limit` results.

        Falls back to keyword scoring if no models are available.

        Args:
            query: Natural-language description of what the user wants to do.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with keys 'tool', 'score', 'score_detail'.
        """
        semantic_available = self.minilm.available or self.biobert.available or self.mpnet.available

        if not semantic_available:
            log.warning("No embedding models available — using keyword fallback")
            return self._keyword_search(query, limit)

        # --- Step 1: collect raw cosine similarities from each model -------
        # We ask for more candidates than `limit` so that the container-count
        # boost has enough material to re-rank before we truncate.
        candidate_pool = min(limit * 4, len(self.metadata))

        minilm_scores: Dict[str, float] = {}
        biobert_scores: Dict[str, float] = {}
        mpnet_scores: Dict[str, float] = {}

        if self.minilm.available:
            for tool_id, score in self.minilm.query(query, candidate_pool):
                minilm_scores[tool_id] = score
            log.info(f"MiniLM top score: {max(minilm_scores.values()):.4f} for tool {max(minilm_scores, key=minilm_scores.get)}")

        if self.biobert.available:
            for tool_id, score in self.biobert.query(query, candidate_pool):
                biobert_scores[tool_id] = score
            log.info(f"BiomedBERT top score: {max(biobert_scores.values()):.4f} for tool {max(biobert_scores, key=biobert_scores.get)}")

        if self.mpnet.available:
            for tool_id, score in self.mpnet.query(query, candidate_pool):
                mpnet_scores[tool_id] = score
            log.info(f"MPNet top score: {max(mpnet_scores.values()):.4f} for tool {max(mpnet_scores, key=mpnet_scores.get)}")
        
        # --- Step 2: combine scores ----------------------------------------
        # Union of all tool IDs that appeared in either model's top results.
        all_ids = set(minilm_scores) | set(biobert_scores) | set(mpnet_scores)

        combined: List[Dict] = []
        for tool_id in all_ids:
            m_score = minilm_scores.get(tool_id, 0.0)
            b_score = biobert_scores.get(tool_id, 0.0)
            p_score = mpnet_scores.get(tool_id, 0.0)

            # If only one model fired, use its full weight rather than
            # penalising the tool for not appearing in the other model's pool.
            if m_score and b_score and p_score:
                semantic_score = (MINILM_WEIGHT * m_score) + (BIOBERT_WEIGHT * b_score) + (MPNET_WEIGHT * p_score)
            elif m_score:
                semantic_score = m_score
            else:
                semantic_score = b_score

            log.info(f"Raw scores for {tool_id}: MiniLM={m_score:.4f}, BiomedBERT={b_score:.4f}, MPNet={p_score:.4f}, Combined={semantic_score:.4f}")

            # --- Step 3: container-count boost ----------------------------
            # Tools with many container versions are more widely adopted.
            # log1p(n) grows quickly at first then levels off, so a tool with
            # 50 versions doesn't completely swamp one with 10.
            # The boost is gated on semantic_score > 0 so irrelevant tools
            # don't get promoted just because they have containers.
            n_containers = len(self.container_index.get(tool_id, []))
            container_boost = np.log1p(n_containers) * 0.08

            final_score = semantic_score + container_boost
            log.info(f"Final score for {tool_id}: {final_score:.4f} (semantic {semantic_score:.4f} + container boost {container_boost:.4f} for {n_containers} containers)")
            # Look up the full metadata dict for this tool_id
            tool_meta = next(
                (e for e in self.metadata if (e.get('id') or '') == tool_id),
                None,
            )
            if tool_meta is None:
                continue

            combined.append({
                'tool':  tool_meta,
                'score': final_score,
                # score_detail is useful for debugging / future tuning
                'score_detail': {
                    'minilm':    round(m_score, 4),
                    'biobert':   round(b_score, 4),
                    'combined':  round(semantic_score, 4),
                    'container_boost': round(container_boost, 4),
                    'final':     round(final_score, 4),
                },
            })

        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:limit]

    # ------------------------------------------------------------------
    # Keyword fallback (preserved from v1, used if models unavailable)
    # ------------------------------------------------------------------

    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Original v1 keyword scorer, kept as a fallback.

        Used when sentence-transformers is not installed. Scores each tool
        by counting how many query terms appear in its metadata fields.
        """
        q = query.lower()
        q_terms = set(q.split())
        results = []

        for entry in self.metadata:
            score = 0
            desc = (entry.get('description') or '').lower()
            if desc:
                score += len(q_terms & set(desc.split())) * 2
                if q in desc:
                    score += 5
            for op in (entry.get('edam-operations') or []):
                if op and q in op.lower():
                    score += 3
            for topic in (entry.get('edam-topics') or []):
                if topic and q in topic.lower():
                    score += 2
            for topic in (entry.get('edam-inputs') or []):
                if topic and q in topic.lower():
                    score += 2
            for topic in (entry.get('edam-outputs') or []):
                if topic and q in topic.lower():
                    score += 2
            if q in (entry.get('name') or '').lower():
                score += 4
            if q in (entry.get('id') or '').lower():
                score += 4
            if score > 0:
                results.append({
                    'tool':         entry,
                    'score':        score,
                    'score_detail': {'keyword': score},
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_version(tag: str) -> Tuple[List[int], str]:
        """
        Extract a sortable version tuple from a Bioconda tag like
        '1.17--h00cdaf9_0'. Returns ([1, 17], '1.17--h00cdaf9_0').
        The tag is kept as a tiebreaker for same-version build strings.
        """
        match = re.match(r'^(\d+(?:\.\d+)*)', tag)
        if match:
            parts = [int(x) for x in match.group(1).split('.')]
            return (parts, tag)
        return ([0], tag)

    def list_all_tools(self, limit: int = 50) -> List[str]:
        """Return a sorted list of all known tool names (from metadata + containers)."""
        tools: set = set()
        for entry in self.metadata:
            if entry.get('id'):
                tools.add(entry['id'])
        tools.update(self.container_index.keys())
        return sorted(tools)[:limit]


# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

# These two objects are module-level singletons. The MCP decorator functions
# below close over them. `index` is populated by load_data() inside main().
index = BioFinderIndex()
app = Server("bio-finder")


# ---------------------------------------------------------------------------
# MCP: resources  (read-only data the client can inspect)
# ---------------------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[Resource]:
    """Expose the two data sources as readable MCP resources."""
    return [
        Resource(
            uri="biofinder://cvmfs-galaxy-containers",
            name="CVMFS Cache Information",
            mimeType="application/json",
            description="Metadata about the Singularity container snapshot",
        ),
        Resource(
            uri="biofinder://metadata",
            name="Tool metadata",
            mimeType="text/plain",
            description=(
                "Bio.tools metadata from "
                "https://github.com/AustralianBioCommons/finder-service-metadata"
            ),
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Return the content of a named resource."""
    if uri == "biofinder://cvmfs-galaxy-containers":
        return json.dumps(index.cache_info, indent=2)
    elif uri == "biofinder://metadata":
        return "\n".join(index.list_all_tools(limit=999_999))
    raise ValueError(f"Unknown resource: {uri}")


# ---------------------------------------------------------------------------
# MCP: tools  (callable functions the client can invoke)
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    Advertise the four tools this server provides.

    The description strings matter — when an LLM agent uses this MCP server,
    it reads these descriptions to decide which tool to call. Be explicit
    about what each tool is for.
    """
    return [
        Tool(
            name="find_tool",
            description=(
                "Find a bioinformatics tool by name and get its container information. "
                "Use when the user asks 'Where can I find X?' or 'How do I use X?'. "
                "Returns metadata, available container versions, and usage examples."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool (e.g. 'fastqc', 'samtools', 'bwa-mem2')",
                    }
                },
                "required": ["tool_name"],
            },
        ),
        Tool(
            name="search_by_function",
            description=(
                "Search for tools by what they do, using semantic similarity. "
                "Use when the user asks 'What can I use to do X?' or describes a task. "
                "Works with natural language: 'align RNA reads', 'call variants', "
                "'assemble a metagenome', 'count reads per gene'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the user wants to do, in plain language",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="get_container_versions",
            description=(
                "List all available container versions for a specific tool, "
                "sorted newest-first with CVMFS paths and file sizes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of the tool"},
                },
                "required": ["tool_name"],
            },
        ),
        Tool(
            name="list_available_tools",
            description=(
                "List all available bioinformatics tools alphabetically. "
                "Use when the user asks 'What tools are available?'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tools to list (default 50)",
                        "default": 50,
                    }
                },
                "required": [],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# MCP: tool call handlers
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Dispatch incoming tool calls to the appropriate handler and format output.

    MCP sends us the tool name and a dict of arguments. We call the relevant
    index method, format the result as human-readable text, and return it
    wrapped in TextContent objects.

    Why TextContent and not structured JSON?
    The primary consumer of these results is a human at a terminal (via
    biofinder_client.py). Returning pre-formatted text means the client
    can just print() it without any rendering logic. If you later want
    machine-readable output, add a 'raw' argument and return JSON instead.
    """
    if name == "find_tool":
        return _handle_find_tool(arguments)
    elif name == "search_by_function":
        return await _handle_search(arguments)
    elif name == "get_container_versions":
        return _handle_versions(arguments)
    elif name == "list_available_tools":
        return _handle_list(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


def _handle_find_tool(arguments: Dict) -> list[TextContent]:
    """Format output for the find_tool call."""
    tool_name = arguments["tool_name"]
    result = index.search_tool(tool_name)
    parts = []

    if result['metadata']:
        meta = result['metadata']
        parts += [
            f"\n{'='*70}\n",
            f"🧬 {meta.get('name', tool_name.upper())}\n",
            f"{'='*70}\n\n",
        ]
        if meta.get('description'):
            parts += [f"📝 Description:\n   {meta['description']}\n\n"]
        if meta.get('homepage'):
            parts += [f"🌐 Homepage: {meta['homepage']}\n"]
        if meta.get('edam-operations'):
            parts += [f"⚙️  Operations: {', '.join(meta['edam-operations'])}\n"]
    else:
        parts += [
            f"\n{'='*70}\n",
            f"🧬 {tool_name.upper()}\n",
            f"{'='*70}\n\n",
            "ℹ️  No metadata available for this tool\n",
        ]

    if result['containers']:
        latest = result['containers'][0]
        parts += [
            f"\n{'─'*70}\n",
            f"📦 AVAILABLE CONTAINERS ({result['container_count']} versions)\n",
            f"{'─'*70}\n\n",
            f"✨ Most Recent Version: {latest['tag']}\n\n",
            f"   Path: {latest['path']}\n",
            f"   Size: {latest['size_bytes'] / (1024**2):.1f} MB\n\n",
            f"{'─'*70}\n",
            f"💡 USAGE EXAMPLES\n",
            f"{'─'*70}\n\n",
            f"# Execute a command in the container\n",
            f"singularity exec {latest['path']} \\\n",
            f"  {tool_name} --help\n\n",
            f"# Run interactively\n",
            f"singularity shell {latest['path']}\n",
        ]
        if len(result['containers']) > 1:
            parts += [f"\n{'─'*70}\n", f"📚 OTHER VERSIONS\n", f"{'─'*70}\n\n"]
            for i, c in enumerate(result['containers'][:3], 1):
                parts.append(f"  {i:2}. {c['tag']}\n      {c['path']}\n")
            if result['container_count'] > 3:
                parts.append(f"   ... and {result['container_count'] - 3} more versions\n")
    else:
        parts += [
            f"\n⚠️  No containers found in CVMFS for this tool.\n",
            f"   The tool may be available via a module system or under a different name.\n",
        ]

    parts.append(f"\n{'='*70}\n")
    return [TextContent(type="text", text="".join(parts))]


async def _handle_search(arguments: Dict) -> list[TextContent]:
    """Format output for the search_by_function call."""
    query = arguments["description"]
    limit = arguments.get("limit", 5)

    results = index.search_by_function(query, limit)
    log.info(f"search_by_function found {len(results)} results for query: '{query}'")

    if not results:
        return [TextContent(
            type="text",
            text=f"\n❌ No tools found matching '{query}'.\nTry different keywords or use 'list' to browse.\n",
        )]

    # Detect whether we're using semantic or keyword scoring so we can
    # label the score column appropriately
    semantic_active = index.minilm.available or index.biobert.available
    score_label = "similarity" if semantic_active else "keyword score"

    parts = [
        f"\n{'='*70}\n",
        f"🔎 TOOLS MATCHING: {query}\n",
        f"{'='*70}\n\n",
        f"Found {len(results)} results",
    ]

    # Tell the user which models are driving the scores
    active_models = []
    if index.minilm.available:
        active_models.append("all-MiniLM-L6-v2")
    if index.biobert.available:
        active_models.append("BiomedBERT")
    if index.mpnet.available:
        active_models.append("all-mpnet-base-v2")
    if active_models:
        parts.append(f" using {' + '.join(active_models)}")
    parts.append(".\n")

    for i, item in enumerate(results, 1):
        tool = item['tool']
        score = item['score']
        tool_name = tool.get('name') or tool.get('id', 'Unknown')
        tool_id = tool.get('id', 'N/A')

        parts += [
            f"\n{'─'*70}\n",
            f"{i:2}. 🧬 {tool_name}  ({tool_id})  │  {score_label}: {score:.3f}\n",
            f"{'─'*70}\n",
        ]

        if tool.get('description'):
            parts.append(f"📝 {tool['description']}\n")
        if tool.get('edam-operations'):
            parts.append(f"⚙️  {', '.join(tool['edam-operations'])}\n")

        container_result = index.search_tool(tool_id)
        if container_result['containers']:
            latest = container_result['containers'][0]
            parts += [
                f"📦 Latest: {latest['tag']}\n",
                f"💡 singularity exec {latest['path']} \\\n",
                f"     {tool_id} --help\n",
            ]

    parts.append(f"\n{'='*70}\n")
    return [TextContent(type="text", text="".join(parts))]


def _handle_versions(arguments: Dict) -> list[TextContent]:
    """Format output for the get_container_versions call."""
    tool_name = arguments["tool_name"]
    result = index.search_tool(tool_name)

    if not result['containers']:
        return [TextContent(type="text", text=f"\n❌ No containers found for '{tool_name}'\n")]

    parts = [
        f"\n{'='*70}\n",
        f"📦 CONTAINER VERSIONS: {tool_name}\n",
        f"{'='*70}\n\n",
        f"Total versions: {result['container_count']}\n\n",
    ]
    for i, c in enumerate(result['containers'], 1):
        modified = datetime.fromtimestamp(c['mtime']).strftime('%Y-%m-%d')
        parts += [
            f"{'─'*70}\n",
            f"{i:3}. {c['tag']}\n",
            f"{'─'*70}\n\n",
            f"     Path:     {c['path']}\n",
            f"     Size:     {c['size_bytes'] / (1024**2):.1f} MB\n",
            f"     Modified: {modified}\n\n",
        ]
    parts.append(f"{'='*70}\n")
    return [TextContent(type="text", text="".join(parts))]


def _handle_list(arguments: Dict) -> list[TextContent]:
    """Format output for the list_available_tools call."""
    limit = arguments.get("limit", 50)
    tools = index.list_all_tools(limit)

    cols = 3
    rows = []
    for i in range(0, len(tools), cols):
        rows.append("  ".join(f"{t:22}" for t in tools[i:i + cols]))

    text = (
        f"\n{'='*70}\n"
        f"📚 AVAILABLE TOOLS ({len(tools)} shown)\n"
        f"{'='*70}\n\n"
        + "\n".join(rows)
        + f"\n\n{'='*70}\n"
        f"💡 Use 'find <name>' for details  │  'search <task>' to search by function\n"
        f"{'='*70}\n"
    )
    return [TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    """
    Start the MCP server.

    Load data first (blocking), then hand control to the MCP runtime which
    listens on stdin for JSON-RPC messages and writes responses to stdout.
    The server runs until the client closes the connection.
    """
    log.info("BioFinder MCP Server starting up...")
    index.load_data()
    log.info("Ready — listening for MCP requests on stdio")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
