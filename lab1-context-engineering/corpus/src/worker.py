"""Nimbus worker loop.

A worker pulls jobs off the queue, runs the matching handler, and reports the
result. Self-hosted deployments run several of these in parallel.
"""

import signal

# Default number of workers started by the server. Overridable via
# workers.concurrency in the config file. More workers = more jobs at once.
DEFAULT_CONCURRENCY = 4

# Per-attempt timeout in seconds. If a handler runs longer than this the attempt
# is aborted and marked failed. Matches jobs.timeout_seconds in the config.
ATTEMPT_TIMEOUT_SECONDS = 30

# A job is tried at most this many times before it is declared failed. Between
# attempts we back off exponentially (2s, 4s, 8s).
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2


class TimeoutError(Exception):
    pass


def _run_with_timeout(handler, payload):
    """Run a handler under the attempt timeout.

    The handler gets 30 seconds of wall-clock time. If it hasn't returned by then
    we raise, the caller records a failed attempt, and the retry logic decides
    whether to try again.
    """
    def _alarm(signum, frame):
        raise TimeoutError("handler exceeded the 30s attempt budget")

    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(ATTEMPT_TIMEOUT_SECONDS)
    try:
        return handler(payload)
    finally:
        signal.alarm(0)


def process(job, handler):
    """Process a single job, retrying on failure.

    We make up to MAX_ATTEMPTS tries. On success the job state becomes
    'succeeded'; if every attempt fails it ends as 'failed'.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = _run_with_timeout(handler, job["payload"])
            return {"state": "succeeded", "result": result}
        except Exception:
            if attempt == MAX_ATTEMPTS:
                return {"state": "failed"}
            # exponential backoff before the next attempt
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            _sleep(wait)


def _sleep(seconds):
    import time
    time.sleep(seconds)
