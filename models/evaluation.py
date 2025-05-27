from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)
    competency = Column(Enum("Passionate", "Professional", "Proactive", "People", "Personal"), nullable=False)
    score_1 = Column(Integer)
    score_2 = Column(Integer)
    score_3 = Column(Integer)
    total_score = Column(Integer)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    answer = relationship("Answer", back_populates="evaluations")
