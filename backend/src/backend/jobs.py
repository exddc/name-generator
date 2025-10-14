import json
from .queue import publish, q_check
from .utils import SessionLocal, get_or_update_domain
from .groq_client import get_suggestions_from_llm

def suggest_job(request_id: str, query: str) -> list[str]:
    suggestions = get_suggestions_from_llm(query)
    publish(f"sse:{request_id}", {"event": "suggestions", "data": suggestions})
    return suggestions

def check_domain_job(request_id: str, full_domain: str) -> dict:
    session = SessionLocal()
    try:
        record = get_or_update_domain(session, full_domain)
        result = {
            "domain": f"{record.domain_name}.{record.tld}" if record.tld else record.domain_name,
            "status": record.status,
        }
        publish(f"sse:{request_id}", {"event": "domain_suggestion", "data": result})
        return result
    finally:
        session.close()

def orchestrate_suggest_and_check(request_id: str, query: str):
    try:
        suggestions = suggest_job(request_id, query)
        for d in suggestions:
            q_check.enqueue(check_domain_job, request_id, d, job_timeout=30)
        publish(f"sse:{request_id}", {"event": "queued", "data": {"count": len(suggestions)}})
    except Exception as e:
        publish(f"sse:{request_id}", {"event": "error", "data": str(e)})
    finally:
        publish(f"sse:{request_id}", {"event": "done", "data": "orchestrator_finished"})
