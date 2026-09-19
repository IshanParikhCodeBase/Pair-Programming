# Nimbus Corpus — for the Context Engineering Lab

This is the messy documentation corpus for the lab. It's the docs for a made-up
task-queue service called **Nimbus**. The facts are internally consistent, but
they're stated redundantly across many files — which is exactly what your context
pipeline is built to clean up.

## What's here

```
nimbus-corpus/
├── README.md              # the "product" README (part of the corpus)
├── docs/
│   ├── getting-started.md # tutorial
│   ├── api-reference.md   # formal API docs
│   ├── faq.md             # conversational Q&A
│   ├── configuration.md   # self-hosting config reference
│   └── changelog.md       # release history — CONTAINS STALE VALUES on purpose
├── src/
│   ├── client.py          # facts embedded in docstrings/comments
│   └── worker.py          # facts embedded in docstrings/comments
├── chunk_corpus.py        # reference chunker -> chunks.jsonl (74 chunks)
├── chunks.jsonl           # pre-chunked corpus, ready to embed
├── gold_questions.json    # starter gold test set (edit/expand this)
├── REDUNDANCY_MAP.md      # ANSWER KEY — where every fact lives (instructors)
└── CORPUS_README.md       # this file
```

## The two kinds of messiness

1. **Redundancy.** Every key fact (rate limit, timeout, payload size, job states,
   etc.) appears in three or more files, phrased differently each time — a formal
   table row in the API reference, a casual sentence in the FAQ, a code comment in
   `src/`. Your **clustering** step should group these; your **selection** step
   should keep one good representative.

2. **Stale values.** `docs/changelog.md` records *older* values of some facts (the
   rate limit was once 60/min, retention was once 3 days, the port was once 3000).
   These are real parts of the corpus. A pipeline whose selection step prefers the
   *most recent* / *most authoritative* source will answer correctly; a naive one
   that grabs whichever chunk is most similar may return the outdated number.

## Quick start

```bash
# (Re)generate the chunks — already included as chunks.jsonl
python chunk_corpus.py --stats

# Each line of chunks.jsonl is: {"id": ..., "source": ..., "text": ...}
```

Embed `chunks.jsonl`, and you have your retrieval corpus. From there, follow the
lab: build the naive baseline, then add clustering → selection → reranking →
compression, measuring tokens and cost at each step.

## Note for instructors

`REDUNDANCY_MAP.md` is the answer key. It lists every canonical fact, its current
value, everywhere it appears, and the stale value hidden in the changelog. Keep it
back from students until after the lab, or use it to grade.
