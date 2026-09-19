# Nimbus

Nimbus is a hosted task queue with a simple REST API. You submit jobs over HTTP,
Nimbus runs them on a pool of workers, and you poll (or receive a webhook) for the
result. It is designed for background work that shouldn't block a web request:
sending email, generating reports, resizing images, calling slow third-party APIs.

This README is the quickest way to get from zero to a running job. For everything
else, see the [documentation](./docs).

## Why Nimbus

- **Dead-simple API.** Submit a job with a single POST. No SDK required.
- **Automatic retries.** Failed jobs are retried for you with backoff.
- **Managed or self-hosted.** Use the hosted service, or run the open-source
  server yourself.

## Quickstart (hosted)

Every request goes to the hosted API at `https://api.nimbusqueue.io/v1`. You
authenticate by sending your API key as a bearer token in the `Authorization`
header. Grab a key from the dashboard, then submit your first job:

```bash
curl -X POST https://api.nimbusqueue.io/v1/jobs \
  -H "Authorization: Bearer $NIMBUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "send_email", "payload": {"to": "user@example.com"}}'
```

The response contains a job ID. Poll `GET /v1/jobs/{id}` to watch it move from
`queued` to `running` and finally to `succeeded`.

## A note on limits

Nimbus is generous but not unlimited. Each API key may make up to 100 requests
per minute; go over and you'll get back a `429 Too Many Requests`. Individual job
payloads are capped at 256 KB. These limits keep the shared service fast for
everyone, and they're high enough that most applications never notice them.

## Self-hosting

Prefer to run it yourself? The server is a single binary. By default it listens
on port 8080 and starts 4 worker processes, both of which you can change in the
config file. See [Configuration](./docs/configuration.md) for the full list of
options.

```bash
nimbus-server --config ./nimbus.toml
```

## Project status

Nimbus is production-ready and used by teams processing millions of jobs a day.
It follows semantic versioning; breaking changes only land in major releases.

## License

Apache 2.0.
