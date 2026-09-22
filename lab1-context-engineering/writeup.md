# Lab Write-up: Engineering the Context Window

## Phase 0 — Token budget note

**The budget.** Claude Haiku 4.5's context window is 200,000 tokens total, shared
across three things: the system prompt, the retrieved context, and headroom left
for the model's output. Our naive agent's system prompt is ~65 tokens, and we cap
output at 1,024 tokens (`max_tokens` in `ClaudeHaikuModel`) — generous room for a
short factual answer, tiny next to the ceiling.

**What the naive agent actually spends.** Across the 14 real Claude Haiku 4.5 runs
(`results/naive_runs_haiku.jsonl`):

| | input tokens | output tokens |
|---|---|---|
| min | 960 | 5 |
| avg | 1,086.4 | 27.2 |
| max | 1,226 | 70 |

Average input is **~0.54% of the 200K budget**. The naive agent doesn't come close
to overflowing the window — at this corpus's scale, "does it fit" is a non-issue.

**Where it does overshoot: the corpus, not the token window.** The naive agent
retrieves the top 15 chunks per question out of a 74-chunk corpus — that's
**20.3% of the entire corpus stuffed into every single request**, most of it
redundant restatements of the same ~14 facts. The token window absorbs this
without complaint, which is exactly what makes the waste easy to miss: nothing
errors, nothing truncates, the bill just quietly includes 5-10x more input than a
clean answer needs.

**Why "it still fits" is the wrong takeaway.** Using the real per-request token
counts above, the corpus's real chunk lengths, and Haiku's actual tokenization
ratio (not an estimate — computed directly from `input_tokens` returned by the
API on these 14 requests: ~0.274 tokens/char), an average chunk costs **~61
tokens**. At that rate, naive-style retrieval (no clustering, no selection — just
grab everything and hope) could keep grabbing chunks up to roughly **~3,270**
before the 200K ceiling itself became the binding constraint — about 44x the size
of our current 74-chunk corpus. So a real production corpus would likely blow the
budget eventually, but a lab-scale toy corpus never gets there, and that's the
trap: **overflow is not where the naive agent's cost is being lost.** Its waste is
already fully paid for at 74 chunks — it's just invisible because nothing hard
fails yet. The `q1` request is a concrete example: retrieval pulled the current
rate-limit value *and* the stale 60/min value from the changelog into the same
15-chunk block, and the model got 3,481 characters of context to answer a
question whose true answer is four words ("100 requests per minute"). The
pipeline steps in Phase 1
(clustering → selection → reranking → compression) exist to fix exactly this —
cost and precision, not overflow.
