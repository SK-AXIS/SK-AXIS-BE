from pydantic import BaseModel
from datetime import datetime

class InterviewCreate(BaseModel):
    user_id: int
    question: str
    competency: str  # 'Passionate', 'Professional', 'Proactive', 'People', 'Personal'

class InterviewOut(BaseModel):
    id: int
    user_id: int
    question: str
    competency: str
    created_at: datetime

    class Config:
        orm_mode = True
