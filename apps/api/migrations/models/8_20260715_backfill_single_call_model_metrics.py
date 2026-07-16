from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        INSERT INTO "llm_generation_metrics" (
            "suggestion_id",
            "generation_path",
            "requested_model",
            "actual_model",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "cost_usd",
            "latency_ms",
            "fallback_used",
            "created_at"
        )
        SELECT
            metrics."suggestion_id",
            COALESCE(metrics."generation_path", 'unknown'),
            metrics."requested_model",
            metrics."actual_model",
            COALESCE(metrics."llm_tokens_prompt", 0),
            COALESCE(metrics."llm_tokens_completion", 0),
            COALESCE(metrics."llm_tokens_total", 0),
            COALESCE(metrics."llm_cost_usd", 0),
            COALESCE(metrics."llm_total_duration_ms", metrics."total_duration_ms", 0),
            metrics."fallback_used",
            metrics."created_at"
        FROM "suggestion_metrics" AS metrics
        WHERE metrics."llm_call_count" = 1
          AND metrics."requested_model" IS NOT NULL
          AND metrics."actual_model" IS NOT NULL
          AND metrics."actual_model" <> 'mixed'
          AND NOT EXISTS (
              SELECT 1
              FROM "llm_generation_metrics" AS calls
              WHERE calls."suggestion_id" = metrics."suggestion_id"
          );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    # The backfilled rows are valid measurements and deliberately survive a
    # code rollback. Migration 7 removes the table if the schema is rolled back.
    return """SELECT 1;"""
