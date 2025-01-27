from os import environ
import datetime
import requests
import tldextract

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Domain

DB_HOST = environ.get("DB_HOST")
DB_PORT = int(environ.get("DB_PORT"))
DB_USER = environ.get("DB_USER")
DB_PASSWORD = environ.get("DB_PASSWORD")

DB_NAME = environ.get("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DOMAIN_CHECKER_URL = environ.get("DOMAIN_CHECKER_URL")
NAME_SUGGESTOR_URL = environ.get("NAME_SUGGESTOR_URL")
DOMAIN_CHECKER_ENDPOINT = environ.get("DOMAIN_CHECKER_ENDPOINT")
NAME_SUGGESTOR_ENDPOINT = environ.get("NAME_SUGGESTOR_ENDPOINT")


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


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
    tld = extracted.suffix

    return domain_name, tld


def query_domain_checker(domains: list[str]) -> list[dict]:
    """
    Calls the external domain-checker service with:
      POST { "domains": [...] }
    Expects a response of the form:
      [ { "domain": "<domain>", "status": "<status>" }, ... ]
    """
    payload = {"domains": domains}
    resp = requests.post(
        DOMAIN_CHECKER_URL + DOMAIN_CHECKER_ENDPOINT, json=payload, timeout=20
    )
    resp.raise_for_status()
    return resp.json()


def get_or_update_domain(session, full_domain: str):
    """
    1. Extract domain_name, tld using tldextract.
    2. Check if in DB:
       - If last_checked < 1 hour => return existing record.
       - Else => call domain-checker, update record, return new.
    3. If not in DB => call domain-checker, insert record.
    """
    domain_name, tld = extract_domain_tld(full_domain)

    try:
        existing = (
            session.query(Domain).filter_by(domain_name=domain_name, tld=tld).first()
        )
    except Exception as e:
        print(f"Error while querying domain: {e}")
        existing = None

    # If found and less than 12 hour old, return it
    if existing:
        time_diff = datetime.datetime.utcnow() - existing.last_checked
        if time_diff.total_seconds() < 3600 * 12:
            return existing

    microservice_result = query_domain_checker([full_domain])
    if not microservice_result:
        raise ValueError("Domain-checker returned no results.")

    new_status = microservice_result[0]["status"]

    if existing:
        existing.status = new_status
        existing.last_checked = datetime.datetime.utcnow()
        session.commit()
        return existing
    else:
        new_domain = Domain(
            domain_name=domain_name,
            tld=tld,
            status=new_status,
            last_checked=datetime.datetime.utcnow(),
        )
        session.add(new_domain)
        session.commit()
        return new_domain


def query_name_suggestor(query: str) -> list[str]:
    """
    Calls the external name-suggestor service with:
      POST { "query": "..." }
    Expects a response of the form:
        { "suggestions": [...] }
    """
    payload = {"query": query}
    resp = requests.post(
        NAME_SUGGESTOR_URL + NAME_SUGGESTOR_ENDPOINT, json=payload, timeout=60
    )
    resp.raise_for_status()
    return resp.json().get("suggestions", [])


def check_services_connections() -> str:
    """
    Check if the services are reachable.
    """
    services = []
    try:
        resp = requests.get(DOMAIN_CHECKER_URL + "health", timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(msg := f"Error connecting to domain-checker: {e}")
        print(f"Used URL: {DOMAIN_CHECKER_URL + 'health'}")
        services.append(msg)

    try:
        resp = requests.get(NAME_SUGGESTOR_URL + "health", timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(msg := f"Error connecting to name-suggestor: {e}")
        print(f"Used URL: {NAME_SUGGESTOR_URL + 'health'}")
        services.append(msg)

    if not services:
        return "All services are reachable"

    return "Some services are unreachable: " + ", ".join(services)
