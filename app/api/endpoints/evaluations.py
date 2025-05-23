from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.evaluation import (
    Evaluation, EvaluationCreate, EvaluationUpdate, 
    CriteriaScore, CriteriaScoreCreate, 
    EvaluateInterviewRequest, EvaluationResult
)
from app.services.evaluation import (
    get_evaluation, get_evaluation_by_interview, 
    create_evaluation, update_evaluation, 
    create_criteria_score, get_criteria_scores_by_evaluation,
    evaluate_interview, generate_evaluation_report
)
from app.services.interview import get_interview

router = APIRouter()

@router.post("", response_model=Evaluation)
def create_evaluation_endpoint(
    evaluation_in: EvaluationCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    새 평가 생성
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, evaluation_in.interview_id)
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
    
    # 이미 평가가 있는지 확인
    existing_evaluation = get_evaluation_by_interview(db, evaluation_in.interview_id)
    if existing_evaluation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 평가가 존재합니다"
        )
    
    evaluation = create_evaluation(db, evaluation_in)
    return evaluation

@router.get("/{evaluation_id}", response_model=Evaluation)
def read_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    평가 정보 조회
    """
    evaluation = get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="평가를 찾을 수 없습니다"
        )
    
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, evaluation.interview_id)
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
    
    return evaluation

@router.put("/{evaluation_id}", response_model=Evaluation)
def update_evaluation_endpoint(
    evaluation_id: int,
    evaluation_in: EvaluationUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """
    평가 정보 업데이트
    """
    evaluation = get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="평가를 찾을 수 없습니다"
        )
    
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, evaluation.interview_id)
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
    
    evaluation = update_evaluation(db, evaluation_id, evaluation_in)
    return evaluation

@router.post("/{evaluation_id}/criteria", response_model=CriteriaScore)
def create_criteria_score_endpoint(
    evaluation_id: int,
    criteria_score_in: CriteriaScoreCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    평가 기준 점수 생성
    """
    # 평가 정보 조회
    evaluation = get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="평가를 찾을 수 없습니다"
        )
    
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, evaluation.interview_id)
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
    
    criteria_score = create_criteria_score(db, criteria_score_in)
    return criteria_score

@router.get("/{evaluation_id}/criteria", response_model=List[CriteriaScore])
def read_criteria_scores(
    evaluation_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    평가 기준 점수 목록 조회
    """
    # 평가 정보 조회
    evaluation = get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="평가를 찾을 수 없습니다"
        )
    
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, evaluation.interview_id)
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
    
    criteria_scores = get_criteria_scores_by_evaluation(db, evaluation_id)
    return criteria_scores

@router.post("/evaluate-interview", response_model=EvaluationResult)
async def evaluate_interview_endpoint(
    request: EvaluateInterviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 평가 수행
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, request.interview_id)
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
    
    if interview.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="완료된 면접만 평가할 수 있습니다"
        )
    
    # 이미 평가가 있는지 확인
    existing_evaluation = get_evaluation_by_interview(db, request.interview_id)
    if existing_evaluation:
        # PDF 리포트 생성 (백그라운드 작업)
        if not existing_evaluation.pdf_report_path:
            background_tasks.add_task(generate_evaluation_report, db, existing_evaluation.id)
        
        # 평가 결과 반환
        return EvaluationResult(
            evaluation_id=existing_evaluation.id,
            candidate_name=interview.candidate_name,
            total_score=existing_evaluation.total_score,
            verbal_score=existing_evaluation.verbal_score,
            nonverbal_score=existing_evaluation.nonverbal_score,
            detailed_scores=existing_evaluation.detailed_scores,
            feedback=existing_evaluation.feedback,
            pdf_url=f"/media/{existing_evaluation.pdf_report_path}" if existing_evaluation.pdf_report_path else None
        )
    
    # 면접 평가 수행
    evaluation = evaluate_interview(db, request.interview_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="면접 평가 중 오류가 발생했습니다"
        )
    
    # PDF 리포트 생성 (백그라운드 작업)
    background_tasks.add_task(generate_evaluation_report, db, evaluation.id)
    
    # 평가 결과 반환
    return EvaluationResult(
        evaluation_id=evaluation.id,
        candidate_name=interview.candidate_name,
        total_score=evaluation.total_score,
        verbal_score=evaluation.verbal_score,
        nonverbal_score=evaluation.nonverbal_score,
        detailed_scores=evaluation.detailed_scores,
        feedback=evaluation.feedback,
        pdf_url=f"/media/{evaluation.pdf_report_path}" if evaluation.pdf_report_path else None
    )
