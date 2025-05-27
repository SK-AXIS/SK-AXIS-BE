from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base  # SQLAlchemy Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    role = Column(Enum("면접관", "지원자", "인사담당자"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    interviews = relationship("Interview", back_populates="user")