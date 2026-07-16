import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_compose_blocks_api_until_migrations_complete():
    compose = (REPOSITORY_ROOT / "docker-compose.yaml").read_text()
    migrate_service = re.search(
        r"(?ms)^  migrate:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\n)", compose
    )
    api_service = re.search(
        r"(?ms)^  api:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\n)", compose
    )

    assert migrate_service
    assert 'command: ["aerich", "upgrade"]' in migrate_service.group("body")
    assert api_service
    assert re.search(
        r"(?m)^      migrate:\n        condition: service_completed_successfully$",
        api_service.group("body"),
    )


def test_rollback_ordering_is_documented():
    readme = (REPOSITORY_ROOT / "apps" / "api" / "README.md").read_text()
    assert "**Rollback ordering:**" in readme
    assert "stop all API replicas" in readme
    assert "aerich downgrade" in readme
