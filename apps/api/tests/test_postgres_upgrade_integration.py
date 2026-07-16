import asyncio
import importlib.util
import os
import socket
import tracemalloc
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import asyncpg
import httpx
import jwt
import pytest
from tortoise import Tortoise


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION_TEST") != "1",
    reason="set RUN_POSTGRES_INTEGRATION_TEST=1 with local PostgreSQL",
)

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations" / "models"
ADMIN_URL = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    "postgresql://postgres:password@127.0.0.1:5432/postgres",
)


async def _migration_sql(version: int, direction: str = "upgrade") -> str:
    path = next(MIGRATIONS.glob(f"{version}_*.py"))
    spec = importlib.util.spec_from_file_location(f"migration_{version}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class StubDB:
        pass

    return await getattr(module, direction)(StubDB())


async def _exercise_upgrade() -> None:
    database_name = f"tw266_{uuid.uuid4().hex}"
    admin = await asyncpg.connect(ADMIN_URL)
    target = None
    tortoise_initialized = False
    try:
        await admin.execute(f'CREATE DATABASE "{database_name}"')
        target_url = ADMIN_URL.rsplit("/", 1)[0] + f"/{database_name}"
        target = await asyncpg.connect(target_url)

        for version in range(6):
            await target.execute(await _migration_sql(version))

        suggestion_id = await target.fetchval(
            """
            INSERT INTO suggestions (description, count, model, prompt, user_id)
            VALUES ('pre-upgrade', 1, 'openai/gpt-oss-20b', 'legacy', 'upgrade-test')
            RETURNING id
            """
        )
        await target.execute(
            """
            INSERT INTO suggestion_metrics
                (suggestion_id, total_duration_ms, llm_call_count,
                 total_domains_generated, unique_domains_generated,
                 domains_returned, available_domains_count, success_rate,
                 reached_target)
            VALUES ($1, 125, 1, 1, 1, 1, 1, 1, TRUE)
            """,
            suggestion_id,
        )

        # The v5 -> current upgrade is safe to retry after partial deployment work.
        for version in (6, 7, 8, 6, 7, 8):
            await target.execute(await _migration_sql(version))

        # Generate enough history to prove the endpoint never materializes it in Python.
        await target.execute(
            """
            INSERT INTO suggestion_metrics (
                suggestion_id, total_duration_ms, llm_total_duration_ms,
                llm_call_count, total_domains_generated,
                unique_domains_generated, domains_returned,
                available_domains_count, success_rate, reached_target,
                llm_tokens_total, llm_cost_usd, generation_path,
                requested_model, actual_model, fallback_used,
                creative_path_duration_ms, created_at
            )
            SELECT $1, 100 + (n % 900), 50 + (n % 400), 1, 1, 1, 1, 1,
                   1, TRUE, 100, 0.00001000, 'lexicon',
                   'openai/gpt-oss-120b',
                   CASE WHEN n % 2 = 0 THEN 'openai/gpt-oss-120b'
                        ELSE 'openai/gpt-oss-20b' END,
                   n % 2 = 1, 50 + (n % 400),
                   CURRENT_TIMESTAMP - (n || ' milliseconds')::interval
            FROM generate_series(1, 120000) AS n
            """,
            suggestion_id,
        )
        await target.execute(
            """
            INSERT INTO llm_generation_metrics (
                suggestion_id, generation_path, requested_model, actual_model,
                prompt_tokens, completion_tokens, total_tokens, cost_usd,
                latency_ms, fallback_used, created_at
            )
            SELECT $1, 'lexicon', 'openai/gpt-oss-120b',
                   CASE WHEN n % 2 = 0 THEN 'openai/gpt-oss-120b'
                        ELSE 'openai/gpt-oss-20b' END,
                   80, 20, 100, 0.00001000, 50 + (n % 400), n % 2 = 1,
                   CURRENT_TIMESTAMP - (n || ' milliseconds')::interval
            FROM generate_series(1, 120000) AS n
            """,
            suggestion_id,
        )
        await target.execute("ANALYZE suggestion_metrics")

        plan_rows = await target.fetch(
            """
            EXPLAIN (FORMAT TEXT)
            SELECT total_duration_ms
            FROM suggestion_metrics
            WHERE total_duration_ms IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 100000
            """
        )
        plan = "\n".join(row[0] for row in plan_rows)
        assert "Index Scan" in plan

        await target.close()
        target = None

        await Tortoise.init(
            config={
                "connections": {
                    "default": target_url.replace("postgresql://", "postgres://", 1)
                },
                "apps": {
                    "models": {
                        "models": ["api.models.db_models", "aerich.models"],
                        "default_connection": "default",
                    }
                },
            }
        )
        tortoise_initialized = True

        from api.config import get_settings
        from api.main import init_fastapi
        from api.models.db_models import LlmGenerationMetric, SuggestionMetrics
        from api.utils import MetricsTracker

        tracker = MetricsTracker(generation_path="lexicon")
        tracker._durations["llm"] = [400.0, 600.0]
        tracker.increment_llm_call()
        tracker.increment_llm_call()
        tracker.record_llm_generation(
            requested_model="openai/gpt-oss-120b",
            actual_model="openai/gpt-oss-20b",
            usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
            cost_usd=0.000012,
            latency_ms=400,
            fallback_used=True,
        )
        tracker.record_llm_generation(
            requested_model="openai/gpt-oss-120b",
            actual_model="openai/gpt-oss-120b",
            usage={"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200},
            cost_usd=0.0000525,
            latency_ms=600,
            fallback_used=False,
        )
        await tracker.save(suggestion_id=suggestion_id, requested_count=1)

        request_rows_before = await SuggestionMetrics.filter(
            suggestion_id=suggestion_id
        ).count()
        call_rows_before = await LlmGenerationMetric.filter(
            suggestion_id=suggestion_id
        ).count()
        failing_tracker = MetricsTracker(generation_path="lexicon")
        failing_tracker.record_llm_generation(
            requested_model="openai/gpt-oss-120b",
            actual_model="openai/gpt-oss-120b",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            cost_usd=0.0000045,
            latency_ms=100,
            fallback_used=False,
        )
        with patch.object(
            LlmGenerationMetric,
            "bulk_create",
            new=AsyncMock(side_effect=RuntimeError("injected per-call write failure")),
        ), pytest.raises(RuntimeError, match="injected per-call write failure"):
            await failing_tracker.save(suggestion_id=suggestion_id, requested_count=1)

        assert await SuggestionMetrics.filter(
            suggestion_id=suggestion_id
        ).count() == request_rows_before
        assert await LlmGenerationMetric.filter(
            suggestion_id=suggestion_id
        ).count() == call_rows_before

        settings = get_settings()
        token = jwt.encode(
            {
                "sub": "upgrade-test",
                "scopes": ["metrics:read"],
                "iss": settings.api_jwt_issuer,
                "aud": settings.api_jwt_audience,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            settings.api_jwt_secret,
            algorithm=settings.api_jwt_algorithm,
        )
        app = init_fastapi()
        transport = httpx.ASGITransport(app=app)
        tracemalloc.start()
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/v1/metrics/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert response.status_code == 200, response.text
        summary = response.json()
        assert summary["creative_request_count"] == 120001
        assert len(summary["model_breakdown"]) == 2
        assert summary["total_llm_cost_usd"] == pytest.approx(1.2000645)
        breakdown = {row["actual_model"]: row for row in summary["model_breakdown"]}
        assert breakdown["openai/gpt-oss-20b"] == {
            "actual_model": "openai/gpt-oss-20b",
            "request_count": 60001,
            "avg_latency_ms": pytest.approx((60000 * 250 + 400) / 60001),
            "avg_llm_latency_ms": pytest.approx((60000 * 250 + 400) / 60001),
            "total_cost_usd": pytest.approx(0.600012),
            "fallback_count": 60001,
            "prompt_tokens": 4_800_080,
            "completion_tokens": 1_200_020,
            "total_tokens": 6_000_100,
        }
        assert breakdown["openai/gpt-oss-120b"] == {
            "actual_model": "openai/gpt-oss-120b",
            "request_count": 60001,
            "avg_latency_ms": pytest.approx((60000 * 249 + 600) / 60001),
            "avg_llm_latency_ms": pytest.approx((60000 * 249 + 600) / 60001),
            "total_cost_usd": pytest.approx(0.6000525),
            "fallback_count": 0,
            "prompt_tokens": 4_800_150,
            "completion_tokens": 1_200_050,
            "total_tokens": 6_000_200,
        }
        assert peak < 20 * 1024 * 1024
    finally:
        if tortoise_initialized:
            await Tortoise.close_connections()
        if target is not None:
            await target.close()
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1",
            database_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        await admin.close()


def test_populated_v5_upgrade_boots_api_and_keeps_summary_memory_bounded():
    asyncio.run(_exercise_upgrade())


async def _exercise_fresh_aerich_bootstrap() -> None:
    database_name = f"tw266_fresh_{uuid.uuid4().hex}"
    admin = await asyncpg.connect(ADMIN_URL)
    api_process = None
    try:
        await admin.execute(f'CREATE DATABASE "{database_name}"')
        target_url = ADMIN_URL.rsplit("/", 1)[0] + f"/{database_name}"
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": target_url.replace("postgresql://", "postgres://", 1),
                "GROQ_VALIDATE_MODEL_ON_STARTUP": "false",
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            }
        )

        migration = await asyncio.create_subprocess_exec(
            str(Path(__file__).resolve().parents[1] / ".venv" / "bin" / "aerich"),
            "upgrade",
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        migration_output, _ = await migration.communicate()
        assert migration.returncode == 0, migration_output.decode()

        target = await asyncpg.connect(target_url)
        try:
            assert await target.fetchval(
                "SELECT version FROM aerich ORDER BY id DESC LIMIT 1"
            ) == "8_20260715_backfill_single_call_model_metrics.py"
            for table in (
                "worker_metrics",
                "queue_snapshots",
                "suggestion_metrics",
                "llm_generation_metrics",
            ):
                assert await target.fetchval("SELECT to_regclass($1)", table) == table
        finally:
            await target.close()

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

        api_process = await asyncio.create_subprocess_exec(
            str(Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python"),
            "-m",
            "uvicorn",
            "api.main:singleton",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            for _ in range(50):
                try:
                    response = await client.get("/health/")
                    if response.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.1)
            else:
                api_process.terminate()
                output, _ = await api_process.communicate()
                pytest.fail(f"API did not start after fresh migrations:\n{output.decode()}")

        assert response.json()["dependencies"]["database"] == "ok"
    finally:
        if api_process is not None and api_process.returncode is None:
            api_process.terminate()
            await api_process.wait()
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1",
            database_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        await admin.close()


def test_fresh_database_runs_real_aerich_history_and_starts_api():
    asyncio.run(_exercise_fresh_aerich_bootstrap())
