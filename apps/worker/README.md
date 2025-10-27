# Domain Checker Service

This service checks the availability of domain names.

## Installation

1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
2. Start an RQ worker:
   ```bash
   poetry run domain-checker
   ```

## Tests

Run the tests with Poetry:

```bash
poetry run pytest
```

## Queue Usage

Enqueue a job from a Python shell:

```python
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("domain_checks", connection=redis_conn)
job = queue.enqueue("domain_checker.main.handle_domain_check", [["example.com"]])
print(job.result)
```
