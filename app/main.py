from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.api import api_router
from app.core.config import settings

app = FastAPI(
    title="SK AXIS API",
    description="SK AX AI 면접 도우미 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix="")

# 미디어 파일 저장 디렉토리 설정
os.makedirs(settings.MEDIA_STORAGE_PATH, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_STORAGE_PATH), name="media")

@app.get("/")
async def root():
    return {"message": "SK AXIS API 서버에 오신 것을 환영합니다!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
