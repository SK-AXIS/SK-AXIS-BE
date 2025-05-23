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
uvicorn app.main:app --reload
```

<br>

## API 문서
서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc