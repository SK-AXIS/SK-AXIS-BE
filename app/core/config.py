from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, ClassVar
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    # 기본 설정
    API_V1_STR: str = "/v1"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    PROJECT_NAME: str = "SK AXIS"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    
    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:password@localhost:3306/sk_axis")
    
    # Redis 설정
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # OpenAI API 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
    
    # 미디어 저장 경로
    MEDIA_STORAGE_PATH: str = os.getenv("MEDIA_STORAGE_PATH", "./media_storage")
    
    # 면접 설정
    INTERVIEW_QUESTIONS_COUNT: int = 5
    
    # 평가 기준 설정
    EVALUATION_CRITERIA: ClassVar[Dict[str, List[str]]] = {
        "verbal": ["clarity", "relevance", "depth", "conciseness", "confidence"],
        "nonverbal": ["volume", "posture", "attire", "facial_expression", "eye_contact", "gestures"]
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 추가 입력 필드 무시

settings = Settings()
