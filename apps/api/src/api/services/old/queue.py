import os, json, redis
from rq import Queue

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
redis_conn = redis.Redis.from_url(REDIS_URL, decode_responses=True)

q_suggest = Queue("suggest", connection=redis_conn)
q_check = Queue("check", connection=redis_conn)
q_orchestrator = Queue("orchestrator", connection=redis_conn)

def publish(channel: str, payload):
    data = payload if isinstance(payload, str) else json.dumps(payload)
    redis_conn.publish(channel, data)
