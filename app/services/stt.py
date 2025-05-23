import os
import logging
import tempfile
import json
from typing import Optional, List, Dict, Any
from google.cloud import speech
import openai
import redis

from app.core.config import settings
from app.schemas.interview import STTChunk

logger = logging.getLogger(__name__)

def transcribe_audio_google(audio_path: str, language_code: str = "ko-KR") -> Optional[str]:
    """
    Google Cloud Speech API를 사용한 오디오 파일 STT 변환
    """
    try:
        # Google Cloud Speech 클라이언트 초기화
        client = speech.SpeechClient()
        
        # 오디오 파일 읽기
        with open(audio_path, "rb") as audio_file:
            content = audio_file.read()
        
        # 오디오 설정
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=16000,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )
        
        # STT 요청
        response = client.recognize(config=config, audio=audio)
        
        # 결과 처리
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        
        return transcript.strip()
    except Exception as e:
        logger.error(f"Google STT 변환 실패: {e}")
        return None

def transcribe_audio_whisper(audio_path: str, language: str = "ko") -> Optional[str]:
    """
    OpenAI Whisper API를 사용한 오디오 파일 STT 변환
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY
        
        with open(audio_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language=language
            )
        
        return response.get("text", "")
    except Exception as e:
        logger.error(f"Whisper STT 변환 실패: {e}")
        return None

def transcribe_audio_chunk(audio_chunk: bytes, language: str = "ko") -> Optional[str]:
    """
    오디오 청크 STT 변환 (Whisper API 사용)
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file.write(audio_chunk)
            temp_file_path = temp_file.name
        
        # STT 변환
        with open(temp_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language=language
            )
        
        # 임시 파일 삭제
        os.unlink(temp_file_path)
        
        return response.get("text", "")
    except Exception as e:
        logger.error(f"오디오 청크 STT 변환 실패: {e}")
        return None

def save_stt_chunk_to_redis(redis_client: redis.Redis, chunk: STTChunk) -> bool:
    """
    STT 청크를 Redis에 저장
    """
    try:
        # Redis 키 형식: stt:{interview_id}:{question_index}:{timestamp}
        key = f"stt:{chunk.interview_id}:{chunk.question_index}:{chunk.timestamp}"
        redis_client.set(key, chunk.content, ex=86400)  # 24시간 유효
        
        # 해당 질문에 대한 모든 청크 키를 저장하는 세트
        set_key = f"stt_chunks:{chunk.interview_id}:{chunk.question_index}"
        redis_client.sadd(set_key, key)
        redis_client.expire(set_key, 86400)  # 24시간 유효
        
        return True
    except Exception as e:
        logger.error(f"STT 청크 Redis 저장 실패: {e}")
        return False

def get_stt_chunks_from_redis(redis_client: redis.Redis, interview_id: int, question_index: int) -> List[Dict[str, Any]]:
    """
    Redis에서 STT 청크 목록 조회
    """
    try:
        # 해당 질문에 대한 모든 청크 키를 가져옴
        set_key = f"stt_chunks:{interview_id}:{question_index}"
        chunk_keys = redis_client.smembers(set_key)
        
        chunks = []
        for key in chunk_keys:
            content = redis_client.get(key)
            if content:
                # 키에서 타임스탬프 추출
                timestamp = float(key.decode().split(":")[-1])
                chunks.append({
                    "timestamp": timestamp,
                    "content": content.decode()
                })
        
        # 타임스탬프 기준 정렬
        chunks.sort(key=lambda x: x["timestamp"])
        return chunks
    except Exception as e:
        logger.error(f"STT 청크 Redis 조회 실패: {e}")
        return []

def save_final_stt_to_file(interview_id: int, stt_data: Dict[int, str]) -> Optional[str]:
    """
    최종 STT 데이터를 파일로 저장
    """
    try:
        # 디렉토리 생성
        stt_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "stt")
        os.makedirs(stt_dir, exist_ok=True)
        
        # 파일 경로
        stt_path = os.path.join(stt_dir, f"interview_{interview_id}_stt.json")
        
        # JSON 파일로 저장
        with open(stt_path, "w", encoding="utf-8") as f:
            json.dump(stt_data, f, ensure_ascii=False, indent=2)
        
        return f"stt/interview_{interview_id}_stt.json"
    except Exception as e:
        logger.error(f"최종 STT 파일 저장 실패: {e}")
        return None
