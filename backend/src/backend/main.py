from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

from models import DomainRequest, DomainResponse, SuggestRequest
from utils import SessionLocal, get_or_update_domain, query_name_suggestor

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
    return {"status": "ok", "message": "Single-table + tldextract backend is running"}


@app.post("/checkdomain", response_model=list[DomainResponse])
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


@app.post("/suggest", response_model=list[DomainResponse])
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


@app.get("/suggest_stream")
def suggest_sse(query: str) -> StreamingResponse:
    """
    1) Accept a 'query' parameter (e.g. /suggest_sse?query=cool+tech).
    2) Use your name_suggestor to get a list of suggested domains (possibly large).
    3) For each domain, call get_or_update_domain for domain checking.
    4) Stream back SSE events:
        - "domain_suggestion" for each domain
        - Stop once we've found 5 free domains or run out of suggestions
        - "done" when we finish (with a message about how many free we found)
        - "error" if something goes wrong
    """
    session = SessionLocal()

    def sse_event_stream():
        try:
            free_count = 0
            total_checked = 0

            while free_count < 5:
                suggestions = query_name_suggestor(query)
                if not suggestions:
                    yield make_sse_event("done", "No suggestions found.")
                    return

                for suggested_domain in suggestions:
                    total_checked += 1

                    try:
                        domain_record = get_or_update_domain(session, suggested_domain)

                        full_dom = domain_record.domain_name
                        if domain_record.tld:
                            full_dom += f".{domain_record.tld}"

                        data = {
                            "domain": full_dom,
                            "status": domain_record.status,
                            "free_found_so_far": free_count,
                            "total_checked": total_checked,
                        }

                        yield make_sse_event("domain_suggestion", data)

                        if domain_record.status == "free":
                            free_count += 1

                        if free_count >= 5:
                            break

                    except Exception as ex:
                        error_message = (
                            f"Error checking domain '{suggested_domain}': {ex}"
                        )
                        print(error_message)
                        yield make_sse_event("error", error_message)

            done_message = f"Successfully found {free_count} free domains out of {total_checked} checked."

            yield make_sse_event("done", done_message)

        except Exception as main_ex:
            error_message = f"Fatal error in suggest_sse: {main_ex}"
            print(error_message)
            yield make_sse_event("error", error_message)
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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
