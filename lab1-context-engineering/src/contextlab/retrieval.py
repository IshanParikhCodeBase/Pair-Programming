"""Cosine-similarity top-K retrieval over the corpus's chunk embeddings."""

import numpy as np

from .embeddings import embed_query, embed_texts, load_chunks


def cosine_similarity(query_vec, chunk_vecs):
    """Both are expected to already be L2-normalized (embeddings.py does this),
    so cosine similarity is just the dot product.
    """
    return chunk_vecs @ query_vec


def top_k(query, chunks, chunk_vecs, k=15):
    """Return the k chunks most similar to `query`, as a list of
    (chunk_dict, score) sorted by descending score.
    """
    query_vec = embed_query(query)
    scores = cosine_similarity(query_vec, chunk_vecs)
    top_idx = np.argsort(-scores)[:k]
    return [(chunks[i], float(scores[i])) for i in top_idx]


if __name__ == "__main__":
    # Sanity check: embed a couple of real gold questions and eyeball whether
    # the chunks that come back are actually the right ones.
    chunks = load_chunks()
    print(f"Embedding {len(chunks)} chunks (cached after first run)...")
    chunk_vecs = embed_texts([c["text"] for c in chunks])

    sample_questions = [
        "What is the rate limit for a single API key?",
        "Which job states are considered terminal?",
        "How long are completed jobs retained before being purged?",
    ]

    for question in sample_questions:
        print(f"\nQuestion: {question}")
        for chunk, score in top_k(question, chunks, chunk_vecs, k=5):
            preview = chunk["text"].replace("\n", " ")[:90]
            print(f"  {score:.3f}  [{chunk['source']}]  {preview}...")
