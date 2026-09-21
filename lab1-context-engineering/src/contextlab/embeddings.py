"""Turn text into vectors, so relatedness becomes a distance you can measure.

Thin wrapper around sentence-transformers (all-MiniLM-L6-v2). Results are cached
to disk keyed by a hash of the exact text, so re-running a script during
development doesn't re-embed the same 74 chunks every time.
"""

import hashlib
import json

import numpy as np

from . import config

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def _cache_path(texts):
    key = hashlib.sha256(
        (config.EMBEDDING_MODEL_NAME + "\n" + "\n".join(texts)).encode("utf-8")
    ).hexdigest()
    return config.EMBEDDING_CACHE_DIR / f"{key}.npy"


def embed_texts(texts):
    """Embed a list of strings, returning an (N, D) numpy array. Cached to disk
    as a whole batch, keyed by the exact list of texts passed in.
    """
    cache_path = _cache_path(texts)
    if cache_path.exists():
        return np.load(cache_path)

    model = _get_model()
    vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)

    config.EMBEDDING_CACHE_DIR.mkdir(exist_ok=True)
    np.save(cache_path, vectors)
    return vectors


def embed_query(text):
    """Embed a single string, returning a (D,) numpy array."""
    return embed_texts([text])[0]


def load_chunks():
    chunks = []
    with open(config.CHUNKS_PATH) as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks
