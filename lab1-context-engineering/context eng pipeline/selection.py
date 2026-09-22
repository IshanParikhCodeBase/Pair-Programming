"""Step 2 of the context pipeline: selection.

Clustering told us which chunks restate the same fact. Selection decides which
one of those chunks actually survives -- the rest are dropped, so only one
version of each fact reaches the model. This is also where the corpus's
planted stale values get (or don't get) resolved: if a cluster contains both
the current value and an old changelog value, the strategy below is what
decides which one wins.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clustering import DEFAULT_DISTANCE_THRESHOLD, cluster_chunks, group_by_cluster
from contextlab.embeddings import embed_texts, load_chunks

# Lower index = more authoritative. api-reference/configuration are living
# reference docs meant to always reflect current behavior; changelog is
# explicitly a history log (REDUNDANCY_MAP.md: "may not reflect current
# defaults"), so it's ranked last on purpose -- this is what lets selection
# resolve a stale-value trap instead of picking whichever chunk happens to be
# first in the cluster.
SOURCE_AUTHORITY = [
    "docs/api-reference.md",
    "docs/configuration.md",
    "src/client.py",
    "src/worker.py",
    "README.md",
    "docs/getting-started.md",
    "docs/faq.md",
    "docs/changelog.md",
]


def _authority_rank(source):
    try:
        return SOURCE_AUTHORITY.index(source)
    except ValueError:
        return len(SOURCE_AUTHORITY)  # unknown sources sort last


def select_most_authoritative(members):
    return min(members, key=lambda c: _authority_rank(c["source"]))


def select_most_detailed(members):
    return max(members, key=lambda c: len(c["text"]))


def select_shortest(members):
    return min(members, key=lambda c: len(c["text"]))


STRATEGIES = {
    "most_authoritative": select_most_authoritative,
    "most_detailed": select_most_detailed,
    "shortest": select_shortest,
}


def select_representatives(groups, strategy="most_authoritative"):
    """One chunk survives per cluster. Returns {cluster_id: chosen_chunk}."""
    pick = STRATEGIES[strategy]
    return {cid: pick(members) for cid, members in groups.items()}


# The four facts REDUNDANCY_MAP.md plants a stale changelog value for, used
# below to audit selection honestly rather than cherry-pick a success case.
STALE_TRAP_FACTS = {
    "rate limit":   ("docs/api-reference.md::2", "docs/changelog.md::2"),
    "payload size": ("docs/api-reference.md::4", "docs/changelog.md::4"),
    "retention":    ("docs/configuration.md::8", "docs/changelog.md::3"),
    "port":         ("docs/configuration.md::2", "docs/changelog.md::5"),
}


def audit_stale_traps(groups, survivors):
    id_to_cluster = {m["id"]: cid for cid, members in groups.items() for m in members}
    print("Stale-trap audit (does clustering + selection resolve each one?):\n")
    for fact, (current_id, stale_id) in STALE_TRAP_FACTS.items():
        current_cluster = id_to_cluster[current_id]
        stale_cluster = id_to_cluster[stale_id]
        if current_cluster != stale_cluster:
            print(f"  {fact:15s} NOT MERGED  -- clustering never grouped the current and "
                  f"stale chunks (they're in different clusters), so both still survive "
                  f"selection independently. Not resolved.")
            continue
        chosen = survivors[current_cluster]
        resolved = chosen["id"] != stale_id
        verdict = "RESOLVED" if resolved else "STILL STALE"
        print(f"  {fact:15s} {verdict:12s} -- cluster {current_cluster} merged both; "
              f"selection kept [{chosen['source']}] {chosen['id']}")
    print()


if __name__ == "__main__":
    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])
    labels, model = cluster_chunks(chunk_vecs, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)
    groups = group_by_cluster(chunks, labels)

    survivors = select_representatives(groups, strategy="most_authoritative")

    print(f"distance_threshold = {DEFAULT_DISTANCE_THRESHOLD}")
    print(f"Chunks before clustering: {len(chunks)}")
    print(f"Clusters after clustering: {len(groups)}")
    print(f"Chunks after selection: {len(survivors)}")
    dropped = len(chunks) - len(survivors)
    print(f"{dropped} redundant chunks dropped by selection "
          f"(kept the single best chunk per cluster)\n")

    audit_stale_traps(groups, survivors)
