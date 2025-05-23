from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    total_score = Column(Float, nullable=True)  # 총점 (100점 만점)
    verbal_score = Column(Float, nullable=True)  # 언어적 평가 점수
    nonverbal_score = Column(Float, nullable=True)  # 비언어적 평가 점수
    detailed_scores = Column(JSON, nullable=True)  # 세부 평가 항목별 점수 (JSON)
    feedback = Column(Text, nullable=True)  # 종합 피드백
    pdf_report_path = Column(String(255), nullable=True)  # PDF 리포트 경로
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 정의
    interview = relationship("Interview", back_populates="evaluations")
    criteria_scores = relationship("CriteriaScore", back_populates="evaluation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Evaluation {self.id} - Interview {self.interview_id}>"


class CriteriaScore(Base):
    __tablename__ = "criteria_scores"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    category = Column(String(50), nullable=False)  # verbal 또는 nonverbal
    criteria = Column(String(50), nullable=False)  # 평가 기준 (예: clarity, volume 등)
    score = Column(Float, nullable=False)  # 점수 (1-5)
    comment = Column(Text, nullable=True)  # 해당 기준에 대한 코멘트
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 정의
    evaluation = relationship("Evaluation", back_populates="criteria_scores")

    def __repr__(self):
        return f"<CriteriaScore {self.id} - {self.category}.{self.criteria}>"
