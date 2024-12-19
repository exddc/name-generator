import hashlib


def generate_uid(domain_name: str, tld: str) -> str:
    """Generate a unique identifier for the domain."""
    return hashlib.md5(f"{domain_name}.{tld}".encode()).hexdigest()
