# Entry point for the domain_checker service
import uvicorn
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import socket
from typing import List
import concurrent.futures
from os import environ

PORT = int(environ.get("DOMAIN_CHECKER_PORT", 8000))
DNS_TIMEOUT = float(environ.get("DOMAIN_CHECKER_DNS_TIMEOUT", 3.0))

app = FastAPI()

# Common strings indicating that a domain is free
FREE_KEYWORDS = [
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

# Common strings indicating that the domain is registered
REGISTERED_KEYWORDS = [
    "domain name:",
    "registrar:",
    "domain status:",
    "creation date:",
    "expiry date:",
    "nameserver:",
    "name server:",
    "redacted for privacy",
]


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
    domain = normalize_domain(domain)

    # DNS resolution
    try:
        ip = dns_lookup_with_timeout(domain, timeout=DNS_TIMEOUT)
        # If DNS resolution succeeds, it's likely registered
        return "registered"
    except socket.gaierror:
        # DNS resolution explicitly failed (no record)
        pass
    except socket.timeout:
        # Timed out during DNS resolution
        return "non conclusive"

    # WHOIS lookup
    try:
        result = subprocess.run(
            ["whois", domain], capture_output=True, text=True, timeout=DNS_TIMEOUT
        )
        whois_output = result.stdout.lower()

        if any(keyword in whois_output for keyword in FREE_KEYWORDS):
            return "free"

        if any(keyword in whois_output for keyword in REGISTERED_KEYWORDS):
            return "registered"
    except subprocess.TimeoutExpired as e:
        partial_output = (e.output or "").lower()

        print(f"WHOIS lookup timed out for {domain}. Partial output: {partial_output}")

        if any(keyword in partial_output for keyword in FREE_KEYWORDS):
            return "free"
        if any(keyword in partial_output for keyword in REGISTERED_KEYWORDS):
            return "registered"

    except Exception as e:
        # If WHOIS lookup fails, or if the output is not as expected
        print(f"Error during WHOIS lookup for {domain}: {e}")
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


def dns_lookup_with_timeout(domain: str, timeout: float = 3.0) -> str:
    """
    Attempts to resolve a domain with a specified timeout.
    Returns the IP as a string if successful.
    Raises socket.timeout if it cannot resolve within the given timeout.
    Raises socket.gaierror if the DNS server returns an error or domain does not exist.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(socket.gethostbyname, domain)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise socket.timeout(f"DNS resolution timed out after {timeout} seconds.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
