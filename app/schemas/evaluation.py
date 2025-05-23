from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 평가 기준 점수 기본 스키마
class CriteriaScoreBase(BaseModel):
    category: str  # verbal 또는 nonverbal
    criteria: str  # 평가 기준 (예: clarity, volume 등)
    score: float = Field(..., ge=1, le=5)  # 점수 (1-5)
    comment: Optional[str] = None

# 평가 기준 점수 생성 스키마
class CriteriaScoreCreate(CriteriaScoreBase):
    evaluation_id: int

# 평가 기준 점수 응답 스키마
class CriteriaScore(CriteriaScoreBase):
    id: int
    evaluation_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 평가 기본 스키마
class EvaluationBase(BaseModel):
    interview_id: int
    total_score: Optional[float] = None
    verbal_score: Optional[float] = None
    nonverbal_score: Optional[float] = None
    detailed_scores: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None

# 평가 생성 스키마
class EvaluationCreate(EvaluationBase):
    pass

# 평가 업데이트 스키마
class EvaluationUpdate(BaseModel):
    total_score: Optional[float] = None
    verbal_score: Optional[float] = None
    nonverbal_score: Optional[float] = None
    detailed_scores: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    pdf_report_path: Optional[str] = None

# 평가 응답 스키마
class Evaluation(EvaluationBase):
    id: int
    pdf_report_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    criteria_scores: Optional[List[CriteriaScore]] = None

    class Config:
        orm_mode = True

# 평가 요청 스키마
class EvaluateInterviewRequest(BaseModel):
    interview_id: int

# 평가 결과 스키마
class EvaluationResult(BaseModel):
    evaluation_id: int
    candidate_name: str
    total_score: float
    verbal_score: float
    nonverbal_score: float
    detailed_scores: Dict[str, Any]
    feedback: str
    pdf_url: Optional[str] = None
