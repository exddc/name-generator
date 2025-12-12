#!/usr/bin/env python3
"""
Helper script to mint short-lived API JWTs for local testing.

Usage:
    python scripts/generate_jwt.py --user-id abc123 --email user@example.com --scopes metrics:read
"""

import argparse
import os
import sys
import time
import jwt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate API bearer tokens for manual testing.")
    parser.add_argument("--user-id", required=True, help="Subject/user id that the token should represent.")
    parser.add_argument("--email", help="Optional email claim to embed.")
    parser.add_argument("--name", help="Optional name claim to embed.")
    parser.add_argument(
        "--session-id",
        help="Optional session identifier to embed in the token (defaults to the user id).",
    )
    parser.add_argument(
        "--scopes",
        nargs="*",
        help="Optional list of scopes (e.g. metrics:read). Separate entries by space.",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=int(os.environ.get("API_JWT_TTL_SECONDS", "300")),
        help="Token lifetime in seconds (default: %(default)s)",
    )
    return parser.parse_args()


def get_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    args = parse_args()
    secret = get_env("API_JWT_SECRET")
    issuer = get_env("API_JWT_ISSUER", "domain-generator-web")
    audience = get_env("API_JWT_AUDIENCE", "domain-generator-api")
    algorithm = get_env("API_JWT_ALGORITHM", "HS256")

    issued_at = int(time.time())
    expires_at = issued_at + args.ttl

    payload = {
        "sub": args.user_id,
        "email": args.email,
        "name": args.name,
        "session_id": args.session_id or args.user_id,
        "scopes": args.scopes or [],
        "iat": issued_at,
        "exp": expires_at,
        "iss": issuer,
        "aud": audience,
    }

    token = jwt.encode(payload, secret, algorithm=algorithm)
    sys.stdout.write(token)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
