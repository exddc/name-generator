"""RQ worker entrypoint for processing domain check jobs.

Supports multiple workers accessing the same Redis queue atomically.
Includes idle recheck functionality to periodically refresh stale domain statuses.
"""

from __future__ import annotations

import os
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
from redis import Redis
from rq import Queue, Worker
from rq.job import Job

from .logic import check_domains


# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE", "domain_checks")

# Database configuration for recheck feature
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_HOST = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432")))
DB_USER = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "password"))
DB_NAME = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "domain_generator"))

# Idle recheck configuration
# How long the queue must be idle before starting recheck (in seconds)
IDLE_THRESHOLD_SECONDS = int(os.getenv("WORKER_IDLE_THRESHOLD_SECONDS", "60"))
# How often to recheck domain statuses (in days)
RECHECK_INTERVAL_DAYS = int(os.getenv("WORKER_RECHECK_INTERVAL_DAYS", "7"))
# Batch size for recheck jobs
RECHECK_BATCH_SIZE = int(os.getenv("WORKER_RECHECK_BATCH_SIZE", "50"))
# Enable/disable the idle recheck feature
ENABLE_IDLE_RECHECK = os.getenv("WORKER_ENABLE_IDLE_RECHECK", "true").lower() == "true"
# How often to check if we should run a recheck (in seconds)
RECHECK_POLL_INTERVAL = int(os.getenv("WORKER_RECHECK_POLL_INTERVAL", "30"))


def handle_domain_check(domains: list[str]) -> list[dict[str, str]]:
    """Process a batch of domains and return their availability status."""
    print(f"[Worker] Handling domain check for {len(domains)} domains: {domains[:5]}...")
    results = check_domains(domains)
    print(f"[Worker] Completed checking {len(results)} domains")
    return [result.model_dump() for result in results]


def handle_domain_recheck(domains: list[str]) -> list[dict[str, str]]:
    """
    Recheck stale domains and update their status in the database.
    
    This is a special job type that also updates the database directly
    after checking domain statuses.
    """
    print(f"[Worker] Rechecking {len(domains)} stale domains")
    results = check_domains(domains)
    
    # Update the database with new statuses
    try:
        _update_domain_statuses(results)
    except Exception as e:
        print(f"[Worker] Failed to update domain statuses in database: {e}")
    
    return [result.model_dump() for result in results]


def _get_db_connection():
    """Create a database connection for the recheck feature."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )


def _update_domain_statuses(results: list) -> None:
    """Update domain statuses in the database after recheck."""
    if not results:
        return
    
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc)
        
        for result in results:
            domain = result.domain
            status = result.status
            
            # Map worker status to API status
            if status == "free":
                db_status = "available"
            elif status == "registered":
                db_status = "registered"
            else:
                db_status = "unknown"
            
            cursor.execute(
                """
                UPDATE domains 
                SET status = %s, last_checked = %s, updated_at = %s
                WHERE domain = %s
                """,
                (db_status, now, now, domain)
            )
        
        conn.commit()
        print(f"[Worker] Updated {len(results)} domain statuses in database")
    except Exception as e:
        print(f"[Worker] Database update error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def _get_stale_domains(batch_size: int) -> list[str]:
    """Fetch domains that haven't been checked in RECHECK_INTERVAL_DAYS days."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=RECHECK_INTERVAL_DAYS)
        
        cursor.execute(
            """
            SELECT domain FROM domains 
            WHERE last_checked IS NULL OR last_checked < %s
            ORDER BY last_checked ASC NULLS FIRST
            LIMIT %s
            """,
            (cutoff_date, batch_size)
        )
        
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"[Worker] Failed to fetch stale domains: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _is_queue_idle(redis_conn: Redis, queue_name: str) -> bool:
    """Check if the queue has been idle (no pending jobs)."""
    queue = Queue(queue_name, connection=redis_conn)
    return queue.is_empty()


class IdleRecheckManager:
    """
    Manages the idle recheck functionality.
    
    When the worker is idle for a configurable amount of time,
    this manager enqueues recheck jobs for stale domains.
    """
    
    def __init__(self, redis_conn: Redis, queue_name: str):
        self.redis_conn = redis_conn
        self.queue_name = queue_name
        self.queue = Queue(queue_name, connection=redis_conn)
        self.last_job_time = time.time()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Redis key for coordinating recheck across multiple workers
        self._recheck_lock_key = f"worker:recheck_lock:{queue_name}"
        self._recheck_lock_ttl = 300  # 5 minutes
    
    def start(self) -> None:
        """Start the idle recheck monitoring thread."""
        if not ENABLE_IDLE_RECHECK:
            print("[Worker] Idle recheck feature is disabled")
            return
        
        print(f"[Worker] Starting idle recheck manager (interval: {RECHECK_INTERVAL_DAYS} days, "
              f"idle threshold: {IDLE_THRESHOLD_SECONDS}s)")
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the idle recheck monitoring thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
    
    def notify_job_completed(self) -> None:
        """Called when a job is completed to reset the idle timer."""
        self.last_job_time = time.time()
    
    def _acquire_recheck_lock(self) -> bool:
        """
        Try to acquire a distributed lock for recheck coordination.
        
        Only one worker should be enqueueing recheck jobs at a time
        to avoid duplicate work.
        """
        # Use Redis SET NX (only set if not exists) with expiry
        result = self.redis_conn.set(
            self._recheck_lock_key,
            "locked",
            nx=True,
            ex=self._recheck_lock_ttl
        )
        return result is True
    
    def _release_recheck_lock(self) -> None:
        """Release the distributed recheck lock."""
        self.redis_conn.delete(self._recheck_lock_key)
    
    def _monitor_loop(self) -> None:
        """Main loop that monitors for idle state and triggers rechecks."""
        while not self._stop_event.is_set():
            try:
                self._check_and_recheck()
            except Exception as e:
                print(f"[Worker] Recheck monitor error: {e}")
            
            # Wait before next check
            self._stop_event.wait(timeout=RECHECK_POLL_INTERVAL)
    
    def _check_and_recheck(self) -> None:
        """Check if we should trigger a recheck and do it if needed."""
        # Check if queue is idle
        if not _is_queue_idle(self.redis_conn, self.queue_name):
            self.last_job_time = time.time()
            return
        
        # Check if we've been idle long enough
        idle_duration = time.time() - self.last_job_time
        if idle_duration < IDLE_THRESHOLD_SECONDS:
            return
        
        # Try to acquire lock (only one worker should do recheck at a time)
        if not self._acquire_recheck_lock():
            print("[Worker] Another worker is handling recheck, skipping")
            return
        
        try:
            self._enqueue_recheck_batch()
        finally:
            self._release_recheck_lock()
    
    def _enqueue_recheck_batch(self) -> None:
        """Fetch stale domains and enqueue a recheck job."""
        stale_domains = _get_stale_domains(RECHECK_BATCH_SIZE)
        
        if not stale_domains:
            print("[Worker] No stale domains to recheck")
            return
        
        print(f"[Worker] Enqueueing recheck job for {len(stale_domains)} stale domains")
        
        # Enqueue the recheck job
        job = self.queue.enqueue(
            "domain_checker.main.handle_domain_recheck",
            args=[stale_domains],
            job_timeout=300,  # 5 minutes timeout for recheck jobs
        )
        
        print(f"[Worker] Enqueued recheck job {job.id}")
        
        # Reset idle timer since we just created work
        self.last_job_time = time.time()


class RecheckAwareWorker(Worker):
    """
    Custom RQ Worker that integrates with the IdleRecheckManager.
    
    Notifies the recheck manager when jobs complete to properly track idle time.
    """
    
    def __init__(self, *args, recheck_manager: Optional[IdleRecheckManager] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.recheck_manager = recheck_manager
    
    def perform_job(self, job: Job, queue: Queue) -> bool:
        result = super().perform_job(job, queue)
        
        # Notify recheck manager that a job was completed
        if self.recheck_manager:
            self.recheck_manager.notify_job_completed()
        
        return result


def main() -> None:
    """Main entry point for the worker process."""
    redis_connection = Redis.from_url(REDIS_URL)
    
    print(f"[Worker] Starting worker on queue '{QUEUE_NAME}' using Redis '{REDIS_URL}'")
    print(f"[Worker] Configuration:")
    print(f"  - Idle recheck enabled: {ENABLE_IDLE_RECHECK}")
    print(f"  - Recheck interval: {RECHECK_INTERVAL_DAYS} days")
    print(f"  - Idle threshold: {IDLE_THRESHOLD_SECONDS} seconds")
    print(f"  - Recheck batch size: {RECHECK_BATCH_SIZE}")
    
    # Initialize the idle recheck manager
    recheck_manager = IdleRecheckManager(redis_connection, QUEUE_NAME)
    recheck_manager.start()
    
    try:
        # Create and run the worker
        worker = RecheckAwareWorker(
            [QUEUE_NAME],
            connection=redis_connection,
            recheck_manager=recheck_manager,
        )
        worker.work()
    finally:
        recheck_manager.stop()


if __name__ == "__main__":
    main()
