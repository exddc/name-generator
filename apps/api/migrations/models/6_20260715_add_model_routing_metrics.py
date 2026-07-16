from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "suggestion_metrics"
            ADD COLUMN IF NOT EXISTS "llm_cost_usd" DECIMAL(12,8),
            ADD COLUMN IF NOT EXISTS "generation_path" VARCHAR(32),
            ADD COLUMN IF NOT EXISTS "requested_model" VARCHAR(128),
            ADD COLUMN IF NOT EXISTS "actual_model" VARCHAR(128),
            ADD COLUMN IF NOT EXISTS "fallback_used" BOOL NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS "creative_path_duration_ms" INT;
        CREATE INDEX IF NOT EXISTS "idx_suggestion_metrics_actual_model"
            ON "suggestion_metrics" ("actual_model");
        CREATE INDEX IF NOT EXISTS "idx_suggestion_metrics_generation_path"
            ON "suggestion_metrics" ("generation_path");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_suggestion_metrics_generation_path";
        DROP INDEX IF EXISTS "idx_suggestion_metrics_actual_model";
        ALTER TABLE "suggestion_metrics"
            DROP COLUMN IF EXISTS "creative_path_duration_ms",
            DROP COLUMN IF EXISTS "fallback_used",
            DROP COLUMN IF EXISTS "actual_model",
            DROP COLUMN IF EXISTS "requested_model",
            DROP COLUMN IF EXISTS "generation_path",
            DROP COLUMN IF EXISTS "llm_cost_usd";
    """
