from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String(255), nullable=False)
    candidate_resume = Column(Text, nullable=True)
    interviewer_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    video_path = Column(String(255), nullable=True)
    audio_path = Column(String(255), nullable=True)
    stt_path = Column(String(255), nullable=True)
    questions = Column(JSON, nullable=True)  # JSON 형식으로 질문 저장
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 정의
    interviewer = relationship("User", back_populates="interviews")
    evaluations = relationship("Evaluation", back_populates="interview", cascade="all, delete-orphan")
    answers = relationship("Answer", back_populates="interview", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Interview {self.id} - {self.candidate_name}>"


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    question_index = Column(Integer, nullable=False)  # 질문 인덱스 (0-4)
    content = Column(Text, nullable=False)  # 답변 내용
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 정의
    interview = relationship("Interview", back_populates="answers")

    def __repr__(self):
        return f"<Answer {self.id} - Interview {self.interview_id} - Q{self.question_index}>"
