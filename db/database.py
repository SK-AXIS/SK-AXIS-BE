from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드

DATABASE_URL = os.getenv("DATABASE_URL")  # .env에서 URL 불러옴

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)

# 세션 클래스 정의
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 모델이 이걸 상속)
Base = declarative_base()
