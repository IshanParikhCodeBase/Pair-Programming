# Getting Started with Nimbus

This tutorial walks you through submitting your first job, checking its status,
and handling the result. By the end you'll understand the full lifecycle of a
Nimbus job.

## Before you begin

You'll need an API key. Sign in to the dashboard and create one under
**Settings → API Keys**. Treat it like a password — anyone with your key can
submit jobs billed to your account.

All of the examples below talk to the production endpoint,
`https://api.nimbusqueue.io/v1`. If you're running the server locally, swap that
for `http://localhost:8080` and the rest of the tutorial works unchanged.

## Step 1: Authenticate

Nimbus uses bearer-token authentication. Put your API key in the `Authorization`
header of every request, prefixed with the word `Bearer`:

```
Authorization: Bearer nmb_live_abc123...
```

If you forget the header, or the key is wrong, you'll get a `401 Unauthorized`.

## Step 2: Submit a job

A job has a `type` (which worker handles it) and a `payload` (the data it needs).
Keep the payload small — the maximum size for a single job's payload is 256
kilobytes. Anything larger should be stored elsewhere (say, in object storage)
with a reference passed in the payload instead.

```bash
curl -X POST https://api.nimbusqueue.io/v1/jobs \
  -H "Authorization: Bearer $NIMBUS_API_KEY" \
  -d '{"type": "resize_image", "payload": {"url": "s3://bucket/photo.jpg"}}'
```

You'll get back JSON with an `id` and an initial state of `queued`.

## Step 3: Track the job

Every job moves through a fixed set of states. It starts **queued**, becomes
**running** when a worker picks it up, and ends in one of three terminal states:
**succeeded**, **failed**, or **cancelled**. Poll the job endpoint to follow along:

```bash
curl https://api.nimbusqueue.io/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $NIMBUS_API_KEY"
```

## Step 4: Understand timeouts and retries

If your job's handler runs too long it will be stopped. By default a job is
allowed 30 seconds to finish before Nimbus kills it and marks the attempt as
failed. When an attempt fails, Nimbus doesn't give up immediately — it retries.

Don't hammer the poll endpoint, either. Remember the account limit of 100
requests per minute applies to status checks too, so poll every few seconds
rather than in a tight loop, or better, use a webhook.

## Step 5: Get notified with webhooks

Instead of polling, you can register a webhook URL. Nimbus will POST the final
job result to that URL when the job reaches a terminal state. This is the
recommended pattern for production.

## Next steps

- [API Reference](./api-reference.md) — every endpoint and field.
- [Configuration](./configuration.md) — tuning a self-hosted server.
- [FAQ](./faq.md) — common questions.
