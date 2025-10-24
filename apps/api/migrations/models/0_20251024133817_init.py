from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "suggestions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "description" VARCHAR(1024) NOT NULL,
    "count" INT NOT NULL,
    "model" VARCHAR(128) NOT NULL,
    "prompt" VARCHAR(4096) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT
);
CREATE INDEX IF NOT EXISTS "idx_suggestions_user_id_edc136" ON "suggestions" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_suggestions_created_23a2f0" ON "suggestions" ("created_at");
CREATE TABLE IF NOT EXISTS "domains" (
    "domain" VARCHAR(255) NOT NULL  PRIMARY KEY,
    "domain_name" VARCHAR(200) NOT NULL,
    "tld" VARCHAR(63) NOT NULL,
    "status" VARCHAR(10) NOT NULL  DEFAULT 'unknown',
    "last_checked" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "upvotes" INT NOT NULL  DEFAULT 0,
    "downvotes" INT NOT NULL  DEFAULT 0,
    "suggestion_id" INT REFERENCES "suggestions" ("id") ON DELETE SET NULL,
    CONSTRAINT "uid_domains_domain__367fb2" UNIQUE ("domain_name", "tld")
);
CREATE INDEX IF NOT EXISTS "idx_domains_status_609434" ON "domains" ("status");
CREATE INDEX IF NOT EXISTS "idx_domains_status_9367af" ON "domains" ("status", "last_checked");
CREATE INDEX IF NOT EXISTS "idx_domains_suggest_68da08" ON "domains" ("suggestion_id");
COMMENT ON COLUMN "domains"."status" IS 'AVAILABLE: available\nREGISTERED: registered\nUNKNOWN: unknown';
CREATE TABLE IF NOT EXISTS "ratings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "vote" INT NOT NULL,
    "rater_key" VARCHAR(128) NOT NULL,
    "user_id" INT,
    "shown_index" INT,
    "model_version" VARCHAR(64),
    "search_id" INT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "domain_id" VARCHAR(255) NOT NULL REFERENCES "domains" ("domain") ON DELETE CASCADE,
    "suggestion_id" INT NOT NULL REFERENCES "suggestions" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_ratings_domain__951296" UNIQUE ("domain_id", "rater_key")
);
CREATE INDEX IF NOT EXISTS "idx_ratings_domain__cca94c" ON "ratings" ("domain_id");
CREATE INDEX IF NOT EXISTS "idx_ratings_suggest_838da5" ON "ratings" ("suggestion_id");
CREATE INDEX IF NOT EXISTS "idx_ratings_rater_k_481b8d" ON "ratings" ("rater_key");
CREATE INDEX IF NOT EXISTS "idx_ratings_user_id_dc15e8" ON "ratings" ("user_id");
COMMENT ON TABLE "ratings" IS 'Binary thumbs voting with unified rater identity.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
