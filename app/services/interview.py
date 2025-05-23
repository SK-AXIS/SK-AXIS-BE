from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import redis
import json
import os
from datetime import datetime
import openai
import logging

from app.models.interview import Interview, Answer
from app.schemas.interview import InterviewCreate, InterviewUpdate, AnswerCreate, STTChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_interview(db: Session, interview_id: int) -> Optional[Interview]:
    """
    ID로 면접 조회
    """
    return db.query(Interview).filter(Interview.id == interview_id).first()

def get_interviews(db: Session, skip: int = 0, limit: int = 100):
    """
    면접 목록 조회
    """
    return db.query(Interview).offset(skip).limit(limit).all()

def get_interviews_by_interviewer(db: Session, interviewer_id: int, skip: int = 0, limit: int = 100):
    """
    면접관 ID로 면접 목록 조회
    """
    return db.query(Interview).filter(Interview.interviewer_id == interviewer_id).offset(skip).limit(limit).all()

def create_interview(db: Session, interview_in: InterviewCreate, interviewer_id: int) -> Interview:
    """
    새 면접 생성
    """
    db_interview = Interview(
        candidate_name=interview_in.candidate_name,
        candidate_resume=interview_in.candidate_resume,
        interviewer_id=interviewer_id,
        status="scheduled"
    )
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def update_interview(db: Session, interview_id: int, interview_in: InterviewUpdate) -> Optional[Interview]:
    """
    면접 정보 업데이트
    """
    db_interview = get_interview(db, interview_id)
    if not db_interview:
        return None
    
    update_data = interview_in.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_interview, field, value)
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def delete_interview(db: Session, interview_id: int) -> bool:
    """
    면접 삭제
    """
    db_interview = get_interview(db, interview_id)
    if not db_interview:
        return False
    
    db.delete(db_interview)
    db.commit()
    return True

def start_interview(db: Session, interview_id: int) -> Optional[Interview]:
    """
    면접 시작
    """
    db_interview = get_interview(db, interview_id)
    if not db_interview:
        return None
    
    db_interview.status = "in_progress"
    db_interview.start_time = datetime.now()
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def end_interview(db: Session, interview_id: int) -> Optional[Interview]:
    """
    면접 종료
    """
    db_interview = get_interview(db, interview_id)
    if not db_interview:
        return None
    
    db_interview.status = "completed"
    db_interview.end_time = datetime.now()
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def create_answer(db: Session, answer_in: AnswerCreate) -> Answer:
    """
    면접 답변 생성
    """
    db_answer = Answer(
        interview_id=answer_in.interview_id,
        question_index=answer_in.question_index,
        content=answer_in.content,
        start_time=answer_in.start_time,
        end_time=answer_in.end_time
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer

def get_answers_by_interview(db: Session, interview_id: int) -> List[Answer]:
    """
    면접 ID로 답변 목록 조회
    """
    return db.query(Answer).filter(Answer.interview_id == interview_id).all()

def save_stt_chunk(redis_client: redis.Redis, chunk: STTChunk) -> bool:
    """
    STT 청크 저장 (Redis)
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
        logger.error(f"STT 청크 저장 실패: {e}")
        return False

def get_stt_chunks(redis_client: redis.Redis, interview_id: int, question_index: int) -> List[Dict[str, Any]]:
    """
    면접 및 질문 인덱스로 STT 청크 목록 조회 (Redis)
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
        logger.error(f"STT 청크 조회 실패: {e}")
        return []

def save_final_stt(db: Session, redis_client: redis.Redis, interview_id: int) -> Optional[str]:
    """
    최종 STT 파일 저장
    """
    try:
        db_interview = get_interview(db, interview_id)
        if not db_interview:
            return None
        
        # 모든 질문에 대한 STT 청크 수집
        all_stt_content = {}
        for i in range(settings.INTERVIEW_QUESTIONS_COUNT):
            chunks = get_stt_chunks(redis_client, interview_id, i)
            if chunks:
                all_stt_content[i] = " ".join([chunk["content"] for chunk in chunks])
        
        # STT 파일 저장
        os.makedirs(os.path.join(settings.MEDIA_STORAGE_PATH, "stt"), exist_ok=True)
        stt_filename = f"interview_{interview_id}_stt.json"
        stt_path = os.path.join(settings.MEDIA_STORAGE_PATH, "stt", stt_filename)
        
        with open(stt_path, "w", encoding="utf-8") as f:
            json.dump(all_stt_content, f, ensure_ascii=False, indent=2)
        
        # 면접 정보 업데이트
        db_interview.stt_path = f"stt/{stt_filename}"
        db.add(db_interview)
        db.commit()
        
        return stt_path
    except Exception as e:
        logger.error(f"최종 STT 저장 실패: {e}")
        return None

def generate_interview_questions(resume: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    자기소개서 기반 면접 질문 생성 (OpenAI API 사용)
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY
        
        prompt = f"""
        다음은 지원자의 자기소개서입니다:
        
        {resume}
        
        위 자기소개서를 바탕으로 면접 질문 {count}개를 생성해주세요. 
        질문은 지원자의 경험, 역량, 성격, 가치관 등을 파악할 수 있는 내용이어야 합니다.
        각 질문은 간결하고 명확해야 하며, 지원자가 구체적인 사례나 경험을 이야기할 수 있도록 해야 합니다.
        JSON 형식으로 다음과 같이 응답해주세요:
        [
          {{"index": 0, "content": "질문 내용"}},
          {{"index": 1, "content": "질문 내용"}},
          ...
        ]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 전문 면접관입니다. 지원자의 자기소개서를 분석하여 적절한 면접 질문을 생성합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        # 응답에서 JSON 부분 추출
        content = response.choices[0].message.content
        # JSON 부분만 추출하는 로직 (실제로는 더 견고한 방식이 필요할 수 있음)
        json_str = content.strip()
        if not json_str.startswith("["):
            # JSON 시작 부분 찾기
            start_idx = json_str.find("[")
            if start_idx != -1:
                json_str = json_str[start_idx:]
            else:
                raise ValueError("응답에서 JSON 형식을 찾을 수 없습니다.")
        
        questions = json.loads(json_str)
        
        # 질문 개수 확인 및 조정
        if len(questions) > count:
            questions = questions[:count]
        
        return questions
    except Exception as e:
        logger.error(f"면접 질문 생성 실패: {e}")
        # 기본 질문 반환
        return [
            {"index": i, "content": f"기본 면접 질문 {i+1}입니다. 자신의 경험에 대해 이야기해주세요."} 
            for i in range(count)
        ]
