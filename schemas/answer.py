from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AnswerCreate(BaseModel):
    interview_id: int
    speaker_role: str  # '면접관', '지원자'
    audio_path: Optional[str] = None
    stt_text: Optional[str] = None
    rewritten_text: Optional[str] = None

class AnswerOut(BaseModel):
    id: int
    interview_id: int
    speaker_role: str
    audio_path: Optional[str]
    stt_text: Optional[str]
    rewritten_text: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
