# Changelog

All notable changes to Nimbus are recorded here, newest first. Historical entries
describe the behavior *at the time of that release* and are kept for reference —
they may not reflect current defaults.

## v1.4.0 — 2025-06-01

- Added webhook support: register a callback URL and Nimbus POSTs the final result
  when a job reaches a terminal state.
- `Retry-After` header now included on all `429` responses.

## v1.3.0 — 2025-03-12

- **Raised the rate limit from 60 to 100 requests per minute per API key.** The
  old ceiling of 60/min was too conservative for interactive dashboards.
- Improved rolling-window accounting for rate limits.

## v1.2.0 — 2024-12-04

- **Extended job retention from 3 days to 7 days.** Previously, completed jobs
  were purged after only 3 days, which several users found too short for
  debugging. Terminal jobs are now kept for a week.
- Added the `POST /jobs/{id}/cancel` endpoint.

## v1.1.0 — 2024-09-20

- Increased the maximum payload size to 256 KB (it was 128 KB in v1.0).
- Added exponential backoff between retry attempts.

## v1.0.0 — 2024-07-01

- First stable release.
- Default self-hosted port set to 8080. (During the beta the server had listened
  on port 3000; the 1.0 release moved it to 8080 to avoid clashes with common dev
  servers.)
- Job model finalized with five states: queued, running, succeeded, failed,
  cancelled.
- Per-attempt timeout of 30 seconds introduced.
