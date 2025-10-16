from typing import List

class SuggestorBase:
    async def generate(self, description: str, count: int) -> List[str]:
        raise NotImplementedError