from pydantic import BaseModel


class SuggestRequest(BaseModel):
    query: str
