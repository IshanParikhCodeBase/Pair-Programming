"""Step 3 of the context pipeline: reranking with Maximal Marginal Relevance.

Plain top-K retrieval picks the K chunks most similar to the question, which
tends to cluster around one narrow angle. MMR balances relevance against
diversity: each pick is scored on how relevant it is AND how different it is
from what's already been picked, so the final set covers more ground instead
of several near-duplicate takes on the same idea.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from contextlab.embeddings import embed_query


def mmr(query_vec, candidates, candidate_vecs, k=15, lambda_param=0.7):
    """Maximal Marginal Relevance selection.

    candidates/candidate_vecs must already be L2-normalized (so a dot product
    is a cosine similarity). Returns a list of (chunk, relevance_score) in
    selection order -- the chunk picked first is most relevant overall; each
    later pick trades some relevance for staying different from what's
    already selected, weighted by lambda_param.
    """
    k = min(k, len(candidates))
    relevance = candidate_vecs @ query_vec

    selected = [int(np.argmax(relevance))]
    remaining = [i for i in range(len(candidates)) if i != selected[0]]

    while remaining and len(selected) < k:
        best_i, best_score = None, -np.inf
        for i in remaining:
            sim_to_selected = max(float(candidate_vecs[i] @ candidate_vecs[j]) for j in selected)
            # 70% focus on relevance and 30% on similarity 
            score = lambda_param * relevance[i] - (1 - lambda_param) * sim_to_selected
            if score > best_score:
                best_i, best_score = i, score
        selected.append(best_i)
        remaining.remove(best_i)

    return [(candidates[i], float(relevance[i])) for i in selected]


def rerank(question, candidates, candidate_vecs, k=15, lambda_param=0.7):
    query_vec = embed_query(question)
    return mmr(query_vec, candidates, candidate_vecs, k=k, lambda_param=lambda_param)


if __name__ == "__main__":
    # Sanity check: lambda=1.0 (pure relevance, same as plain top-K) vs
    # lambda=0.7 (the brief's default, room for diversity) on a real question,
    # over the already cluster+select-reduced chunk set.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from clustering import DEFAULT_DISTANCE_THRESHOLD, cluster_chunks, group_by_cluster
    from selection import select_representatives
    from contextlab.embeddings import embed_texts, load_chunks

    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])
    labels, _ = cluster_chunks(chunk_vecs, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)
    groups = group_by_cluster(chunks, labels)
    survivors = select_representatives(groups, strategy="most_authoritative")
    pipeline_chunks = list(survivors.values())
    pipeline_vecs = embed_texts([c["text"] for c in pipeline_chunks])

    question = "What is the rate limit for a single API key?"
    print(f"Question: {question}")
    print(f"Candidate pool: {len(pipeline_chunks)} chunks (post cluster+select)\n")

    print("=== k=5 (small pool: diversity pressure has room to matter) ===\n")
    for lam, label in [(1.0, "lambda=1.0 (pure relevance, = plain top-K)"),
                        (0.7, "lambda=0.7 (brief's default)"),
                        (0.5, "lambda=0.5 (stronger diversity push)")]:
        print(f"--- {label} ---")
        results = rerank(question, pipeline_chunks, pipeline_vecs, k=5, lambda_param=lam)
        for chunk, score in results:
            preview = chunk["text"].replace("\n", " ")[:70]
            print(f"  relevance={score:.3f}  [{chunk['source']}]  {preview}...")
        print()

    # Does reranking actually drop the stale changelog chunk from the context
    # at the pipeline's real k=15, where MMR has much more room to include
    # everything and the diversity penalty has far less pressure to apply?
    print("=== k=15 (the pipeline's actual TOP_K) -- does the stale rate-limit "
          "chunk survive? ===\n")
    stale_id = "docs/changelog.md::2"
    for lam in (1.0, 0.7, 0.5):
        results = rerank(question, pipeline_chunks, pipeline_vecs, k=15, lambda_param=lam)
        included = stale_id in [c["id"] for c, _ in results]
        print(f"  lambda={lam}  stale chunk ({stale_id}) included = {included}")
    print("\n  At k=15 there's enough room for everything even mildly relevant, so "
          "MMR mostly just reorders rather than excludes -- the stale-trap chunk "
          "clustering/selection missed still reaches the model regardless of "
          "lambda at this k. The exclusion effect only shows up above at the "
          "tighter k=5, where MMR genuinely has to trade something away.")
