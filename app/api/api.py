from fastapi import APIRouter

from app.api.endpoints import users, interviews, evaluations, media, admin

api_router = APIRouter()

# 사용자 관련 엔드포인트
api_router.include_router(users.router, prefix="/api/v1/users", tags=["사용자"])

# 면접 관련 엔드포인트
api_router.include_router(interviews.router, prefix="/api/v1/interviews", tags=["면접"])

# 평가 관련 엔드포인트
api_router.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["평가"])

# 미디어 관련 엔드포인트
api_router.include_router(media.router, prefix="/api/v1/media", tags=["미디어"])

# 관리자 관련 엔드포인트
api_router.include_router(admin.router, prefix="/api/v1/admin", tags=["관리자"])
