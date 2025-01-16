# Entry point for the domain_checker service
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import socket
from typing import List

app = FastAPI()


class DomainCheckRequest(BaseModel):
    domains: List[str]


class DomainCheckResponse(BaseModel):
    domain: str
    status: str


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Server is running"}


@app.post("/v1/checkdomain", response_model=List[DomainCheckResponse])
async def check_domains(request: DomainCheckRequest):
    results = []

    for domain in request.domains:
        status = check_domain(domain)
        results.append({"domain": domain, "status": status})

    return results


def check_domain(domain: str) -> str:
    """
    Checks if a domain is registered, free, or if the status is non conclusive.

    :param domain: Domain name to check (e.g. "example.com")
    :return: "registered", "free", or "non conclusive"
    """
    # Normalize the input domain
    domain = normalize_domain(domain)

    # 1. Try DNS resolution
    # If DNS resolution succeeds, it's almost certainly registered (active).
    try:
        socket.gethostbyname(domain)
        # If DNS resolution succeeds, it's very likely registered
        return "registered"
    except socket.gaierror:
        # DNS resolution failed - might be free, or might not have DNS set up.
        pass

    # 2. Try a WHOIS lookup
    try:
        result = subprocess.run(
            ["whois", domain], capture_output=True, text=True, timeout=10
        )
        whois_output = result.stdout.lower()

        # Common strings indicating that a domain is free
        free_keywords = [
            "no match",
            "not found",
            "no entries found",
            "domain you requested is not known",
            "status: available",
            "available for purchase",
            "status: free",
            "the queried object does not exist",
            "no data found",
        ]
        if any(keyword in whois_output for keyword in free_keywords):
            return "free"

        # Common strings indicating that the domain is registered
        # (presence of a registrar, domain creation/expiry info, name servers, etc.)
        registered_keywords = [
            "domain name:",
            "registrar:",
            "domain status:",
            "creation date:",
            "expiry date:",
            "nameserver:",
            "name server:",
        ]
        if any(keyword in whois_output for keyword in registered_keywords):
            return "registered"

    except Exception:
        pass

    # If neither DNS nor WHOIS conclusively determines free vs. registered
    return "non conclusive"


def normalize_domain(input_string: str) -> str:
    """
    Normalize input to extract the domain name from a URL or raw domain string.

    :param input_string: The input string (URL or domain)
    :return: A normalized domain name
    """
    parsed = urlparse(input_string)
    domain = parsed.netloc if parsed.netloc else input_string
    return domain.strip().lower()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
