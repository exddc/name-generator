import os
import datetime
import requests
import tldextract

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Domain

# =========================================================
# 1. Database Session Setup
# =========================================================

DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "securepassword")
DB_NAME = os.getenv("DB_NAME", "domain_generator")
DB_HOST = os.getenv("DB_HOST", "localhost")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


# =========================================================
# 2. Enhanced Domain Extraction (handles .co.uk, etc.)
# =========================================================


def extract_domain_tld(full_domain: str):
    """
    Use tldextract to handle multi-level TLDs (e.g., co.uk).
    This splits the full domain (subdomain + domain + tld) into:
      - domain_name = extracted.domain  (e.g. 'example')
      - tld = extracted.suffix         (e.g. 'co.uk')
      - subdomain = extracted.subdomain (not used here, but available)
    """
    # Clean up scheme and trailing slashes if the user provides http:// or https://
    full_domain = full_domain.strip().rstrip("/")

    extracted = tldextract.extract(full_domain)
    # e.g. for 'https://sub.example.co.uk' => subdomain='sub', domain='example', suffix='co.uk'

    domain_name = extracted.domain
    tld = extracted.suffix  # 'com', 'co.uk', etc.

    return domain_name, tld


# =========================================================
# 3. Query Domain Checker Microservice
# =========================================================

DOMAIN_CHECKER_URL = os.getenv(
    "DOMAIN_CHECKER_URL", "http://localhost:8001/checkdomain"
)


def query_domain_checker(domains: list[str]) -> list[dict]:
    """
    Calls the external domain-checker service with:
      POST { "domains": [...] }
    Expects a response of the form:
      [ { "domain": "<domain>", "status": "<status>" }, ... ]
    """
    payload = {"domains": domains}
    resp = requests.post(DOMAIN_CHECKER_URL, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


# =========================================================
# 4. Upsert / Fetch Logic
# =========================================================


def get_or_update_domain(session, full_domain: str):
    """
    1. Extract domain_name, tld using tldextract.
    2. Check if in DB:
       - If last_checked < 1 hour => return existing record.
       - Else => call domain-checker, update record, return new.
    3. If not in DB => call domain-checker, insert record.
    """
    domain_name, tld = extract_domain_tld(full_domain)

    existing = session.query(Domain).filter_by(domain_name=domain_name, tld=tld).first()

    # If found and less than 1 hour old, return it
    if existing:
        time_diff = datetime.datetime.utcnow() - existing.last_checked
        if time_diff.total_seconds() < 3600:  # < 1 hour
            return existing  # Return existing record

    # Need to call domain-checker (because not in DB or older than 1 hour)
    microservice_result = query_domain_checker([full_domain])
    # Expect e.g. [ { "domain": "...", "status": "..." } ]
    if not microservice_result:
        # If domain-checker returns empty or error
        raise ValueError("Domain-checker returned no results.")

    new_status = microservice_result[0]["status"]

    if existing:
        # Update existing record
        existing.status = new_status
        existing.last_checked = datetime.datetime.utcnow()
        session.commit()
        return existing
    else:
        # Create new record
        new_domain = Domain(
            domain_name=domain_name,
            tld=tld,
            status=new_status,
            last_checked=datetime.datetime.utcnow(),
        )
        session.add(new_domain)
        session.commit()
        return new_domain
