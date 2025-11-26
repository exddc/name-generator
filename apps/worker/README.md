# Domain Checker Worker

A scalable RQ worker service for checking domain name availability. Designed to support multiple workers operating concurrently on the same Redis queue.

## Features

- **Multi-Worker Support**: Multiple workers can connect to the same Redis queue and atomically pick up jobs
- **Internal Concurrency**: Each worker processes domains in parallel using a thread pool
- **Idle Recheck**: Automatically rechecks stale domain statuses when workers are idle
- **Configurable**: All settings can be adjusted via environment variables

## Installation

1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

2. Start a single RQ worker:
   ```bash
   poetry run domain-checker
   ```

## Running Multiple Workers

### Using Docker Compose

Scale workers using the `--scale` flag:

```bash
# Start 3 workers
docker-compose --profile worker up --scale worker=3

# Or in detached mode
docker-compose --profile worker up -d --scale worker=3
```

### Using Direct Commands

Run multiple instances in separate terminals or as background processes:

```bash
# Terminal 1
poetry run domain-checker

# Terminal 2
poetry run domain-checker

# Terminal 3
poetry run domain-checker
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `RQ_QUEUE` | `domain_checks` | Name of the RQ queue to listen on |
| `DOMAIN_CHECKER_DNS_TIMEOUT` | `3.0` | Timeout in seconds for DNS lookups |
| `WORKER_MAX_CONCURRENT_CHECKS` | `10` | Maximum concurrent domain checks per worker |

### Idle Recheck Configuration

The idle recheck feature automatically rechecks domain statuses when workers have been idle for a configurable amount of time.

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_ENABLE_IDLE_RECHECK` | `true` | Enable/disable the idle recheck feature |
| `WORKER_IDLE_THRESHOLD_SECONDS` | `60` | How long the queue must be idle before starting recheck |
| `WORKER_RECHECK_INTERVAL_DAYS` | `7` | How old a domain check must be before rechecking |
| `WORKER_RECHECK_BATCH_SIZE` | `50` | Number of domains to recheck per batch |
| `WORKER_RECHECK_POLL_INTERVAL` | `30` | How often to check if a recheck should run (seconds) |

### Database Configuration (for Idle Recheck)

The recheck feature requires database access to query and update domain statuses.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | Full database URL (takes precedence if set) |
| `DB_HOST` / `POSTGRES_HOST` | `localhost` | Database host |
| `DB_PORT` / `POSTGRES_PORT` | `5432` | Database port |
| `DB_USER` / `POSTGRES_USER` | `postgres` | Database username |
| `DB_PASSWORD` / `POSTGRES_PASSWORD` | `password` | Database password |
| `DB_NAME` / `POSTGRES_DB` | `domain_generator` | Database name |

## Architecture

### How It Works

1. **Job Processing**: The API enqueues batches of domains to the Redis queue. Workers atomically pick up jobs (one worker per job) using RQ's built-in locking.

2. **Concurrent Checking**: Each worker processes domains in parallel using a `ThreadPoolExecutor`. This dramatically speeds up I/O-bound DNS and WHOIS lookups.

3. **Idle Recheck**: When the queue is empty and a worker has been idle for the configured threshold, it checks the database for stale domain records and enqueues recheck jobs.

4. **Distributed Lock**: A Redis-based distributed lock ensures only one worker enqueues recheck jobs at a time, preventing duplicate work.

### Scaling Considerations

- **Workers compete for jobs**: RQ ensures each job is processed by exactly one worker
- **Concurrent checks per worker**: Adjust `WORKER_MAX_CONCURRENT_CHECKS` based on system resources
- **Optimal worker count**: Start with 2-3 workers and scale based on queue depth and latency requirements
- **Resource limits**: DNS and WHOIS lookups are I/O-bound; more workers help more than more threads per worker

## Tests

Run the tests with Poetry:

```bash
poetry run pytest
```

## Queue Usage

### Enqueue a Domain Check Job

```python
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("domain_checks", connection=redis_conn)
job = queue.enqueue("domain_checker.main.handle_domain_check", [["example.com", "test.io"]])
print(job.result)
```

### Monitor Queue Status

```python
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("domain_checks", connection=redis_conn)

print(f"Jobs in queue: {len(queue)}")
print(f"Queue is empty: {queue.is_empty()}")
```

## Troubleshooting

### Workers Not Picking Up Jobs

1. Ensure Redis is running and accessible
2. Verify `RQ_QUEUE` matches between API and workers
3. Check Redis connection URL is correct

### Slow Domain Checking

1. Increase `WORKER_MAX_CONCURRENT_CHECKS` (default: 10)
2. Add more worker instances
3. Reduce `DOMAIN_CHECKER_DNS_TIMEOUT` if acceptable

### Recheck Not Working

1. Verify database credentials are correct
2. Check `WORKER_ENABLE_IDLE_RECHECK` is `true`
3. Ensure the `domains` table exists with required columns
4. Check worker logs for connection errors
