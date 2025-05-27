from pydantic import BaseModel
from datetime import datetime

class EvaluationCreate(BaseModel):
    answer_id: int
    competency: str  # 역량 이름
    score_1: int
    score_2: int
    score_3: int
    total_score: int

class EvaluationOut(BaseModel):
    id: int
    answer_id: int
    competency: str
    score_1: int
    score_2: int
    score_3: int
    total_score: int
    evaluated_at: datetime

    class Config:
        orm_mode = True
