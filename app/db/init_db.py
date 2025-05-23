from sqlalchemy.orm import Session
from app.db.session import Base, engine
from app.models import user, interview, evaluation
import logging

logger = logging.getLogger(__name__)

def init_db() -> None:
    """
    데이터베이스 테이블 초기화 및 기본 데이터 생성
    """
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    logger.info("데이터베이스 테이블이 생성되었습니다.")

if __name__ == "__main__":
    logger.info("데이터베이스 초기화 중...")
    init_db()
    logger.info("데이터베이스 초기화 완료!")
