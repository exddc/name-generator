from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "favorites" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "domain_id" VARCHAR(255) NOT NULL REFERENCES "domains" ("domain") ON DELETE CASCADE,
    CONSTRAINT "uid_favorites_domain__a1b2c3" UNIQUE ("domain_id", "user_id")
);
CREATE INDEX IF NOT EXISTS "idx_favorites_domain__d4e5f6" ON "favorites" ("domain_id");
CREATE INDEX IF NOT EXISTS "idx_favorites_user_id_g7h8i9" ON "favorites" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_favorites_created_j0k1l2" ON "favorites" ("created_at");
COMMENT ON TABLE "favorites" IS 'User favorites for domains.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "favorites";"""

