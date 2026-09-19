# Configuration

Self-hosted Nimbus is configured with a single TOML file, passed via
`--config`. This page documents every option and its default. Options you don't
set fall back to the defaults shown here.

## Example config

```toml
[server]
port = 8080
base_path = "/v1"

[workers]
concurrency = 4

[jobs]
timeout_seconds = 30
max_attempts = 3
max_payload_kb = 256
retention_days = 7
```

## Server options

### `server.port`

The TCP port the HTTP server binds to. Defaults to 8080. If you put Nimbus behind
a reverse proxy, this is the upstream port the proxy should forward to.

### `server.base_path`

The path prefix for the API. Defaults to `/v1`, so a locally running server
serves the jobs endpoint at `http://localhost:8080/v1/jobs`.

## Worker options

### `workers.concurrency`

How many worker processes run in parallel, i.e. how many jobs can execute at
once. The default is 4. Raise it on bigger machines to increase throughput;
lower it if your job handlers are memory-hungry.

## Job options

### `jobs.timeout_seconds`

The per-attempt time budget. A handler that runs longer than this is aborted and
the attempt is marked failed. Defaults to 30. Unlike the hosted service, where
this is fixed, self-hosted deployments may set any value here.

### `jobs.max_attempts`

Total number of times an attempt is made before the job is declared failed.
Defaults to 3. Setting it to 1 disables retries entirely. Backoff between
attempts is exponential and not configurable.

### `jobs.max_payload_kb`

Maximum size, in kilobytes, of a job's payload. Defaults to 256. Requests over
the limit are rejected before the job is enqueued.

### `jobs.retention_days`

How long terminal jobs are kept before being purged from the database. Defaults
to 7. After this many days a completed job is deleted and can no longer be
fetched.

## Authentication

Self-hosted servers still require bearer-token auth. Define keys in a separate
`keys.toml` (see the deployment guide); each incoming request must present one of
them in the `Authorization` header.
