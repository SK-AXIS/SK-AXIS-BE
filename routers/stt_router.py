from fastapi import APIRouter, UploadFile, File
import shutil
import os
import json
from app.services.stt_service import convert_audio_to_wav, transcribe_audio_file_with_speaker_labels
from openai import OpenAI  # ✅ 새로운 방식
from dotenv import load_dotenv

load_dotenv()  # .env 로드

router = APIRouter()
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ 새로운 OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🧠 GPT에게 역할 분류 요청
def classify_speakers_with_gpt(speaker_segments: list) -> dict:
    dialogue = "\n".join(f"{seg['speaker']}: {seg['text']}" for seg in speaker_segments)

    prompt = (
        "다음은 화자 분리된 대화 내용입니다:\n\n"
        f"{dialogue}\n\n"
        "각 SPEAKER가 '면접관'인지 '지원자'인지 분류해주세요.\n"
        "다음 형식으로 JSON으로 출력하세요:\n"
        "{ \"SPEAKER_00\": \"면접관\", \"SPEAKER_01\": \"지원자\" }"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 또는 "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("[GPT 오류]", e)
        return {}

# 🔁 같은 화자 블록 묶기
def group_by_speaker(segments: list, speaker_map: dict) -> str:
    result_lines = []
    current_speaker = None
    current_text = ""

    for seg in segments:
        spk = seg["speaker"]
        role = speaker_map.get(spk, spk)
        text = seg["text"].strip()

        if spk != current_speaker:
            if current_speaker is not None:
                result_lines.append(f"{speaker_map[current_speaker]}: {current_text.strip()}")
            current_speaker = spk
            current_text = text
        else:
            current_text += " " + text

    if current_speaker and current_text:
        result_lines.append(f"{speaker_map[current_speaker]}: {current_text.strip()}")

    return "\n".join(result_lines)

@router.post("/")
async def stt_with_diarization(audio: UploadFile = File(...)):
    input_path = os.path.join(UPLOAD_DIR, audio.filename)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
        base_name = os.path.splitext(input_path)[0]
        wav_path = base_name + ".wav"

        convert_audio_to_wav(input_path, wav_path)
        speaker_segments = transcribe_audio_file_with_speaker_labels(wav_path)

        # 🧠 GPT로 화자 역할 판단
        speaker_map = classify_speakers_with_gpt(speaker_segments)

        # 📜 문장 묶기
        result_text = group_by_speaker(speaker_segments, speaker_map)

        os.remove(input_path)
        os.remove(wav_path)

        return {"result": result_text}

    except Exception as e:
        return {"error": str(e)}