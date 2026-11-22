"""
Help-docs search (RAG).

1. The help file is split into chunks: one per FAQ and one per policy.
2. Each chunk is turned into an embedding (a list of numbers that captures its meaning).
3. The embeddings are saved in data/index.json.
4. For a customer question we embed the question too and return the 3 closest chunks.

The index has only ~23 chunks, so a small JSON file and plain maths are enough.
"""

import json
import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HELP_FILE = DATA_DIR / "tiffingo_help.txt"
INDEX_FILE = DATA_DIR / "index.json"
EMBED_MODEL = "gemini-embedding-001"


_client_cache = None


def _client():
    # Keep one client alive (a throw-away client closes its connection when it is garbage collected).
    global _client_cache
    if _client_cache is None:
        _client_cache = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client_cache


def split_into_chunks(text: str) -> list[dict]:
    """One chunk per 'Q:' FAQ and one per 'Policy:' section."""
    chunks, current = [], None
    for line in text.splitlines():
        if line.startswith("Q:") or line.startswith("Policy:"):
            if current:
                chunks.append(current)
            title = re.sub(r"^(Q:|Policy:)\s*", "", line).strip()
            current = {"title": title, "text": line.strip()}
        elif current is not None and line.strip():
            if line.strip() in ("Policies", "Frequently asked questions"):
                continue
            current["text"] += "\n" + line.strip()
    if current:
        chunks.append(current)
    return chunks


def build_index() -> int:
    """Read the help file, embed every chunk and save data/index.json."""
    chunks = split_into_chunks(HELP_FILE.read_text(encoding="utf-8"))
    result = _client().models.embed_content(
        model=EMBED_MODEL,
        contents=[c["text"] for c in chunks],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    for chunk, emb in zip(chunks, result.embeddings):
        chunk["embedding"] = emb.values
    INDEX_FILE.write_text(json.dumps(chunks), encoding="utf-8")
    return len(chunks)


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def search(question: str, top_k: int = 3) -> list[dict]:
    """Return the top_k chunks that best match the question."""
    if not INDEX_FILE.exists():  # build automatically if the index is missing
        build_index()
    chunks = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    q = _client().models.embed_content(
        model=EMBED_MODEL,
        contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    ).embeddings[0].values
    ranked = sorted(chunks, key=lambda c: _cosine(q, c["embedding"]), reverse=True)
    return [{"source": c["title"], "text": c["text"]} for c in ranked[:top_k]]
