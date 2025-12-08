"""RQ worker entrypoint for processing domain check jobs."""

from __future__ import annotations

import os
import socket
import time

from redis import Redis
from rq import Worker

from .logic import check_domains, check_domain


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE", "domain_checks")


def handle_domain_check(domains: list[str]) -> list[dict[str, str]]:
    worker_pid = os.getppid()
    print(f"[Worker {worker_pid}] Handling domain check for: {domains}")
    results = check_domains(domains)
    print(f"[Worker {worker_pid}] Computed results: {results}")
    return [result.model_dump() for result in results]


def handle_single_domain_check(domain: str, enqueued_at: float | None = None) -> dict:
    """
    Check a single domain and return result with timing metrics.
    
    Args:
        domain: The domain to check
        enqueued_at: Unix timestamp when the job was enqueued (for queue wait time calculation)
    
    Returns:
        Dict with domain, status, worker_id, processing_time_ms, and queue_wait_time_ms
    """
    start_time = time.time()
    queue_wait_time_ms = 0
    
    if enqueued_at is not None:
        queue_wait_time_ms = int((start_time - enqueued_at) * 1000)
    
    worker_pid = os.getppid()
    worker_id = f"{socket.gethostname()}:{worker_pid}"
    print(f"[Worker {worker_pid}] Handling single domain check for: {domain}")
    
    try:
        status = check_domain(domain)
    except Exception as e:
        print(f"[Worker {worker_pid}] Error checking domain '{domain}': {e}")
        status = "invalid"
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    result = {
        "domain": domain,
        "status": status,
        "worker_id": worker_id,
        "processing_time_ms": processing_time_ms,
        "queue_wait_time_ms": queue_wait_time_ms,
    }
    print(f"[Worker {worker_pid}] Computed result: {result}")
    return result


def main() -> None:
    redis_connection = Redis.from_url(REDIS_URL)
    print(f"[Worker {os.getpid()}] Starting worker on queue '{QUEUE_NAME}' using Redis '{REDIS_URL}'")
    worker = Worker([QUEUE_NAME], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    main()
