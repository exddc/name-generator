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


def check_domains(domains: Sequence[str]) -> List[DomainCheckResult]:
    results: List[DomainCheckResult] = []
    for domain in domains:
        status = check_domain(domain)
        results.append(DomainCheckResult(domain=domain, status=status))
    return results


def check_domain(domain: str) -> str:
    domain = normalize_domain(domain)

    try:
        dns_lookup_with_timeout(domain, timeout=DNS_TIMEOUT)
        return "registered"
    except socket.gaierror:
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

