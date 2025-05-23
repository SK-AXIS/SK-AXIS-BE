import uvicorn
import os
import logging
from app.utils.logging import setup_logging
from app.core.config import settings

if __name__ == "__main__":
    # 로깅 설정
    setup_logging()
    
    # 서버 실행
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=logging.INFO if settings.DEBUG else logging.WARNING
    )
