from pydub import AudioSegment
import whisper
from pyannote.audio import Pipeline
import os
from dotenv import load_dotenv

# Whisper 모델 로드
model = whisper.load_model("small")

# 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
#load_dotenv()
load_dotenv(dotenv_path)
HUGGINGFACE_TOKEN = os.getenv("HF_TOKEN")
print(f"HUGGINGFACE_TOKEN: {HUGGINGFACE_TOKEN[:8]}..." if HUGGINGFACE_TOKEN else "❌ 환경 변수 로드 실패")

# pyannote 화자 분리 파이프라인
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization",
    use_auth_token=HUGGINGFACE_TOKEN
)

def convert_webm_to_wav(webm_path, wav_path):
    audio = AudioSegment.from_file(webm_path, format="webm")
    audio.export(wav_path, format="wav")
# 오디오 변환 (확장자 무관)
def convert_audio_to_wav(input_path: str, output_path: str):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)  # 샘플레이트 및 채널 설정
    audio.export(output_path, format="wav")

# Whisper 단순 전사
def transcribe_audio_file(file_path: str) -> str:
    result = model.transcribe(file_path)
    return result["text"]

# Whisper + pyannote 화자 분리 전사
def transcribe_audio_file_with_speaker_labels(wav_path: str) -> list:
    diarization = diarization_pipeline(wav_path)
    result = model.transcribe(wav_path, verbose=False)

    segments = []
    for turn in diarization.itertracks(yield_label=True):
        start, end = turn[0].start, turn[0].end
        speaker = turn[2]
        spoken_texts = [
            seg['text'] for seg in result['segments']
            if not (seg['end'] < start or seg['start'] > end)
        ]
        combined = ' '.join(spoken_texts).strip()
        if combined:
            segments.append({
                "speaker": speaker,
                "start": round(start, 1),
                "end": round(end, 1),
                "text": combined
            })
    return segments