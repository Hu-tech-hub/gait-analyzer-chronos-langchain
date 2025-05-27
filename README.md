# 6축 센서 데이터 진단 시스템 - Chronos 임베딩 기반 RAG 서버

## 1. 폴더/파일 구조

sensor-diagnosis-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI + LangServe 메인
│   │   ├── config.py               # 환경변수 설정
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py          # Pydantic 모델
│   │   │   └── database.py         # DB 모델
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── csv_processor.py    # CSV 파싱/처리
│   │   │   ├── chronos_embedder.py # Chronos 임베딩
│   │   │   ├── rag_service.py      # RAG 검색
│   │   │   └── diagnosis_chain.py  # LangChain 진단 체인
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py           # 업로드 엔드포인트
│   │   │   ├── diagnosis.py        # 진단 엔드포인트
│   │   │   └── chat.py             # 대화 엔드포인트
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── db_client.py        # Supabase 클라이언트
│   │       └── vector_store.py     # Faiss 벡터 스토어
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── scripts/
│   ├── run.sh                      # 자동 생성 스크립트
│   └── init_db.sql                # DB 초기화 SQL
├── data/
│   └── sample_sensor_data.csv      # 샘플 CSV
└── README.md

## 2. 주요 파일 설명

txtfastapi==0.109.0
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
faiss-cpu==1.7.4
python-multipart==0.0.6
pydantic==2.5.3
python-dotenv==1.0.0
psycopg2-binary==2.9.9

## Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

##  Chronos Model
CHRONOS_MODEL=amazon/chronos-bolt-tiny
DEVICE=cpu  # or cuda, mps

## Server
HOST=0.0.0.0
PORT=8000


## 전체 실행 순서 정리

환경 설정
```bash
cp .env.example .env
# .env 파일에 API 키 등 입력
```

데이터베이스 초기화

Supabase Dashboard에서 scripts/init_db.sql 실행
pgvector extension 활성화 확인


의존성 설치
```bash
cd backend
pip install -r pip_requirements.txt
conda install -c conda-forge faiss-cpu
```

진단 지식베이스 초기화 (중요!)
```bash
cd backend && python -m app.services.diagnosis_knowlege_seeder
```
이 단계에서 "He is limping to the left" 같은 진단 텍스트들이 DB에 저장됩니다.
서버 실행
```bash
cd backend && python -m app.main
```

프론트엔드 실행 (미완성)
```bash
cd ../frontend
python -m http.server 8001
```


이제 시스템이 센서 데이터를 분석할 때:

각 축의 임베딩을 생성
RAG로 유사한 진단 패턴 검색 (영어 진단 텍스트)
매칭된 진단 텍스트와 원본 통계를 GPT-4o에 전달
종합적인 진단 생성