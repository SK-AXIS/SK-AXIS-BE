import os
import logging
import ffmpeg
import tempfile
import base64
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import aiofiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.interview import Interview
from app.services.interview import get_interview, update_interview

logger = logging.getLogger(__name__)

async def save_video_chunk(interview_id: int, chunk_data: bytes, chunk_index: int) -> Optional[str]:
    """
    비디오 청크 저장
    """
    try:
        # 디렉토리 생성
        video_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "videos", f"interview_{interview_id}")
        os.makedirs(video_dir, exist_ok=True)
        
        # 청크 파일 경로
        chunk_path = os.path.join(video_dir, f"chunk_{chunk_index}.webm")
        
        # 청크 저장
        async with aiofiles.open(chunk_path, "wb") as f:
            await f.write(chunk_data)
        
        return chunk_path
    except Exception as e:
        logger.error(f"비디오 청크 저장 실패: {e}")
        return None

async def save_audio_chunk(interview_id: int, chunk_data: bytes, chunk_index: int) -> Optional[str]:
    """
    오디오 청크 저장
    """
    try:
        # 디렉토리 생성
        audio_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "audios", f"interview_{interview_id}")
        os.makedirs(audio_dir, exist_ok=True)
        
        # 청크 파일 경로
        chunk_path = os.path.join(audio_dir, f"chunk_{chunk_index}.webm")
        
        # 청크 저장
        async with aiofiles.open(chunk_path, "wb") as f:
            await f.write(chunk_data)
        
        return chunk_path
    except Exception as e:
        logger.error(f"오디오 청크 저장 실패: {e}")
        return None

def merge_video_chunks(db: Session, interview_id: int) -> Optional[str]:
    """
    비디오 청크 병합
    """
    try:
        # 면접 정보 조회
        interview = get_interview(db, interview_id)
        if not interview:
            logger.error(f"면접 ID {interview_id}에 대한 비디오 병합 실패: 면접이 존재하지 않습니다.")
            return None
        
        # 청크 디렉토리
        video_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "videos", f"interview_{interview_id}")
        if not os.path.exists(video_dir):
            logger.error(f"면접 ID {interview_id}에 대한 비디오 청크가 존재하지 않습니다.")
            return None
        
        # 청크 파일 목록
        chunk_files = [f for f in os.listdir(video_dir) if f.startswith("chunk_") and f.endswith(".webm")]
        chunk_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))
        
        if not chunk_files:
            logger.error(f"면접 ID {interview_id}에 대한 비디오 청크가 존재하지 않습니다.")
            return None
        
        # 청크 목록 파일 생성
        concat_file_path = os.path.join(video_dir, "concat_list.txt")
        with open(concat_file_path, "w") as f:
            for chunk_file in chunk_files:
                f.write(f"file '{os.path.join(video_dir, chunk_file)}'\n")
        
        # 출력 파일 경로
        output_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "videos")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"interview_{interview_id}.mp4")
        
        # FFmpeg로 비디오 병합
        (
            ffmpeg
            .input(concat_file_path, format="concat", safe=0)
            .output(output_path, c="copy")
            .run(quiet=True, overwrite_output=True)
        )
        
        # 면접 정보 업데이트
        relative_path = f"videos/interview_{interview_id}.mp4"
        update_interview(db, interview_id, {"video_path": relative_path})
        
        return relative_path
    except Exception as e:
        logger.error(f"비디오 청크 병합 실패: {e}")
        return None

def merge_audio_chunks(db: Session, interview_id: int) -> Optional[str]:
    """
    오디오 청크 병합
    """
    try:
        # 면접 정보 조회
        interview = get_interview(db, interview_id)
        if not interview:
            logger.error(f"면접 ID {interview_id}에 대한 오디오 병합 실패: 면접이 존재하지 않습니다.")
            return None
        
        # 청크 디렉토리
        audio_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "audios", f"interview_{interview_id}")
        if not os.path.exists(audio_dir):
            logger.error(f"면접 ID {interview_id}에 대한 오디오 청크가 존재하지 않습니다.")
            return None
        
        # 청크 파일 목록
        chunk_files = [f for f in os.listdir(audio_dir) if f.startswith("chunk_") and f.endswith(".webm")]
        chunk_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))
        
        if not chunk_files:
            logger.error(f"면접 ID {interview_id}에 대한 오디오 청크가 존재하지 않습니다.")
            return None
        
        # 청크 목록 파일 생성
        concat_file_path = os.path.join(audio_dir, "concat_list.txt")
        with open(concat_file_path, "w") as f:
            for chunk_file in chunk_files:
                f.write(f"file '{os.path.join(audio_dir, chunk_file)}'\n")
        
        # 출력 파일 경로
        output_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "audios")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"interview_{interview_id}.mp3")
        
        # FFmpeg로 오디오 병합
        (
            ffmpeg
            .input(concat_file_path, format="concat", safe=0)
            .output(output_path, acodec="libmp3lame", ab="128k")
            .run(quiet=True, overwrite_output=True)
        )
        
        # 면접 정보 업데이트
        relative_path = f"audios/interview_{interview_id}.mp3"
        update_interview(db, interview_id, {"audio_path": relative_path})
        
        return relative_path
    except Exception as e:
        logger.error(f"오디오 청크 병합 실패: {e}")
        return None

def extract_audio_from_video(video_path: str) -> Optional[str]:
    """
    비디오에서 오디오 추출
    """
    try:
        # 출력 파일 경로
        output_path = os.path.splitext(video_path)[0] + ".mp3"
        
        # FFmpeg로 오디오 추출
        (
            ffmpeg
            .input(video_path)
            .output(output_path, acodec="libmp3lame", ab="128k")
            .run(quiet=True, overwrite_output=True)
        )
        
        return output_path
    except Exception as e:
        logger.error(f"비디오에서 오디오 추출 실패: {e}")
        return None

def decode_base64_video(base64_data: str) -> Optional[bytes]:
    """
    Base64 인코딩된 비디오 데이터 디코딩
    """
    try:
        # Base64 데이터에서 헤더 제거
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        # Base64 디코딩
        video_data = base64.b64decode(base64_data)
        
        return video_data
    except Exception as e:
        logger.error(f"Base64 비디오 디코딩 실패: {e}")
        return None

def process_video_frame(frame_data: bytes) -> Dict[str, Any]:
    """
    비디오 프레임 처리 (Computer Vision 분석)
    """
    try:
        # 실제 구현에서는 mediapipe 또는 openCV를 사용한 분석 수행
        # 현재는 가상 데이터 반환
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(frame_data)
            temp_file_path = temp_file.name
        
        # 여기서 실제 Computer Vision 분석 수행
        # 예: face_landmarks = analyze_face(temp_file_path)
        
        # 임시 파일 삭제
        os.unlink(temp_file_path)
        
        # 가상 분석 결과 반환
        return {
            "face_detected": True,
            "emotion": "neutral",
            "eye_contact": True,
            "posture": "good",
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        logger.error(f"비디오 프레임 처리 실패: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().timestamp()
        }
