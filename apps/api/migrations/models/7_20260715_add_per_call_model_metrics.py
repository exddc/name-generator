from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "llm_generation_metrics" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "generation_path" VARCHAR(32) NOT NULL,
            "requested_model" VARCHAR(128) NOT NULL,
            "actual_model" VARCHAR(128) NOT NULL,
            "prompt_tokens" INT NOT NULL DEFAULT 0,
            "completion_tokens" INT NOT NULL DEFAULT 0,
            "total_tokens" INT NOT NULL DEFAULT 0,
            "cost_usd" DECIMAL(12,8) NOT NULL DEFAULT 0,
            "latency_ms" INT NOT NULL,
            "fallback_used" BOOL NOT NULL DEFAULT FALSE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "suggestion_id" INT NOT NULL REFERENCES "suggestions" ("id") ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS "idx_llm_generation_suggestion"
            ON "llm_generation_metrics" ("suggestion_id");
        CREATE INDEX IF NOT EXISTS "idx_llm_generation_created"
            ON "llm_generation_metrics" ("created_at");
        CREATE INDEX IF NOT EXISTS "idx_llm_generation_model_created"
            ON "llm_generation_metrics" ("actual_model", "created_at");
        CREATE INDEX IF NOT EXISTS "idx_llm_generation_path_created"
            ON "llm_generation_metrics" ("generation_path", "created_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "llm_generation_metrics";
    """
