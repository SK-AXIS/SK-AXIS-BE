from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import os
import json
import logging
import openai
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import openpyxl

from app.models.evaluation import Evaluation, CriteriaScore
from app.models.interview import Interview, Answer
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate, CriteriaScoreCreate
from app.core.config import settings
from app.services.interview import get_interview, get_answers_by_interview

logger = logging.getLogger(__name__)

def get_evaluation(db: Session, evaluation_id: int) -> Optional[Evaluation]:
    """
    ID로 평가 조회
    """
    return db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()

def get_evaluation_by_interview(db: Session, interview_id: int) -> Optional[Evaluation]:
    """
    면접 ID로 평가 조회
    """
    return db.query(Evaluation).filter(Evaluation.interview_id == interview_id).first()

def create_evaluation(db: Session, evaluation_in: EvaluationCreate) -> Evaluation:
    """
    새 평가 생성
    """
    db_evaluation = Evaluation(
        interview_id=evaluation_in.interview_id,
        total_score=evaluation_in.total_score,
        verbal_score=evaluation_in.verbal_score,
        nonverbal_score=evaluation_in.nonverbal_score,
        detailed_scores=evaluation_in.detailed_scores,
        feedback=evaluation_in.feedback
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def update_evaluation(db: Session, evaluation_id: int, evaluation_in: EvaluationUpdate) -> Optional[Evaluation]:
    """
    평가 정보 업데이트
    """
    db_evaluation = get_evaluation(db, evaluation_id)
    if not db_evaluation:
        return None
    
    update_data = evaluation_in.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_evaluation, field, value)
    
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def create_criteria_score(db: Session, criteria_score_in: CriteriaScoreCreate) -> CriteriaScore:
    """
    평가 기준 점수 생성
    """
    db_criteria_score = CriteriaScore(
        evaluation_id=criteria_score_in.evaluation_id,
        category=criteria_score_in.category,
        criteria=criteria_score_in.criteria,
        score=criteria_score_in.score,
        comment=criteria_score_in.comment
    )
    db.add(db_criteria_score)
    db.commit()
    db.refresh(db_criteria_score)
    return db_criteria_score

def get_criteria_scores_by_evaluation(db: Session, evaluation_id: int) -> List[CriteriaScore]:
    """
    평가 ID로 평가 기준 점수 목록 조회
    """
    return db.query(CriteriaScore).filter(CriteriaScore.evaluation_id == evaluation_id).all()

def evaluate_interview(db: Session, interview_id: int) -> Optional[Evaluation]:
    """
    면접 평가 수행
    """
    try:
        # 면접 정보 조회
        interview = get_interview(db, interview_id)
        if not interview or interview.status != "completed":
            logger.error(f"면접 ID {interview_id}에 대한 평가 실패: 면접이 존재하지 않거나 완료되지 않았습니다.")
            return None
        
        # 이미 평가가 있는지 확인
        existing_evaluation = get_evaluation_by_interview(db, interview_id)
        if existing_evaluation:
            logger.info(f"면접 ID {interview_id}에 대한 평가가 이미 존재합니다.")
            return existing_evaluation
        
        # 답변 목록 조회
        answers = get_answers_by_interview(db, interview_id)
        
        # 언어적 평가 (OpenAI API 사용)
        verbal_scores, verbal_feedback = evaluate_verbal_aspects(interview, answers)
        
        # 비언어적 평가 (가상 데이터 - 실제로는 Computer Vision 분석 결과 사용)
        nonverbal_scores, nonverbal_feedback = evaluate_nonverbal_aspects(interview_id)
        
        # 종합 점수 계산
        detailed_scores = {
            "verbal": verbal_scores,
            "nonverbal": nonverbal_scores
        }
        
        verbal_avg = np.mean(list(verbal_scores.values()))
        nonverbal_avg = np.mean(list(nonverbal_scores.values()))
        
        # 총점 계산 (100점 만점, 언어적 60%, 비언어적 40%)
        total_score = (verbal_avg * 0.6 + nonverbal_avg * 0.4) * 20  # 5점 만점을 100점 만점으로 변환
        
        # 종합 피드백
        feedback = f"{verbal_feedback}\n\n{nonverbal_feedback}"
        
        # 평가 생성
        evaluation_data = EvaluationCreate(
            interview_id=interview_id,
            total_score=total_score,
            verbal_score=verbal_avg * 20,  # 5점 만점을 100점 만점으로 변환
            nonverbal_score=nonverbal_avg * 20,  # 5점 만점을 100점 만점으로 변환
            detailed_scores=detailed_scores,
            feedback=feedback
        )
        
        evaluation = create_evaluation(db, evaluation_data)
        
        # 평가 기준별 점수 저장
        for category, scores in detailed_scores.items():
            for criteria, score in scores.items():
                criteria_score_data = CriteriaScoreCreate(
                    evaluation_id=evaluation.id,
                    category=category,
                    criteria=criteria,
                    score=score,
                    comment=f"{criteria.capitalize()} 점수: {score}/5"
                )
                create_criteria_score(db, criteria_score_data)
        
        # PDF 리포트 생성
        pdf_path = generate_evaluation_report(db, evaluation.id)
        if pdf_path:
            # PDF 경로 업데이트
            evaluation_update = EvaluationUpdate(pdf_report_path=pdf_path)
            evaluation = update_evaluation(db, evaluation.id, evaluation_update)
        
        return evaluation
    except Exception as e:
        logger.error(f"면접 평가 실패: {e}")
        return None

def evaluate_verbal_aspects(interview: Interview, answers: List[Answer]) -> tuple:
    """
    언어적 측면 평가 (OpenAI API 사용)
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY
        
        # 답변 내용 정리
        answer_contents = {}
        for answer in answers:
            answer_contents[answer.question_index] = answer.content
        
        # 질문 목록
        questions = interview.questions if interview.questions else []
        
        # 평가 요청 프롬프트 작성
        prompt = f"""
        다음은 면접 질문과 지원자 {interview.candidate_name}의 답변입니다:
        
        """
        
        for q in questions:
            q_idx = q.get("index", 0)
            q_content = q.get("content", "")
            a_content = answer_contents.get(q_idx, "")
            prompt += f"질문 {q_idx+1}: {q_content}\n답변: {a_content}\n\n"
        
        prompt += f"""
        위 답변을 바탕으로 다음 기준에 따라 1-5점 척도로 평가해주세요:
        1. 명확성(clarity): 답변이 명확하고 이해하기 쉬운가?
        2. 관련성(relevance): 답변이 질문과 관련이 있는가?
        3. 깊이(depth): 답변이 충분한 깊이와 통찰력을 보여주는가?
        4. 간결성(conciseness): 답변이 간결하고 핵심을 잘 전달하는가?
        5. 자신감(confidence): 답변에서 자신감이 느껴지는가?
        
        JSON 형식으로 다음과 같이 응답해주세요:
        {{
          "clarity": 점수,
          "relevance": 점수,
          "depth": 점수,
          "conciseness": 점수,
          "confidence": 점수,
          "feedback": "종합적인 피드백"
        }}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 전문 면접 평가자입니다. 지원자의 답변을 객관적으로 평가합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        # 응답에서 JSON 부분 추출
        content = response.choices[0].message.content
        # JSON 부분만 추출하는 로직
        json_str = content.strip()
        if not json_str.startswith("{"):
            # JSON 시작 부분 찾기
            start_idx = json_str.find("{")
            if start_idx != -1:
                json_str = json_str[start_idx:]
                # JSON 끝 부분 찾기
                end_idx = json_str.rfind("}")
                if end_idx != -1:
                    json_str = json_str[:end_idx+1]
            else:
                raise ValueError("응답에서 JSON 형식을 찾을 수 없습니다.")
        
        result = json.loads(json_str)
        
        scores = {
            "clarity": result.get("clarity", 3),
            "relevance": result.get("relevance", 3),
            "depth": result.get("depth", 3),
            "conciseness": result.get("conciseness", 3),
            "confidence": result.get("confidence", 3)
        }
        
        feedback = result.get("feedback", "언어적 측면에 대한 평가 피드백이 없습니다.")
        
        return scores, feedback
    except Exception as e:
        logger.error(f"언어적 측면 평가 실패: {e}")
        # 기본 점수 및 피드백 반환
        default_scores = {
            "clarity": 3,
            "relevance": 3,
            "depth": 3,
            "conciseness": 3,
            "confidence": 3
        }
        default_feedback = "언어적 측면 평가 중 오류가 발생했습니다. 기본 점수가 적용됩니다."
        return default_scores, default_feedback

def evaluate_nonverbal_aspects(interview_id: int) -> tuple:
    """
    비언어적 측면 평가 (가상 데이터 - 실제로는 Computer Vision 분석 결과 사용)
    """
    try:
        # 실제 구현에서는 mediapipe 또는 openCV를 사용한 분석 결과를 사용
        # 현재는 가상 데이터 생성
        
        # 랜덤 점수 생성 (3~5점 사이)
        np.random.seed(interview_id)  # 동일한 면접 ID에 대해 일관된 결과 생성
        
        scores = {
            "volume": round(np.random.uniform(3, 5), 1),
            "posture": round(np.random.uniform(3, 5), 1),
            "attire": round(np.random.uniform(3, 5), 1),
            "facial_expression": round(np.random.uniform(3, 5), 1),
            "eye_contact": round(np.random.uniform(3, 5), 1),
            "gestures": round(np.random.uniform(3, 5), 1)
        }
        
        # 피드백 생성
        feedback_items = []
        
        if scores["volume"] < 4:
            feedback_items.append("성량이 다소 작습니다. 더 큰 목소리로 자신감 있게 말하는 것이 좋습니다.")
        else:
            feedback_items.append("적절한 성량으로 말하고 있습니다.")
            
        if scores["posture"] < 4:
            feedback_items.append("자세가 다소 불안정합니다. 더 바른 자세를 유지하는 것이 좋습니다.")
        else:
            feedback_items.append("바른 자세를 잘 유지하고 있습니다.")
            
        if scores["attire"] < 4:
            feedback_items.append("복장이 다소 격식에 맞지 않습니다. 면접에 적합한 복장을 갖추는 것이 좋습니다.")
        else:
            feedback_items.append("면접에 적합한 복장을 잘 갖추고 있습니다.")
            
        if scores["facial_expression"] < 4:
            feedback_items.append("표정이 다소 경직되어 있습니다. 더 자연스러운 표정을 유지하는 것이 좋습니다.")
        else:
            feedback_items.append("자연스럽고 적절한 표정을 잘 유지하고 있습니다.")
            
        if scores["eye_contact"] < 4:
            feedback_items.append("시선 처리가 다소 불안정합니다. 면접관과의 눈 맞춤을 더 자주 하는 것이 좋습니다.")
        else:
            feedback_items.append("면접관과의 눈 맞춤을 잘 유지하고 있습니다.")
            
        if scores["gestures"] < 4:
            feedback_items.append("제스처가 다소 부자연스럽습니다. 더 자연스러운 제스처를 사용하는 것이 좋습니다.")
        else:
            feedback_items.append("적절하고 자연스러운 제스처를 잘 사용하고 있습니다.")
        
        feedback = "비언어적 측면 평가:\n" + "\n".join(feedback_items)
        
        return scores, feedback
    except Exception as e:
        logger.error(f"비언어적 측면 평가 실패: {e}")
        # 기본 점수 및 피드백 반환
        default_scores = {
            "volume": 3,
            "posture": 3,
            "attire": 3,
            "facial_expression": 3,
            "eye_contact": 3,
            "gestures": 3
        }
        default_feedback = "비언어적 측면 평가 중 오류가 발생했습니다. 기본 점수가 적용됩니다."
        return default_scores, default_feedback

def generate_evaluation_report(db: Session, evaluation_id: int) -> Optional[str]:
    """
    평가 결과 PDF 리포트 생성
    """
    try:
        # 평가 정보 조회
        evaluation = get_evaluation(db, evaluation_id)
        if not evaluation:
            logger.error(f"평가 ID {evaluation_id}에 대한 리포트 생성 실패: 평가가 존재하지 않습니다.")
            return None
        
        # 면접 정보 조회
        interview = get_interview(db, evaluation.interview_id)
        if not interview:
            logger.error(f"면접 ID {evaluation.interview_id}에 대한 리포트 생성 실패: 면접이 존재하지 않습니다.")
            return None
        
        # 평가 기준 점수 목록 조회
        criteria_scores = get_criteria_scores_by_evaluation(db, evaluation_id)
        
        # PDF 파일 경로 설정
        os.makedirs(os.path.join(settings.MEDIA_STORAGE_PATH, "reports"), exist_ok=True)
        pdf_filename = f"evaluation_{evaluation_id}_{interview.candidate_name.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(settings.MEDIA_STORAGE_PATH, "reports", pdf_filename)
        
        # PDF 생성
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # 제목
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=12
        )
        elements.append(Paragraph(f"SK AXIS 면접 평가 리포트", title_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        # 기본 정보
        elements.append(Paragraph(f"지원자: {interview.candidate_name}", styles["Normal"]))
        elements.append(Paragraph(f"면접 일시: {interview.start_time.strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        elements.append(Paragraph(f"총점: {evaluation.total_score:.1f}/100", styles["Normal"]))
        elements.append(Spacer(1, 0.25 * inch))
        
        # 평가 결과 테이블
        data = [["평가 영역", "점수 (5점 만점)"]]
        
        # 언어적 측면
        data.append(["언어적 측면", f"{evaluation.verbal_score/20:.1f}"])
        verbal_scores = evaluation.detailed_scores.get("verbal", {})
        for criteria, score in verbal_scores.items():
            data.append([f"  - {criteria.capitalize()}", f"{score:.1f}"])
        
        # 비언어적 측면
        data.append(["비언어적 측면", f"{evaluation.nonverbal_score/20:.1f}"])
        nonverbal_scores = evaluation.detailed_scores.get("nonverbal", {})
        for criteria, score in nonverbal_scores.items():
            data.append([f"  - {criteria.capitalize()}", f"{score:.1f}"])
        
        table = Table(data, colWidths=[4*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, 1), colors.lightblue),
            ('BACKGROUND', (0, len(verbal_scores)+2), (1, len(verbal_scores)+2), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # 피드백
        elements.append(Paragraph("종합 피드백:", styles["Heading2"]))
        feedback_paragraphs = evaluation.feedback.split("\n")
        for p in feedback_paragraphs:
            if p.strip():
                elements.append(Paragraph(p, styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))
        
        # PDF 생성
        doc.build(elements)
        
        return f"reports/{pdf_filename}"
    except Exception as e:
        logger.error(f"평가 리포트 생성 실패: {e}")
        return None

def generate_excel_report(db: Session) -> Optional[str]:
    """
    모든 면접 평가 결과를 포함한 Excel 리포트 생성
    """
    try:
        # 모든 면접 정보 조회
        interviews = db.query(Interview).all()
        
        # Excel 파일 경로 설정
        os.makedirs(os.path.join(settings.MEDIA_STORAGE_PATH, "reports"), exist_ok=True)
        excel_filename = f"interview_evaluations_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        excel_path = os.path.join(settings.MEDIA_STORAGE_PATH, "reports", excel_filename)
        
        # Excel 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "면접 평가 결과"
        
        # 헤더 설정
        headers = [
            "면접 ID", "지원자 이름", "면접 일시", "총점", 
            "언어적 점수", "비언어적 점수",
            "명확성", "관련성", "깊이", "간결성", "자신감",
            "성량", "자세", "복장", "표정", "시선처리", "제스처",
            "피드백"
        ]
        ws.append(headers)
        
        # 데이터 추가
        for interview in interviews:
            # 평가 정보 조회
            evaluation = get_evaluation_by_interview(db, interview.id)
            if not evaluation:
                continue
            
            # 세부 점수 추출
            verbal_scores = evaluation.detailed_scores.get("verbal", {})
            nonverbal_scores = evaluation.detailed_scores.get("nonverbal", {})
            
            row = [
                interview.id,
                interview.candidate_name,
                interview.start_time.strftime("%Y-%m-%d %H:%M") if interview.start_time else "",
                f"{evaluation.total_score:.1f}",
                f"{evaluation.verbal_score:.1f}",
                f"{evaluation.nonverbal_score:.1f}",
                f"{verbal_scores.get('clarity', 0):.1f}",
                f"{verbal_scores.get('relevance', 0):.1f}",
                f"{verbal_scores.get('depth', 0):.1f}",
                f"{verbal_scores.get('conciseness', 0):.1f}",
                f"{verbal_scores.get('confidence', 0):.1f}",
                f"{nonverbal_scores.get('volume', 0):.1f}",
                f"{nonverbal_scores.get('posture', 0):.1f}",
                f"{nonverbal_scores.get('attire', 0):.1f}",
                f"{nonverbal_scores.get('facial_expression', 0):.1f}",
                f"{nonverbal_scores.get('eye_contact', 0):.1f}",
                f"{nonverbal_scores.get('gestures', 0):.1f}",
                evaluation.feedback[:1000] if evaluation.feedback else ""  # 피드백 길이 제한
            ]
            ws.append(row)
        
        # 열 너비 조정
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = (max_length + 2) * 1.2
            ws.column_dimensions[column].width = adjusted_width
        
        # Excel 파일 저장
        wb.save(excel_path)
        
        return f"reports/{excel_filename}"
    except Exception as e:
        logger.error(f"Excel 리포트 생성 실패: {e}")
        return None
