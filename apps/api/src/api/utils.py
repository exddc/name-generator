from os import environ
import datetime
import requests
import tldextract

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Domain
from .domain_check import check_domain

DB_HOST = environ.get("DB_HOST", "http://postgres")
DB_PORT = int(environ.get("DB_PORT", 5432))
DB_USER = environ.get("DB_USER", "postgres")
DB_PASSWORD = environ.get("DB_PASSWORD", "password")

DB_NAME = environ.get("DB_NAME", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"DATABASE_URL: {DATABASE_URL}")
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

    new_status = check_domain(full_domain)
    if not new_status:
        raise ValueError("Domain-checker returned no results.")

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


def check_services_connections(session) -> str:
    """
    Check if the services are reachable.
    """
    services = []
    try:
        session.query(Domain).first()
    except Exception as e:
        print(msg := f"Error connecting to DB: {e}")
        services.append(msg)

    if not services:
        return "All services are reachable"

    return "Some services are unreachable: " + ", ".join(services)
