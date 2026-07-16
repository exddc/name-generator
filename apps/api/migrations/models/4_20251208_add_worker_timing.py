from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- worker_metrics existed in the application model before it was added to
        -- the checked-in Aerich history. Create the original shape so a fresh
        -- database can replay the real migration chain without schema bootstrap.
        CREATE TABLE IF NOT EXISTS "worker_metrics" (
            "worker_id" VARCHAR(255) NOT NULL PRIMARY KEY,
            "total_jobs" INT NOT NULL DEFAULT 0,
            "last_seen" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Add new timing columns to worker_metrics
        ALTER TABLE "worker_metrics" 
            ADD COLUMN IF NOT EXISTS "total_processing_time_ms" INT NOT NULL DEFAULT 0;
        ALTER TABLE "worker_metrics" 
            ADD COLUMN IF NOT EXISTS "total_queue_wait_time_ms" INT NOT NULL DEFAULT 0;
        
        -- Create queue_snapshots table for accurate queue monitoring
        CREATE TABLE IF NOT EXISTS "queue_snapshots" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "queue_depth" INT NOT NULL,
            "active_workers" INT NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS "idx_queue_snapshots_timestamp" ON "queue_snapshots" ("timestamp");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Drop queue_snapshots table
        DROP TABLE IF EXISTS "queue_snapshots";
        
        -- Remove timing columns from worker_metrics
        ALTER TABLE "worker_metrics" DROP COLUMN IF EXISTS "total_processing_time_ms";
        ALTER TABLE "worker_metrics" DROP COLUMN IF EXISTS "total_queue_wait_time_ms";
    """
