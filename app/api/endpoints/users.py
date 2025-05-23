from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.services.user import get_user, get_users, create_user, update_user, delete_user

router = APIRouter()

@router.get("/me/{user_id}", response_model=UserSchema)
def read_user_me(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 정보 조회
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    return user

@router.put("/me/{user_id}", response_model=UserSchema)
def update_user_me(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 정보 업데이트
    """
    user = update_user(db, user_id, user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    return user

@router.get("", response_model=List[UserSchema])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 목록 조회
    """
    users = get_users(db, skip=skip, limit=limit)
    return users

@router.post("", response_model=UserSchema)
def create_user_endpoint(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    새 사용자 생성
    """
    user = create_user(db, user_in)
    return user

@router.get("/{user_id}", response_model=UserSchema)
def read_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 정보 조회
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    return user

@router.put("/{user_id}", response_model=UserSchema)
def update_user_endpoint(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 정보 업데이트
    """
    user = update_user(db, user_id, user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    return user

@router.delete("/{user_id}", response_model=dict)
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 삭제
    """
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    return {"msg": "사용자가 삭제되었습니다"}
