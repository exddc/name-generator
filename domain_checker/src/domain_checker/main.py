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


@app.post("/checkdomain", response_model=List[DomainCheckResponse])
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

    # 1. Try DNS resolution to see if it resolves to an IP address
    try:
        socket.gethostbyname(domain)
        # If DNS resolution succeeds, it's very likely registered
        return "registered"
    except socket.gaierror:
        # DNS resolution failed - might be free, or might just not have DNS set up.
        pass

    # 2. Try a WHOIS lookup
    try:
        # Run a whois command (assuming the local system has it installed)
        result = subprocess.run(
            ["whois", domain], capture_output=True, text=True, timeout=10
        )

        # Normalize the output to handle case-insensitivity
        whois_output = result.stdout.lower()

        # If WHOIS indicates there's no record
        if (
            "no match" in whois_output
            or "not found" in whois_output
            or "no entries found" in whois_output
        ):
            return "free"

        # If WHOIS output seems to contain a domain name or relevant info
        if "domain name" in whois_output or "registrar" in whois_output:
            return "registered"
    except Exception:
        # If WHOIS fails for any reason (timeout, not installed, etc.)
        pass

    # If neither DNS resolution nor WHOIS lookups can conclude, return non conclusive
    return "non conclusive"


def normalize_domain(input_string: str) -> str:
    """
    Normalize input to extract the domain name from a URL or raw domain string.

    :param input_string: The input string (URL or domain)
    :return: A normalized domain name
    """
    # Parse the URL to extract the netloc (domain)
    parsed = urlparse(input_string)
    domain = parsed.netloc if parsed.netloc else input_string

    # Remove any trailing slashes
    return domain.strip().lower()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
