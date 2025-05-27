from pydantic import BaseModel

class HRKeyword(BaseModel):
    term: str
    description: str