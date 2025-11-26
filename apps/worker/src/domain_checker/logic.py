"""Core domain checking logic for queue workers and web handlers."""

from __future__ import annotations

import concurrent.futures
import os
import socket
import subprocess
from typing import Iterable, List, Sequence
from urllib.parse import urlparse

from pydantic import BaseModel


DNS_TIMEOUT = float(os.getenv("DOMAIN_CHECKER_DNS_TIMEOUT", "3.0"))
# Maximum concurrent domain checks within a single worker
# Adjust based on system resources (DNS/WHOIS are I/O bound)
MAX_CONCURRENT_CHECKS = int(os.getenv("WORKER_MAX_CONCURRENT_CHECKS", "10"))


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


class DomainCheckResult(BaseModel):
    domain: str
    status: str


def _check_single_domain(domain: str) -> DomainCheckResult:
    """Check a single domain and return a result. Used for concurrent execution."""
    try:
        status = check_domain(domain)
        return DomainCheckResult(domain=domain, status=status)
    except Exception as e:
        print(f"[Worker] Error checking domain '{domain}': {e}")
        return DomainCheckResult(domain=domain, status="invalid")


def check_domains(domains: Sequence[str]) -> List[DomainCheckResult]:
    """
    Check multiple domains concurrently using a thread pool.
    
    Uses ThreadPoolExecutor to parallelize I/O-bound DNS and WHOIS lookups.
    The number of concurrent checks is controlled by WORKER_MAX_CONCURRENT_CHECKS.
    """
    if not domains:
        return []
    
    # For a single domain, skip the overhead of threading
    if len(domains) == 1:
        return [_check_single_domain(domains[0])]
    
    results: List[DomainCheckResult] = []
    max_workers = min(MAX_CONCURRENT_CHECKS, len(domains))
    
    print(f"[Worker] Checking {len(domains)} domains with {max_workers} concurrent workers")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all domain checks
        future_to_domain = {
            executor.submit(_check_single_domain, domain): domain
            for domain in domains
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[Worker] Unexpected error for domain '{domain}': {e}")
                results.append(DomainCheckResult(domain=domain, status="invalid"))
    
    return results


def check_domain(domain: str) -> str:
    domain = normalize_domain(domain)

    try:
        dns_lookup_with_timeout(domain, timeout=DNS_TIMEOUT)
        return "registered"
    except (socket.gaierror, UnicodeEncodeError, ValueError) as e:
        if isinstance(e, UnicodeEncodeError):
            print(f"[Worker] Invalid domain encoding for '{domain}': {e}")
            raise
        pass
    except socket.timeout:
        return "non conclusive"

    try:
        result = subprocess.run(
            ["whois", domain], capture_output=True, text=True, timeout=DNS_TIMEOUT
        )
        whois_output = result.stdout.lower()

        if contains_any_keyword(whois_output, FREE_KEYWORDS):
            return "free"

        if contains_any_keyword(whois_output, REGISTERED_KEYWORDS):
            return "registered"
    except subprocess.TimeoutExpired as e:
        partial_output = (e.output or "").lower()

        print(
            f"WHOIS lookup timed out for {domain}. Partial output: {partial_output}"
        )

        if contains_any_keyword(partial_output, FREE_KEYWORDS):
            return "free"
        if contains_any_keyword(partial_output, REGISTERED_KEYWORDS):
            return "registered"

    except Exception as e:  # pragma: no cover - log unexpected errors
        print(f"Error during WHOIS lookup for {domain}: {e}")

    return "non conclusive"


def normalize_domain(input_string: str) -> str:
    parsed = urlparse(input_string)
    domain = parsed.netloc if parsed.netloc else input_string
    return domain.strip().lower()


def dns_lookup_with_timeout(domain: str, timeout: float = DNS_TIMEOUT) -> str:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(socket.gethostbyname, domain)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise socket.timeout(f"DNS resolution timed out after {timeout} seconds.")


def contains_any_keyword(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)

