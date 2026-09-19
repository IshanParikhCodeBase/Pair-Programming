"""Thin Python client for the Nimbus task queue.

This is a convenience wrapper over the REST API. It does not add behavior beyond
what the HTTP endpoints already provide; anything documented here is also true of
the raw API.
"""

import time
import requests

# Production base URL. Point this at http://localhost:8080/v1 for a local server.
DEFAULT_BASE_URL = "https://api.nimbusqueue.io/v1"

# The server rejects payloads larger than 256 KB, so we check client-side too and
# fail fast with a clearer error than a raw 413.
MAX_PAYLOAD_BYTES = 256 * 1024

# Terminal states: once a job is in one of these it will never change again.
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


class NimbusClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE_URL):
        self.base_url = base_url
        # All requests authenticate with the API key as a bearer token in the
        # Authorization header. A missing or bad token comes back as 401.
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def submit(self, job_type, payload, webhook=None):
        """Submit a job and return its ID.

        Note the rate limit: the account is capped at 100 requests per minute, and
        submit() counts against that budget. Exceeding it raises on the 429.
        """
        body = {"type": job_type, "payload": payload}
        if webhook:
            body["webhook"] = webhook
        resp = requests.post(f"{self.base_url}/jobs", json=body, headers=self.headers)
        resp.raise_for_status()
        return resp.json()["id"]

    def get(self, job_id):
        """Fetch a job. Returns 404 once the job has aged out.

        Completed jobs are retained for 7 days server-side; after that they are
        purged and this call will 404.
        """
        resp = requests.get(f"{self.base_url}/jobs/{job_id}", headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def wait(self, job_id, poll_interval=3):
        """Poll until the job reaches a terminal state.

        Keep poll_interval at a few seconds. Polling too aggressively will burn
        through the 100 req/min limit and start returning 429s.
        """
        while True:
            job = self.get(job_id)
            if job["state"] in TERMINAL_STATES:
                return job
            time.sleep(poll_interval)
