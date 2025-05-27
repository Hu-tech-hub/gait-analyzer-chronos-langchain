# 6축 센서 데이터 진단 시스템 - Chronos 임베딩 기반 RAG 서버

## 1. 폴더/파일 구조

```

sensor-diagnosis-system/
├── backend/
│   ├── app/
│   │   ├── **init**.py
│   │   ├── main.py                 # FastAPI + LangServe 메인
│   │   ├── config.py               # 환경변수 설정
│   │   ├── models/
│   │   │   ├── **init**.py
│   │   │   ├── schemas.py          # Pydantic 모델
│   │   │   └── database.py         # DB 모델
│   │   ├── services/
│   │   │   ├── **init**.py
│   │   │   ├── csv\_processor.py    # CSV 파싱/처리
│   │   │   ├── chronos\_embedder.py # Chronos 임베딩
│   │   │   ├── rag\_service.py      # RAG 검색
│   │   │   └── diagnosis\_chain.py  # LangChain 진단 체인
│   │   ├── api/
│   │   │   ├── **init**.py
│   │   │   ├── upload.py           # 업로드 엔드포인트
│   │   │   ├── diagnosis.py        # 진단 엔드포인트
│   │   │   └── chat.py             # 대화 엔드포인트
│   │   └── utils/
│   │       ├── **init**.py
│   │       ├── db\_client.py        # Supabase 클라이언트
│   │       └── vector\_store.py     # Faiss 벡터 스토어
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── scripts/
│   ├── run.sh                      # 자동 생성 스크립트
│   └── init\_db.sql                 # DB 초기화 SQL
├── data/
│   └── sample\_sensor\_data.csv      # 샘플 CSV
└── README.md

````

---

## 2. 주요 파일 설명

- **backend/app/main.py**: FastAPI + LangServe 메인 엔트리포인트  
- **backend/app/services/chronos_embedder.py**: Chronos 임베딩 생성  
- **backend/app/services/rag_service.py**: RAG 검색  
- **backend/app/services/diagnosis_chain.py**: LangChain 진단 체인  
- 기타 주요 파일 생략...

---

## 3. requirements.txt (pip 설치 목록)
> **faiss-cpu는 pip가 아닌 conda로 설치!**
> **conda 가상환경에서 실행하는 예시임.**

```text
fastapi==0.109.0
uvicorn==0.27.0
langchain==0.3.0
langraph==0.2.0
langserve==0.1.0
openai==1.40.0
supabase==2.5.0
pandas==2.1.4
numpy==1.26.3
torch==2.1.2
chronos-forecasting==1.2.0
python-multipart==0.0.6
pydantic==2.5.3
python-dotenv==1.0.0
psycopg2-binary==2.9.9
````

*(`faiss-cpu`는 아래 conda 명령 참고)*

---

## 4. .env 예시

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

CHRONOS_MODEL=amazon/chronos-bolt-tiny
DEVICE=cpu  # or cuda, mps

HOST=0.0.0.0
PORT=8000
```

---

## 5. **전체 실행 순서**

### 1) 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 등 입력
```

### 2) 데이터베이스 초기화

* Supabase Dashboard에서 `scripts/init_db.sql` 실행
* pgvector extension 활성화 확인

### 3) 의존성 설치

```bash
cd backend
pip install -r requirements.txt
conda install -c conda-forge faiss-cpu
```

### 4) 진단 지식베이스 초기화

```bash
cd backend
python -m app.services.diagnosis_knowlege_seeder
```

* (예: "He is limping to the left" 등 진단 텍스트 DB 저장)

### 5) 서버 실행

```bash
cd backend
python -m app.main
```

### 6) 프론트엔드 실행 (옵션)

```bash
cd ../frontend
python -m http.server 8001
```

---

## 6. **동작 원리 요약**

1. 센서 데이터 각 축의 임베딩 생성 (Chronos)
2. RAG로 유사 진단 패턴 검색 (영어 진단 텍스트)
3. 매칭된 진단 텍스트와 원본 통계를 GPT-4o에 전달
4. 종합 진단 생성 및 응답

---