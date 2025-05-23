from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import redis
from datetime import datetime

from app.db.session import get_db, get_redis
from app.models.user import User
from app.models.interview import Interview as InterviewModel
from app.schemas.interview import (
    Interview, InterviewCreate, InterviewUpdate, 
    Answer, AnswerCreate, STTChunk, 
    GenerateQuestionsRequest, GenerateQuestionsResponse, Question
)
from app.services.interview import (
    get_interview, get_interviews, get_interviews_by_interviewer,
    create_interview, update_interview, delete_interview,
    start_interview, end_interview, create_answer, get_answers_by_interview,
    save_stt_chunk, get_stt_chunks, save_final_stt, generate_interview_questions
)

router = APIRouter()

@router.get("", response_model=List[Interview])
def read_interviews(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 목록 조회
    """
    if current_user.is_admin:
        interviews = get_interviews(db, skip=skip, limit=limit)
    else:
        interviews = get_interviews_by_interviewer(db, current_user.id, skip=skip, limit=limit)
    return interviews

@router.post("", response_model=Interview)
def create_interview_endpoint(
    interview_in: InterviewCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    새 면접 생성
    """
    interview = create_interview(db, interview_in, current_user.id)
    return interview

@router.get("/{interview_id}", response_model=Interview)
def read_interview(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 정보 조회
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    return interview

@router.put("/{interview_id}", response_model=Interview)
def update_interview_endpoint(
    interview_id: int,
    interview_in: InterviewUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 정보 업데이트
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    interview = update_interview(db, interview_id, interview_in)
    return interview

@router.delete("/{interview_id}", response_model=dict)
def delete_interview_endpoint(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 삭제
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    success = delete_interview(db, interview_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="면접 삭제 중 오류가 발생했습니다"
        )
    
    return {"msg": "면접이 삭제되었습니다"}

@router.post("/{interview_id}/start", response_model=Interview)
def start_interview_endpoint(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 시작
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    if interview.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 시작되었거나 완료된 면접입니다"
        )
    
    interview = start_interview(db, interview_id)
    return interview

@router.post("/{interview_id}/end", response_model=Interview)
def end_interview_endpoint(
    interview_id: int,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Any:
    """
    면접 종료
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    if interview.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="진행 중인 면접이 아닙니다"
        )
    
    # 최종 STT 저장
    save_final_stt(db, redis_client, interview_id)
    
    interview = end_interview(db, interview_id)
    return interview

@router.post("/{interview_id}/answers", response_model=Answer)
def create_answer_endpoint(
    interview_id: int,
    answer_in: AnswerCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 답변 생성
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    answer = create_answer(db, answer_in)
    return answer

@router.get("/{interview_id}/answers", response_model=List[Answer])
def read_answers(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 답변 목록 조회
    """
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not current_user.is_admin and interview.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    answers = get_answers_by_interview(db, interview_id)
    return answers

@router.post("/{interview_id}/stt", response_model=dict)
def save_stt_chunk_endpoint(
    interview_id: int,
    chunk: STTChunk,
    redis_client: redis.Redis = Depends(get_redis)
) -> Any:
    """
    STT 청크 저장
    """
    success = save_stt_chunk(redis_client, chunk)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STT 청크 저장 중 오류가 발생했습니다"
        )
    
    return {"msg": "STT 청크가 저장되었습니다"}

@router.get("/{interview_id}/stt/{question_index}", response_model=List[STTChunk])
def get_stt_chunks_endpoint(
    interview_id: int,
    question_index: int,
    redis_client: redis.Redis = Depends(get_redis)
) -> Any:
    """
    STT 청크 목록 조회
    """
    chunks = get_stt_chunks(redis_client, interview_id, question_index)
    return chunks

@router.post("/generate-questions", response_model=GenerateQuestionsResponse)
def generate_questions_endpoint(
    request: GenerateQuestionsRequest
) -> Any:
    """
    자기소개서 기반 면접 질문 생성
    """
    questions_data = generate_interview_questions(request.resume, request.count)
    
    # Question 객체 리스트로 변환
    questions = [
        Question(index=q["index"], content=q["content"])
        for q in questions_data
    ]
    
    return GenerateQuestionsResponse(questions=questions)
