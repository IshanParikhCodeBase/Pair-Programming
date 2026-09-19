# Redundancy Map

This is the instructor/answer key for the Nimbus corpus. It documents the planted
redundancy so you can (a) verify your clustering step actually merges these, and
(b) build a gold test set with unambiguous correct answers. **Give this file to
graders, not to students** (or hand it out only after the lab).

The corpus is deliberately messy in two ways:

1. **Redundancy** — each canonical fact below is stated in several places, worded
   differently every time. This is the primary property the pipeline must handle:
   clustering should group the restatements, and selection should keep just one.
2. **Stale duplicates** — a few facts have an *older* value recorded in
   `docs/changelog.md`. These are legitimately part of the corpus (real changelogs
   keep history) and exist so the "most recent" / "most authoritative" selection
   strategy has something to decide. A naive pipeline that keeps the stale chunk
   will answer some questions wrong.

## Canonical facts and where they appear

| Fact | Current value | Appears in (worded differently each time) | Stale value planted in changelog |
| --- | --- | --- | --- |
| API base URL | `https://api.nimbusqueue.io/v1` | README, getting-started, api-reference, src/client.py | — |
| Authentication | API key as bearer token in `Authorization` header | README, getting-started, api-reference, configuration, src/client.py | — |
| Rate limit | 100 requests / minute / key | README, getting-started, api-reference, faq, src/client.py | **60/min** (v1.3 raised it) |
| Max payload size | 256 KB | README, getting-started, api-reference, faq, configuration, src/client.py | **128 KB** (v1.1 raised it) |
| Per-attempt timeout | 30 seconds | getting-started, api-reference, faq, configuration, src/worker.py | — |
| Retry policy | up to 3 attempts, exponential backoff from 2s | api-reference, faq, configuration, src/worker.py | — |
| Job states | queued, running, succeeded, failed, cancelled | getting-started, api-reference, faq, changelog, src/client.py | — |
| Self-hosted port | 8080 | README, getting-started, configuration | **3000** (beta, changed in v1.0) |
| Worker concurrency | 4 | README, configuration, src/worker.py | — |
| Job retention | 7 days | faq, configuration, src/client.py | **3 days** (v1.2 extended it) |

## Suggested distractor for clustering

The rate-limit fact and the max-payload fact both mention "limits" and both appear
in the same sections of several files. A good clustering threshold keeps them in
*separate* clusters (they are different facts); a too-high threshold will wrongly
merge them. Use this pair to sanity-check your threshold, not just the easy
duplicates.

## How to use this for the gold test set

Pick facts from the table above and phrase questions so the answer is exactly the
"current value." Include at least a couple whose *stale* value is present in the
changelog (rate limit, retention, payload size, port) — those are the questions
that separate a pipeline with a working selection step from one without.
