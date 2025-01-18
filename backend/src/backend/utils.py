import os
import datetime
import requests
import tldextract
import dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Domain

dotenv.load_dotenv()

DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

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
    resp = requests.post(os.getenv("DOMAIN_CHECKER_URL"), json=payload, timeout=20)
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
    resp = requests.post(os.getenv("NAME_SUGGESTOR_URL"), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json().get("suggestions", [])
