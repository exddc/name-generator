import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DOCKER_BOOTSTRAP_TEST") != "1",
    reason="set RUN_DOCKER_BOOTSTRAP_TEST=1 to exercise clean Compose volumes",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def test_clean_compose_volume_migrates_before_api_startup():
    project = f"tw266fresh{uuid.uuid4().hex[:10]}"
    api_port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "COMPOSE_PROJECT_NAME": project,
            "API_PORT": str(api_port),
            "POSTGRES_HOST_PORT": str(_free_port()),
            "REDIS_PORT": str(_free_port()),
            "GROQ_API_KEY": env.get("GROQ_API_KEY", "fresh-bootstrap-test"),
            "GROQ_VALIDATE_MODEL_ON_STARTUP": "false",
            "API_JWT_SECRET": env.get("API_JWT_SECRET", "fresh-bootstrap-secret"),
        }
    )
    compose = [
        "docker",
        "compose",
        "--profile",
        "infra",
        "--profile",
        "backend",
    ]

    try:
        startup = subprocess.run(
            [*compose, "up", "-d", "--build"],
            cwd=REPOSITORY_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
        assert startup.returncode == 0, startup.stdout

        for _ in range(60):
            try:
                with urlopen(f"http://127.0.0.1:{api_port}/health/", timeout=1) as response:
                    payload = json.load(response)
                if response.status == 200:
                    break
            except OSError:
                pass
            time.sleep(0.25)
        else:
            logs = subprocess.run(
                [*compose, "logs", "--no-color", "migrate", "api"],
                cwd=REPOSITORY_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ).stdout
            pytest.fail(f"API did not start from clean Compose volumes:\n{logs}")

        migrate_container = subprocess.check_output(
            [*compose, "ps", "-a", "-q", "migrate"],
            cwd=REPOSITORY_ROOT,
            env=env,
            text=True,
        ).strip()
        exit_code = subprocess.check_output(
            ["docker", "inspect", "-f", "{{.State.ExitCode}}", migrate_container],
            text=True,
        ).strip()
        assert exit_code == "0"
        assert payload["dependencies"]["database"] == "ok"
    finally:
        subprocess.run(
            [*compose, "down", "-v", "--remove-orphans"],
            cwd=REPOSITORY_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
