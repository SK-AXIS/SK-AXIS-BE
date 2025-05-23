## 오디오 처리 및 STT 프로세스

### 1. 오디오 녹음 및 청크 업로드
- 클라이언트에서 오디오를 녹음하여 청크 단위로 서버에 전송합니다.
- 각 청크는 `POST /api/v1/media/{interview_id}/upload-audio-chunk` 엔드포인트를 통해 업로드됩니다.
- 업로드된 각 청크는 `./media_storage/audios/interview_{interview_id}/chunk_{chunk_index}.webm` 경로에 저장됩니다.
- 동시에 각 청크는 STT(Speech-to-Text) 처리되어 텍스트로 변환됩니다.
- 변환된 텍스트는 Redis에 저장되어 실시간으로 조회할 수 있습니다.

### 2. 오디오 청크 병합
- 녹음이 완료되면 클라이언트는 `POST /api/v1/media/{interview_id}/merge-audio` 엔드포인트를 호출합니다.
- 서버는 백그라운드 작업으로 모든 오디오 청크를 하나의 MP3 파일로 병합합니다.
- 병합된 MP3 파일은 `./media_storage/audios/interview_{interview_id}.mp3` 경로에 저장됩니다.
- 병합된 오디오 파일의 경로는 데이터베이스에 저장되어 나중에 조회할 수 있습니다.

### 3. 오디오 파일 조회
- 병합된 오디오 파일은 `GET /api/v1/media/{interview_id}/audio` 엔드포인트를 통해 다운로드할 수 있습니다.

<br>

## 설치 및 실행 방법

### 1. 의존성 설치(가상환경 추천)
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다.

### 3. 데이터베이스 설정
MySQL 데이터베이스를 생성하고 초기 마이그레이션을 실행합니다.

### 4. 서버 실행
```bash
python run.py
```
또는
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

<br>

## API 문서
서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
