"""
Smoke tests for the semantic-cache fix.

Run from repo root AGAINST THE RUNNING DOCKER STACK:
    python -m pytest tests/test_cache_behavior.py -v -s

Requirements:
    - Docker stack is up (docker compose up -d --build)
    - Ollama has llama3.2 + nomic-embed-text pulled
"""
import os
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from backend.cache import (
    query_with_cache,
    get_from_chroma_cache,
    _sql_cache,
)


def _clear_in_memory_cache():
    _sql_cache.clear()


class TestCacheNotServedForDifferentQuestions:
    """Semantically different questions must NOT return cached results from each other."""

    def test_gibberish_not_cached(self):
        """Random characters like 'asda' should not get a Chroma hit."""
        _clear_in_memory_cache()
        # Prime the cache with a real question
        r1 = query_with_cache("How many patients were admitted last week?", session_id="test")
        assert r1["error"] == "", f"First query failed: {r1['error']}"

        # Gibberish should NOT match via Chroma
        chroma_hit = get_from_chroma_cache("asda")
        assert chroma_hit is None, (
            f"Chroma returned a hit for 'asda' — distance threshold is too loose. "
            f"Got SQL: {chroma_hit.get('sql')}"
        )

    def test_different_questions_not_cached(self):
        """Two semantically different questions should not share a Chroma hit."""
        _clear_in_memory_cache()
        r1 = query_with_cache("How many patients were admitted last week?", session_id="test")
        assert r1["error"] == "", f"First query failed: {r1['error']}"

        chroma_hit = get_from_chroma_cache("What was the name of the most recent patient?")
        assert chroma_hit is None, (
            f"Chroma returned a hit for a different question. "
            f"Got SQL: {chroma_hit.get('sql')}"
        )

    def test_same_question_IS_cached(self):
        """The exact same question should hit the Chroma cache."""
        _clear_in_memory_cache()
        question = "How many patients were admitted last week?"
        r1 = query_with_cache(question, session_id="test")
        assert r1["error"] == "", f"First query failed: {r1['error']}"

        # Clear in-memory so only Chroma can answer
        _clear_in_memory_cache()
        chroma_hit = get_from_chroma_cache(question)
        assert chroma_hit is not None, "Exact same question should hit Chroma cache"
        assert chroma_hit.get("from_cache") is True


class TestCacheFlow:
    """Verify the overall query_with_cache flow."""

    def test_first_call_not_from_cache(self):
        """A brand-new question should execute fresh (from_cache=False)."""
        _clear_in_memory_cache()
        # Use a unique question unlikely to be in Chroma already
        unique_q = f"How many visits happened on 2025-01-15? -- test_ts={time.time()}"
        result = query_with_cache(unique_q, session_id="test")
        assert result["from_cache"] is False, "First call should not be from cache"

    def test_second_identical_call_from_cache(self):
        """Repeating the same question should return from_cache=True."""
        _clear_in_memory_cache()
        question = "How many departments are there?"
        r1 = query_with_cache(question, session_id="test")
        assert r1["error"] == ""

        r2 = query_with_cache(question, session_id="test")
        assert r2["from_cache"] is True, "Second identical call should be from cache"
        assert r2["sql"] == r1["sql"], "Cached SQL should match original"
