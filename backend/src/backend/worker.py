from rq import Worker
from .queue import redis_conn
from . import jobs  # ensure callables imported

if __name__ == "__main__":
    Worker(["orchestrator", "suggest", "check"], connection=redis_conn).work()
