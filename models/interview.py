from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(String(255), nullable=False)
    competency = Column(Enum("Passionate", "Professional", "Proactive", "People", "Personal"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interviews")
    answers = relationship("Answer", back_populates="interview")
