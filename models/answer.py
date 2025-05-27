from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    speaker_role = Column(Enum("면접관", "지원자"), nullable=False)
    audio_path = Column(Text)
    stt_text = Column(Text)
    rewritten_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="answers")
    evaluations = relationship("Evaluation", back_populates="answer")
