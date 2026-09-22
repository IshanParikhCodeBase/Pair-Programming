"""Step 1 of the context pipeline: clustering near-duplicate chunks.

Chunks that restate the same fact land close together in embedding space.
Agglomerative clustering groups them so selection (step 2) can keep just one
representative per fact instead of forwarding every restatement to the model.
"""

import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from contextlab.embeddings import embed_texts, load_chunks

# Tuned empirically against REDUNDANCY_MAP.md's known fact groups and the
# planted rate-limit/payload-size distractor pair (see naive_agent's sibling
# investigation notes). Below ~0.35, the distractor pair and other unrelated
# facts stay correctly separated; at 0.35-0.55 short code fragments in
# src/worker.py start chaining together (e.g. the retry-count fact wrongly
# merges with the per-attempt-timeout fact, since both are terse comments
# sharing "attempt"/"handler" vocabulary). 0.28 sits in the safe zone: it
# merges the real same-fact restatements without a single confirmed bad merge.
DEFAULT_DISTANCE_THRESHOLD = 0.28  # cosine distance


def cluster_chunks(chunk_vecs, distance_threshold=DEFAULT_DISTANCE_THRESHOLD):
    """Group chunk embeddings into clusters of near-duplicates.

    Returns (labels, model) -- labels[i] is the cluster id chunk i belongs to;
    model is the fitted AgglomerativeClustering instance, kept around so its
    merge tree can be visualized as a dendrogram.
    """
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
        compute_distances=True,
    )
    labels = model.fit_predict(chunk_vecs)
    return labels, model


def group_by_cluster(chunks, labels):
    """{cluster_id: [chunk, chunk, ...]}. A cluster with just one member had
    no near-duplicate; clusters with 2+ members are the redundancy we're
    about to remove in the selection step.
    """
    groups = {}
    for chunk, label in zip(chunks, labels):
        groups.setdefault(int(label), []).append(chunk)
    return groups


def _linkage_matrix(model):
    """Rebuild a scipy-style linkage matrix from a fitted
    AgglomerativeClustering model, for dendrogram plotting. Standard recipe
    from scikit-learn's own dendrogram example -- sklearn fits the tree but
    doesn't expose a ready-made linkage matrix directly.
    """
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count
    return np.column_stack([model.children_, model.distances_, counts]).astype(float)


def plot_dendrogram(chunks, model, distance_threshold, out_path):
    """Visualize the merge tree: every leaf is a chunk, every join is a merge
    at some cosine distance. The dashed line marks the chosen threshold --
    anything joined below the line becomes one cluster; anything joined above
    it stays separate. This is literally a picture of the merging.
    """
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram

    Z = _linkage_matrix(model)
    labels = [c["id"] for c in chunks]

    fig, ax = plt.subplots(figsize=(12, 16))
    dendrogram(
        Z,
        labels=labels,
        orientation="left",
        color_threshold=distance_threshold,
        above_threshold_color="#c3c2b7",
        ax=ax,
    )
    ax.axvline(distance_threshold, color="#e34948", linestyle="--", linewidth=1.5,
               label=f"threshold = {distance_threshold}")
    ax.set_xlabel("Cosine distance")
    ax.set_title(f"Chunk clustering merge tree (n={len(chunks)})", loc="left")
    ax.legend(loc="lower right", frameon=False)
    ax.tick_params(axis="y", labelsize=6)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"\nWrote dendrogram to {out_path}")


if __name__ == "__main__":
    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])

    threshold = DEFAULT_DISTANCE_THRESHOLD
    labels, model = cluster_chunks(chunk_vecs, distance_threshold=threshold)
    groups = group_by_cluster(chunks, labels)

    n_clusters = len(groups)
    print(f"distance_threshold = {threshold}")
    print(f"Chunks before clustering: {len(chunks)}")
    print(f"Chunks (clusters) after clustering: {n_clusters}")
    print(f"{len(chunks)} chunks -> {n_clusters} clusters "
          f"({len(chunks) - n_clusters} chunks merged away)\n")

    merged = {cid: members for cid, members in groups.items() if len(members) > 1}
    print(f"{len(merged)} clusters have 2+ members (the redundancy being removed):\n")
    for cid, members in sorted(merged.items(), key=lambda kv: -len(kv[1])):
        sources = ", ".join(m["source"] for m in members)
        preview = members[0]["text"].replace("\n", " ")[:70]
        print(f"  cluster {cid}  ({len(members)} chunks: {sources})")
        print(f"    e.g. \"{preview}...\"")

    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    plot_dendrogram(chunks, model, threshold, out_dir / "clustering_dendrogram.png")
