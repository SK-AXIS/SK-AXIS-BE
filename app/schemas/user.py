from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# 공통 속성
class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False

# 사용자 생성 요청
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# 사용자 업데이트 요청
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

# 데이터베이스에서 반환된 사용자 정보
class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 인증 관련 클래스 필요 X
