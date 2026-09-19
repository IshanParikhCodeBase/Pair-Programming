# API Reference

The Nimbus REST API is versioned under a path prefix. The current version is v1,
served from the base URL `https://api.nimbusqueue.io/v1`. All responses are JSON.

## Authentication

Every endpoint requires authentication. Supply your API key as a bearer token:

```
Authorization: Bearer <your-api-key>
```

Requests without a valid token receive `401 Unauthorized`. Keys are scoped to a
single account and can be revoked from the dashboard at any time.

## Rate limiting

The API enforces a limit of 100 requests per minute per API key. When you exceed
it, the API responds with HTTP status `429 Too Many Requests` and a
`Retry-After` header indicating how many seconds to wait. The limit is applied as
a rolling window, not a fixed calendar minute.

## POST /jobs

Create a new job.

**Request body**

| Field     | Type   | Required | Description                                   |
| --------- | ------ | -------- | --------------------------------------------- |
| `type`    | string | yes      | The job type; determines which worker runs it |
| `payload` | object | yes      | Arbitrary JSON passed to the handler          |
| `webhook` | string | no       | URL to notify when the job finishes           |

The `payload` object is limited to 256 KB when serialized. Requests with a larger
payload are rejected with `413 Payload Too Large`.

**Response**

Returns the created job with its `id` and a `state` of `queued`.

## GET /jobs/{id}

Retrieve a single job by ID, including its current state and result.

The `state` field is one of exactly five values: `queued`, `running`,
`succeeded`, `failed`, or `cancelled`. The first two are transient; the last
three are terminal and will never change once set.

## POST /jobs/{id}/cancel

Request cancellation of a job. A job that is still `queued` is cancelled
immediately. A job that is already `running` is signalled to stop; if it does not
stop on its own it will be terminated at the next timeout boundary.

## Execution model

### Timeouts

Each job attempt is given a wall-clock budget. If the handler has not returned
within 30 seconds, the attempt is aborted and recorded as a failure. This
per-attempt timeout is configurable on self-hosted deployments but fixed on the
hosted service.

### Retries

A failed attempt is retried automatically. Nimbus makes up to 3 attempts in
total before marking the job `failed` for good, and it waits longer between each
try — an exponential backoff that starts at 2 seconds and doubles each time.
Retries are not counted against your rate limit.

## Errors

All errors return a JSON body with an `error` code and a human-readable
`message`. Common codes: `401` (bad auth), `413` (payload too large), `429`
(rate limited), `404` (no such job).
