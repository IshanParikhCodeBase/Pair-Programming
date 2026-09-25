"""Step 4 of the context pipeline: compression.

Even after clustering + selection + reranking, surviving chunks can still
share overlapping sentences -- e.g. two chunks about different facts might
both open with similar boilerplate. Compression is algorithmic, deterministic
sentence-level dedup: given an ordered list of chunks, drop any sentence
that's too similar to one already kept, from this chunk or any earlier one.
No LLM involved, so the same input always produces exactly the same output.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_WORD_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Tuned empirically against the post-selection (55-chunk) set. At 0.4-0.5,
# short generic phrases produce false-positive matches purely from shared
# filler words -- e.g. "Defaults to 3." vs "Defaults to 8080." share
# {"defaults", "to"} out of 3 words each (Jaccard 0.5) despite being two
# different facts. 0.6 is the highest threshold below which every confirmed
# drop is a genuine same-fact restatement (URL as prose vs. code constant,
# job states in backticks vs. bold, concurrency=4 and timeout=30 each stated
# twice), with no confirmed false positives.
OVERLAP_THRESHOLD = 0.6


def _split_sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _word_set(sentence):
    return set(_WORD_RE.findall(sentence.lower()))


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compress_chunks_with_report(chunks, overlap_threshold=OVERLAP_THRESHOLD):
    """Deterministic sentence-level dedup across an ordered list of chunks.

    Processes chunks in the given order. For each sentence, checks its word
    overlap (Jaccard) against every sentence already kept -- from this chunk
    or any earlier one -- and drops it if the overlap is >= overlap_threshold.

    Returns (compressed_chunks, drops):
      - compressed_chunks: new chunk dicts with compressed `text`; a chunk
        that becomes fully redundant (every sentence dropped) is dropped
        entirely.
      - drops: a list of (dropped_sentence, matched_sentence, score) for
        every sentence actually removed, for auditing/reporting.
    """
    seen = []  # (sentence_text, word_set) already kept, in order
    compressed = []
    drops = []

    for chunk in chunks:
        kept_sentences = []
        for sentence in _split_sentences(chunk["text"]):
            words = _word_set(sentence)
            best_match, best_score = None, 0.0
            for seen_text, seen_words in seen:
                score = _jaccard(words, seen_words)
                if score > best_score:
                    best_match, best_score = seen_text, score

            if best_score >= overlap_threshold:
                drops.append((sentence, best_match, best_score))
            else:
                kept_sentences.append(sentence)
                seen.append((sentence, words))

        if kept_sentences:
            new_chunk = dict(chunk)
            new_chunk["text"] = " ".join(kept_sentences)
            compressed.append(new_chunk)
        # else: chunk was fully redundant with earlier content -- dropped

    return compressed, drops


def compress_chunks(chunks, overlap_threshold=OVERLAP_THRESHOLD):
    return compress_chunks_with_report(chunks, overlap_threshold)[0]


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from clustering import DEFAULT_DISTANCE_THRESHOLD, cluster_chunks, group_by_cluster
    from selection import select_representatives
    from contextlab.embeddings import embed_texts, load_chunks

    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])
    labels, _ = cluster_chunks(chunk_vecs, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)
    groups = group_by_cluster(chunks, labels)
    survivors = list(select_representatives(groups, strategy="most_authoritative").values())

    print(f"Chunks entering compression (post cluster+select): {len(survivors)}")
    total_sentences = sum(len(_split_sentences(c["text"])) for c in survivors)
    before_chars = sum(len(c["text"]) for c in survivors)

    compressed, drops = compress_chunks_with_report(survivors)
    after_chars = sum(len(c["text"]) for c in compressed)
    dropped_content_chars = sum(len(s) for s, _, _ in drops)

    print(f"Chunks after compression: {len(compressed)}")
    print(f"Sentences dropped as redundant: {len(drops)} / {total_sentences}")
    print(f"  chars removed as genuine redundancy: {dropped_content_chars} "
          f"({100 * dropped_content_chars / before_chars:.1f}% of {before_chars})")
    print(f"  chars before -> after (includes whitespace normalization "
          f"from rejoining sentences): {before_chars} -> {after_chars} "
          f"({100 * (1 - after_chars / before_chars):.1f}% total)\n")

    print("Sentences actually dropped:")
    for sentence, match, score in drops:
        print(f"  [{score:.2f}] dropped: {sentence!r}")
        print(f"         matched: {match!r}")
    print()

    # Determinism check required by the brief: same input -> same output.
    compressed_again = compress_chunks(survivors)
    same = [c["text"] for c in compressed] == [c["text"] for c in compressed_again]
    print(f"Determinism check (run twice on identical input): {'PASS' if same else 'FAIL'}")
