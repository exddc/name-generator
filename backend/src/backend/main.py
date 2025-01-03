from fastapi import FastAPI, HTTPException
from models import DomainRequest, DomainResponse
from utils import SessionLocal, get_or_update_domain

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
