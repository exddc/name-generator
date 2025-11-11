from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "suggestions" 
        SET "model" = 'qwen/qwen3-32b' 
        WHERE "model" = 'variants-check';
        
        UPDATE "suggestions" 
        SET "prompt" = 'legacy' 
        WHERE "prompt" = 'variants-check';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Note: This downgrade is approximate as we cannot perfectly identify
        -- which records were originally variants-check vs regular suggestions
        -- with the same model/prompt values
        UPDATE "suggestions" 
        SET "model" = 'variants-check', "prompt" = 'variants-check'
        WHERE "model" = 'qwen/qwen3-32b' AND "prompt" = 'legacy'
        AND "description" LIKE 'Variants for %';
    """

