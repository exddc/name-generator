from fastapi import FastAPI, HTTPException
from models import DomainRequest, DomainResponse, SuggestRequest
from utils import SessionLocal, get_or_update_domain, query_name_suggestor

app = FastAPI()


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
                # domain_record => Domain(domain_name=..., tld=..., status=..., last_checked=...)

                # Reconstruct a "full domain" string if you'd like
                # or just return the original 'full_domain'
                combined = (
                    f"{domain_record.domain_name}.{domain_record.tld}"
                    if domain_record.tld
                    else domain_record.domain_name
                )

                results.append(
                    DomainResponse(
                        domain=full_domain, status=domain_record.status  # or combined
                    )
                )
            except ValueError as ve:
                # e.g. domain-checker returned no results
                raise HTTPException(status_code=500, detail=str(ve))

        return results
    except Exception as e:
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
        # Step 1: Grab the user query
        user_input = suggest_request.query

        # Step 2: Get suggestions as a list of strings
        suggestions_list = query_name_suggestor(user_input)

        if not suggestions_list:
            # If empty, we can decide to return an empty list or raise an exception
            return results

        # Step 3: For each suggested domain, check or update via domain_checker logic
        for suggested_domain in suggestions_list:
            domain_record = get_or_update_domain(session, suggested_domain)
            results.append(
                DomainResponse(domain=suggested_domain, status=domain_record.status)
            )

        # Step 4: Return the final list
        return results

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
