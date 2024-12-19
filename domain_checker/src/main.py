import whois
import logging
import time
from cachetools import TTLCache
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# Cache to store recent lookups with a TTL of 1 hour
cache = TTLCache(maxsize=1000, ttl=3600)

# Initialize FastAPI app
app = FastAPI()


def analyze_whois_data(whois_data: str) -> Optional[bool]:
    """Analyzes WHOIS data to determine if the domain is available or taken."""
    lower_data = whois_data.lower()
    if (
        "no match" in lower_data
        or "not found" in lower_data
        or "no such domain" in lower_data
    ):
        return True  # Domain is available
    if "domain name" in lower_data and "registrar" in lower_data:
        return False  # Domain is taken
    return None  # Unable to determine


def is_domain_available(
    domain: str, retries: int = 3, sleep_between_retries: int = 2
) -> Optional[str]:
    """Checks if a domain is available using WHOIS."""
    # Check cache first
    if domain in cache:
        logging.info(f"Cache hit for {domain}: {cache[domain]}")
        return cache[domain]

    attempt = 0
    while attempt < retries:
        try:
            # Perform WHOIS lookup
            w = whois.whois(domain)
            whois_data = str(w)

            # Analyze the WHOIS data
            analysis_result = analyze_whois_data(whois_data)
            if analysis_result is True:
                logging.info(f"The domain {domain} appears to be available.")
                cache[domain] = "available"
                return "available"
            elif analysis_result is False:
                logging.info(f"The domain {domain} is already registered.")
                cache[domain] = "taken"
                return "taken"

        except whois.parser.PywhoisError as e:
            logging.warning(f"WHOIS lookup failed for {domain}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking {domain}: {e}")

        attempt += 1
        time.sleep(sleep_between_retries)

    # If unable to determine from WHOIS
    logging.warning(
        f"Unable to confirm domain status for {domain} after {retries} attempts."
    )
    cache[domain] = "uncertain"
    return "uncertain"


@app.get("/v1/health")
async def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "ok"}


@app.post("/v1/check")
async def check_domains(domains: List[str]) -> Dict[str, str]:
    """Endpoint to check the availability of one or more domains."""
    if not domains:
        raise HTTPException(status_code=400, detail="No domains provided.")

    results = {}
    for domain in domains:
        status = is_domain_available(domain)
        results[domain] = status

    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
