from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "suggestions" ALTER COLUMN "user_id" TYPE VARCHAR(255) USING "user_id"::VARCHAR(255);
        CREATE TABLE IF NOT EXISTS "suggestion_metrics" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "total_duration_ms" INT,
    "llm_total_duration_ms" INT,
    "worker_total_duration_ms" INT,
    "db_write_duration_ms" INT,
    "time_to_first_suggestion_ms" INT,
    "llm_attempt_durations_ms" JSONB,
    "worker_attempt_durations_ms" JSONB,
    "retry_count" INT NOT NULL  DEFAULT 0,
    "llm_call_count" INT NOT NULL  DEFAULT 0,
    "worker_job_count" INT NOT NULL  DEFAULT 0,
    "total_domains_generated" INT NOT NULL  DEFAULT 0,
    "unique_domains_generated" INT NOT NULL  DEFAULT 0,
    "domains_returned" INT NOT NULL  DEFAULT 0,
    "available_domains_count" INT NOT NULL  DEFAULT 0,
    "registered_domains_count" INT NOT NULL  DEFAULT 0,
    "unknown_domains_count" INT NOT NULL  DEFAULT 0,
    "success_rate" DOUBLE PRECISION,
    "reached_target" BOOL NOT NULL  DEFAULT False,
    "llm_tokens_total" INT,
    "llm_tokens_prompt" INT,
    "llm_tokens_completion" INT,
    "error_count" INT NOT NULL  DEFAULT 0,
    "error_messages" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "suggestion_id" INT NOT NULL REFERENCES "suggestions" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_suggestion__suggest_f41e6c" ON "suggestion_metrics" ("suggestion_id");
CREATE INDEX IF NOT EXISTS "idx_suggestion__created_1603bf" ON "suggestion_metrics" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_suggestion__retry_c_305285" ON "suggestion_metrics" ("retry_count");
CREATE INDEX IF NOT EXISTS "idx_suggestion__success_327db6" ON "suggestion_metrics" ("success_rate");
COMMENT ON TABLE "suggestion_metrics" IS 'Performance and timing metrics for each suggestion request.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "suggestions" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        DROP TABLE IF EXISTS "suggestion_metrics";"""
