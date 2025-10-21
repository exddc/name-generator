"""RQ worker entrypoint for processing domain check jobs."""

from __future__ import annotations

import os

from redis import Redis
from rq import Worker

from .logic import check_domains


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE", "domain_checks")


def handle_domain_check(domains: list[str]) -> list[dict[str, str]]:
    print(f"[Worker] Handling domain check for: {domains}")
    results = check_domains(domains)
    print(f"[Worker] Computed results: {results}")
    return [result.model_dump() for result in results]


def main() -> None:
    redis_connection = Redis.from_url(REDIS_URL)
    print(f"[Worker] Starting worker on queue '{QUEUE_NAME}' using Redis '{REDIS_URL}'")
    worker = Worker([QUEUE_NAME], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    main()
