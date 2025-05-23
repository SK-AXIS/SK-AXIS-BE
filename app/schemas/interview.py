from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 질문 스키마
class Question(BaseModel):
    index: int
    content: str

# 답변 기본 스키마
class AnswerBase(BaseModel):
    question_index: int
    content: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

# 답변 생성 스키마
class AnswerCreate(AnswerBase):
    interview_id: int

# 답변 응답 스키마
class Answer(AnswerBase):
    id: int
    interview_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 면접 기본 스키마
class InterviewBase(BaseModel):
    candidate_name: str
    candidate_resume: Optional[str] = None

# 면접 생성 스키마
class InterviewCreate(InterviewBase):
    pass

# 면접 업데이트 스키마
class InterviewUpdate(BaseModel):
    candidate_name: Optional[str] = None
    candidate_resume: Optional[str] = None
    status: Optional[str] = None
    end_time: Optional[datetime] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    stt_path: Optional[str] = None

# 면접 응답 스키마
class Interview(InterviewBase):
    id: int
    interviewer_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    stt_path: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    answers: Optional[List[Answer]] = None

    class Config:
        orm_mode = True

# STT 청크 스키마
class STTChunk(BaseModel):
    interview_id: int
    question_index: int
    content: str
    timestamp: float

# 면접 질문 생성 요청 스키마
class GenerateQuestionsRequest(BaseModel):
    candidate_name: str
    resume: str
    count: int = Field(5, ge=1, le=10)

# 면접 질문 생성 응답 스키마
class GenerateQuestionsResponse(BaseModel):
    questions: List[Question]
