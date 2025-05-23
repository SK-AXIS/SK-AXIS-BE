from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import base64
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.services.media import (
    save_video_chunk, save_audio_chunk, 
    merge_video_chunks, merge_audio_chunks,
    extract_audio_from_video, decode_base64_video, process_video_frame
)
from app.services.stt import transcribe_audio_chunk
from app.services.interview import get_interview, save_stt_chunk
from app.schemas.interview import STTChunk
from app.core.config import settings

router = APIRouter()

@router.post("/upload-video-chunk", response_model=dict)
async def upload_video_chunk(
    interview_id: int = Form(...),
    chunk_index: int = Form(...),
    chunk_data: UploadFile = File(...)
) -> Any:
    """
    비디오 청크 업로드
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(get_db(), interview_id)
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
    
    # 청크 데이터 읽기
    chunk_bytes = await chunk_data.read()
    
    # 청크 저장
    chunk_path = await save_video_chunk(interview_id, chunk_bytes, chunk_index)
    if not chunk_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비디오 청크 저장 중 오류가 발생했습니다"
        )
    
    return {"msg": "비디오 청크가 저장되었습니다", "chunk_path": chunk_path}

@router.post("/upload-audio-chunk", response_model=dict)
async def upload_audio_chunk(
    interview_id: int = Form(...),
    question_index: int = Form(...),
    chunk_index: int = Form(...),
    chunk_data: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    오디오 청크 업로드 및 STT 처리
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    # 청크 데이터 읽기
    chunk_bytes = await chunk_data.read()
    
    # 청크 저장
    chunk_path = await save_audio_chunk(interview_id, chunk_bytes, chunk_index)
    if not chunk_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="오디오 청크 저장 중 오류가 발생했습니다"
        )
    
    # STT 처리
    transcript = transcribe_audio_chunk(chunk_bytes)
    
    # STT 결과가 있으면 Redis에 저장
    if transcript:
        stt_chunk = STTChunk(
            interview_id=interview_id,
            question_index=question_index,
            content=transcript,
            timestamp=datetime.now().timestamp()
        )
        save_stt_chunk(db, stt_chunk)
    
    return {
        "msg": "오디오 청크가 저장되었습니다", 
        "chunk_path": chunk_path,
        "transcript": transcript
    }

@router.post("/upload-base64-video", response_model=dict)
async def upload_base64_video(
    interview_id: int,
    base64_data: str
) -> Any:
    """
    Base64 인코딩된 비디오 업로드
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(get_db(), interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    # Base64 디코딩
    video_data = decode_base64_video(base64_data)
    if not video_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 Base64 데이터입니다"
        )
    
    # 비디오 저장
    video_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "videos")
    os.makedirs(video_dir, exist_ok=True)
    video_path = os.path.join(video_dir, f"interview_{interview_id}_snapshot.webm")
    
    with open(video_path, "wb") as f:
        f.write(video_data)
    
    return {"msg": "비디오가 저장되었습니다", "video_path": video_path}

@router.post("/process-video-frame", response_model=dict)
async def process_video_frame_endpoint(
    interview_id: int,
    base64_data: str
) -> Any:
    """
    비디오 프레임 처리 (Computer Vision 분석)
    """
    # Base64 디코딩
    frame_data = base64.b64decode(base64_data.split(",")[1] if "," in base64_data else base64_data)
    
    # 프레임 처리
    result = process_video_frame(frame_data)
    
    return result

@router.post("/{interview_id}/merge-video", response_model=dict)
def merge_video_chunks_endpoint(
    interview_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    비디오 청크 병합
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    # 백그라운드 작업으로 비디오 병합
    background_tasks.add_task(merge_video_chunks, db, interview_id)
    
    return {"msg": "비디오 병합이 시작되었습니다"}

@router.post("/{interview_id}/merge-audio", response_model=dict)
def merge_audio_chunks_endpoint(
    interview_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    오디오 청크 병합
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    # 백그라운드 작업으로 오디오 병합
    background_tasks.add_task(merge_audio_chunks, db, interview_id)
    
    return {"msg": "오디오 병합이 시작되었습니다"}

@router.get("/{interview_id}/video", response_class=FileResponse)
def get_interview_video(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 비디오 조회
    """
    # 면접 정보 조회 및 권한 확인
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="면접을 찾을 수 없습니다"
        )
    
    if not interview.video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비디오가 없습니다"
        )
    
    video_path = os.path.join(settings.MEDIA_STORAGE_PATH, interview.video_path)
    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비디오 파일을 찾을 수 없습니다"
        )
    
    return FileResponse(video_path)

@router.get("/{interview_id}/audio", response_class=FileResponse)
def get_interview_audio(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    면접 오디오 조회
    """
    # 면접 정보 조회 및 권한 확인
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
    
    if not interview.audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="오디오가 없습니다"
        )
    
    audio_path = os.path.join(settings.MEDIA_STORAGE_PATH, interview.audio_path)
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="오디오 파일을 찾을 수 없습니다"
        )
    
    return FileResponse(audio_path)
