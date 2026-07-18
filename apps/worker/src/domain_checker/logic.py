"""Core domain checking logic for queue workers and web handlers."""

from __future__ import annotations

import concurrent.futures
import os
import re
import socket
import subprocess
from typing import Iterable, List, Sequence

from pydantic import BaseModel


DNS_TIMEOUT = float(os.getenv("DOMAIN_CHECKER_DNS_TIMEOUT", "3.0"))
DOMAIN_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


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
        try:
            status = check_domain(domain)
            results.append(DomainCheckResult(domain=domain, status=status))
        except Exception as e:
            print(f"[Worker] Error checking domain '{domain}': {e}")
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
    value = input_string.strip().lower().rstrip(".")
    if not value or len(value) > 253 or "." not in value:
        raise ValueError("domain must contain a public suffix")
    if any(character in value for character in ("/", ":", "@")):
        raise ValueError("URLs and credentials are not domain names")
    if any(ord(character) > 127 for character in value):
        raise ValueError("domain must use ASCII or punycode labels")

    labels = value.split(".")
    if any(DOMAIN_LABEL_PATTERN.fullmatch(label) is None for label in labels):
        raise ValueError("domain contains an invalid label")
    if labels[-1].isdigit():
        raise ValueError("domain suffix must not be numeric")
    return value


def dns_lookup_with_timeout(domain: str, timeout: float = DNS_TIMEOUT) -> str:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(socket.gethostbyname, domain)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise socket.timeout(f"DNS resolution timed out after {timeout} seconds.")


def contains_any_keyword(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)
