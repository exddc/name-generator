from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "suggestion_metrics" ADD COLUMN IF NOT EXISTS "queue_depth_at_start" INT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "suggestion_metrics" DROP COLUMN IF EXISTS "queue_depth_at_start";
    """

