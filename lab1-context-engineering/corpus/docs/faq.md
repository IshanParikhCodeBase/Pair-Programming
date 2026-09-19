# Frequently Asked Questions

## How many requests can I make?

Each API key is allowed 100 calls per minute. If you burst past that, further
requests come back as `429` until the rolling window clears. If you consistently
need more, contact us about a higher tier — the limit is per key, so sharding
across multiple keys also works.

## How big can a job be?

The payload you attach to a job can be at most 256 KB. That's plenty for
parameters and references, but it's not meant to carry large files. Put big blobs
in storage and pass a URL.

## What happens if my job takes too long?

Jobs aren't allowed to run forever. Each attempt has half a minute to complete —
if it hasn't finished in 30 seconds, Nimbus stops it and treats that attempt as a
failure. If your work genuinely needs longer, break it into smaller jobs or, on a
self-hosted server, raise the timeout in the config.

## Do failed jobs get retried?

Yes. When an attempt fails (including a timeout), Nimbus tries again, up to three
attempts total, spacing the retries out with exponential backoff. If all three
attempts fail, the job's final state is `failed` and, if you configured a
webhook, you'll be notified.

## How long do you keep my jobs?

Finished jobs — whether they succeeded or failed — stick around for 7 days so you
can inspect the results. After that they're purged automatically and
`GET /jobs/{id}` will return `404`. Export anything you need to keep before the
retention window closes.

## Can I cancel a job?

Yes, call the cancel endpoint. Queued jobs stop right away; a job that's already
running is asked to stop and, if it doesn't, is killed at the next timeout.

## What are the possible job states?

A job is always in one of five states: queued, running, succeeded, failed, or
cancelled. Once it reaches succeeded, failed, or cancelled it's done and won't
change again.

## Is there an SDK?

You can use plain HTTP — that's the whole point. Official thin clients exist for
Python and JavaScript, but they're just convenience wrappers over the same REST
API described in the [reference](./api-reference.md).
