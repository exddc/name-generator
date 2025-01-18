from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import json
import datetime
import uuid
import asyncio
import time
from os import environ

from models import DomainRequest, DomainResponse, SuggestRequest, Metric
from utils import (
    SessionLocal,
    get_or_update_domain,
    query_name_suggestor,
    check_services_connections,
)

BACKEND_PORT = int(environ.get("BACKEND_PORT"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    services = check_services_connections()
    return {"status": "ok", "message": "Backend is running", "services": services}


@app.post("/v1/checkdomain", response_model=list[DomainResponse])
def checkdomain(request: DomainRequest):
    """
    For each domain in request.domains:
    - Attempt to get or update from DB (with domain-checker microservice call if needed).
    - Return the aggregated results.
    """
    results = []
    session = SessionLocal()

    try:
        for full_domain in request.domains:
            try:
                domain_record = get_or_update_domain(session, full_domain)

                results.append(
                    DomainResponse(domain=full_domain, status=domain_record.status)
                )
            except ValueError as ve:
                raise HTTPException(status_code=500, detail=str(ve))

        return results
    except Exception as e:
        print(f"Error in checkdomain: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/v1/suggest", response_model=list[DomainResponse])
def suggest(suggest_request: SuggestRequest):
    """
    1. Receive user input string ("query").
    2. Send this to the name_suggestor service, which returns a list[str] of domain suggestions.
    3. For each suggestion, call get_or_update_domain to get its status (or re-check if needed).
    4. Return the list of DomainResponse objects.
    """
    session = SessionLocal()
    results = []

    try:
        user_input = suggest_request.query
        suggestions_list = query_name_suggestor(user_input)

        if not suggestions_list:
            return results

        for suggested_domain in suggestions_list:
            domain_record = get_or_update_domain(session, suggested_domain)
            results.append(
                DomainResponse(domain=suggested_domain, status=domain_record.status)
            )

        return results

    except Exception as e:
        print(f"Error in suggest: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/v1/suggest_stream")
def suggest_sse(request: Request, query: str) -> StreamingResponse:
    # Basic metadata
    request_id = str(uuid.uuid4())
    request_start_time = datetime.datetime.utcnow()
    start_perf = time.perf_counter()

    # Attempt to get IP
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    def sse_event_stream():
        session = SessionLocal()

        # Initialize counters and timers
        total_checked = 0
        free_found = 0
        suggestions_count = 0
        errors_count = 0
        time_suggestor_ms = 0.0
        time_domain_check_ms = 0.0

        # Store all domain strings if you want to see them later
        checked_domains = []
        # NEW: a list to keep all error messages
        error_messages = []

        try:
            while free_found < 5:
                # measure how long the suggestor takes
                suggestor_start = time.perf_counter()
                suggestions = query_name_suggestor(query)
                suggestor_end = time.perf_counter()
                time_suggestor_ms += (suggestor_end - suggestor_start) * 1000

                if not suggestions:
                    yield make_sse_event("done", "No suggestions found.")
                    return

                suggestions_count += len(suggestions)

                for suggested_domain in suggestions:
                    check_start = time.perf_counter()
                    try:
                        domain_record = get_or_update_domain(session, suggested_domain)
                    except Exception as ex:
                        errors_count += 1
                        error_msg = f"Error checking domain '{suggested_domain}': {ex}"
                        error_messages.append(error_msg)
                        print(error_msg)
                        yield make_sse_event("error", error_msg)
                        continue
                    finally:
                        check_end = time.perf_counter()
                        time_domain_check_ms += (check_end - check_start) * 1000

                    total_checked += 1

                    full_dom = domain_record.domain_name
                    if domain_record.tld:
                        full_dom += f".{domain_record.tld}"
                    checked_domains.append(full_dom)

                    data = {
                        "domain": full_dom,
                        "status": domain_record.status,
                        "free_found_so_far": free_found,
                        "total_checked": total_checked,
                    }
                    yield make_sse_event("domain_suggestion", data)

                    if domain_record.status == "free":
                        free_found += 1
                    if free_found >= 5:
                        break

            done_message = f"Successfully found {free_found} free domains out of {total_checked} checked."
            yield make_sse_event("done", done_message)

        except asyncio.CancelledError:
            # SSE disconnected by client
            error_msg = "SSE stream cancelled by client."
            error_messages.append(error_msg)
            print(error_msg)
            yield make_sse_event("done", "Client disconnected.")
            # No re-raise so we still log in the finally block
        except Exception as main_ex:
            errors_count += 1
            error_msg = f"Error generating domain suggestions: {main_ex}"
            error_messages.append(error_msg)
            print(error_msg)
            yield make_sse_event("error", error_msg)
        finally:
            # Always log your metrics
            session_expired_time = time.perf_counter()
            total_request_ms = (session_expired_time - start_perf) * 1000
            request_end_time = datetime.datetime.utcnow()

            new_metric = Metric(
                request_id=request_id,
                start_time=request_start_time,
                end_time=request_end_time,
                total_request_ms=total_request_ms,
                time_suggestor_ms=time_suggestor_ms,
                time_domain_check_ms=time_domain_check_ms,
                suggestions_count=suggestions_count,
                total_checked=total_checked,
                free_found=free_found,
                errors_count=errors_count,
                error_messages=json.dumps(error_messages),
                query=query,
                domains=json.dumps(checked_domains),
                ip=ip_address,
            )

            try:
                session.add(new_metric)
                session.commit()
            except Exception as metric_ex:
                print(f"Error saving metric: {metric_ex}")
                session.rollback()
            finally:
                session.close()

    return StreamingResponse(sse_event_stream(), media_type="text/event-stream")


def make_sse_event(event_type: str, data) -> str:
    """
    Helper to format a Server-Sent Event:
      event: <event_type>
      data: <json serialized data>
      (plus a blank line)
    """
    json_data = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)
