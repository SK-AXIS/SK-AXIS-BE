from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.services.evaluation import generate_excel_report
from app.core.config import settings

router = APIRouter()

@router.get("/dashboard", response_model=dict)
def get_dashboard_stats(
    db: Session = Depends(get_db)
) -> Any:
    """
    관리자 대시보드 통계 조회
    """
    # 면접 통계
    total_interviews = db.execute("SELECT COUNT(*) FROM interviews").scalar()
    completed_interviews = db.execute("SELECT COUNT(*) FROM interviews WHERE status = 'completed'").scalar()
    in_progress_interviews = db.execute("SELECT COUNT(*) FROM interviews WHERE status = 'in_progress'").scalar()
    scheduled_interviews = db.execute("SELECT COUNT(*) FROM interviews WHERE status = 'scheduled'").scalar()
    
    # 평가 통계
    total_evaluations = db.execute("SELECT COUNT(*) FROM evaluations").scalar()
    avg_score = db.execute("SELECT AVG(total_score) FROM evaluations").scalar() or 0
    
    # 최근 면접 목록
    recent_interviews = db.execute("""
        SELECT i.id, i.candidate_name, i.start_time, i.status, u.username as interviewer_name
        FROM interviews i
        JOIN users u ON i.interviewer_id = u.id
        ORDER BY i.start_time DESC
        LIMIT 5
    """).fetchall()
    
    recent_interviews_list = [
        {
            "id": row[0],
            "candidate_name": row[1],
            "start_time": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else None,
            "status": row[3],
            "interviewer_name": row[4]
        }
        for row in recent_interviews
    ]
    
    return {
        "interview_stats": {
            "total": total_interviews,
            "completed": completed_interviews,
            "in_progress": in_progress_interviews,
            "scheduled": scheduled_interviews
        },
        "evaluation_stats": {
            "total": total_evaluations,
            "avg_score": round(avg_score, 2)
        },
        "recent_interviews": recent_interviews_list
    }

@router.post("/export-excel-report", response_model=dict)
def export_excel_report_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 평가 결과 Excel 리포트 생성
    """
    # 백그라운드 작업으로 Excel 리포트 생성
    excel_path = generate_excel_report(db)
    
    if not excel_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Excel 리포트 생성 중 오류가 발생했습니다"
        )
    
    return {
        "msg": "Excel 리포트가 생성되었습니다",
        "excel_url": f"/media/{excel_path}"
    }

@router.get("/download-excel-report/{filename}", response_class=FileResponse)
def download_excel_report(
    filename: str
) -> Any:
    """
    Excel 리포트 다운로드
    """
    excel_path = os.path.join(settings.MEDIA_STORAGE_PATH, "reports", filename)
    
    if not os.path.exists(excel_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Excel 파일을 찾을 수 없습니다"
        )
    
    return FileResponse(
        excel_path,
        filename=f"interview_evaluations_{datetime.now().strftime('%Y%m%d')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.post("/init-database", response_model=dict)
def init_database() -> Any:
    """
    데이터베이스 초기화 (관리자 전용)
    """
    from app.db.init_db import init_db
    
    try:
        init_db()
        return {"msg": "데이터베이스가 초기화되었습니다"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 초기화 중 오류가 발생했습니다: {str(e)}"
        )
