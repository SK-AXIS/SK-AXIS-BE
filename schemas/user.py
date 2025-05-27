from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    role: str  # '면접관', '지원자', '인사담당자'

class UserOut(BaseModel):
    id: int
    name: str
    role: str
    created_at: datetime

    class Config:
        orm_mode = True
