from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
import pandas as pd
import numpy as np
import io
import logging
from typing import Dict, List
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from app.config import settings
from app.models.schemas import UploadResponse, DiagnosisRequest, DiagnosisResponse, ChannelDiagnosis
from app.services.csv_processor import CSVProcessor
from app.services.chronos_embedder import ChronosEmbedder
from app.services.rag_service import RAGService
from app.services.diagnosis_chain import DiagnosisChain
from app.utils.db_client import get_supabase_client

# FastAPI 앱 초기화
app = FastAPI(
    title="센서 진단 시스템",
    debug=True,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
try:
    supabase = get_supabase_client()
    embedder = ChronosEmbedder(settings.CHRONOS_MODEL, settings.DEVICE)
    rag_service = RAGService(supabase)
    diagnosis_chain = DiagnosisChain(settings.OPENAI_API_KEY)
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")
    raise

@app.post("/upload_csv", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """CSV 파일 업로드 및 처리"""
    try:
        # CSV 읽기
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # 유효성 검증
        is_valid, message = CSVProcessor.validate_sensor_data(df)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
            
        # 전처리
        df = CSVProcessor.preprocess_data(df)
        
        # DB에 원본 저장
        sensor_data = supabase.table('sensor_data').insert({
            "filename": file.filename,
            "row_count": len(df),
            "channel_count": 6,
            "raw_data": df.to_dict('records'),
            "status": "processing"
        }).execute()
        
        sensor_data_id = sensor_data.data[0]['id']
        
        # 임베딩 생성
        embeddings = embedder.process_sensor_data(df)
        
        # 임베딩 DB 저장
        for channel, data in embeddings.items():
            supabase.table('embeddings').insert({
                "sensor_data_id": sensor_data_id,
                "channel_name": channel,
                "embedding": data["embedding"].tolist(),
                "mean_value": data["stats"]["mean"],
                "variance": data["stats"]["variance"],
                "peak_value": data["stats"]["peak"],
                "min_value": data["stats"]["min"],
                "outlier_count": data["stats"]["outlier_count"],
                "zero_crossing_rate": data["stats"]["zero_crossing_rate"]
            }).execute()
            
        # 상태 업데이트
        supabase.table('sensor_data').update({
            "status": "completed"
        }).eq('id', sensor_data_id).execute()
        
        return UploadResponse(
            sensor_data_id=sensor_data_id,
            filename=file.filename,
            row_count=len(df),
            channel_count=6,
            status="completed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diagnosis", response_model=DiagnosisResponse)
async def create_diagnosis(request: DiagnosisRequest):
    """진단 생성"""
    try:
        logger.debug(f"Processing diagnosis request for sensor_data_id: {request.sensor_data_id}")
        
        # 1. 센서 데이터의 임베딩 조회
        embeddings_data = supabase.table('embeddings').select("*").eq(
            'sensor_data_id', request.sensor_data_id
        ).execute()
        
        logger.debug(f"Found {len(embeddings_data.data)} embeddings")

        if not embeddings_data.data:
            raise HTTPException(
                status_code=404,
                detail=f"No embeddings found for sensor_data_id: {request.sensor_data_id}"
            )
        
        # 2. 임베딩과 통계 데이터 구성
        sensor_embeddings = {}
        sensor_stats = {}
        
        for emb in embeddings_data.data:
            channel = emb['channel_name']
            # 문자열 임베딩을 numpy 배열로 변환
            if isinstance(emb['embedding'], str):
                embedding_str = emb['embedding'].strip('[]')
                embedding_list = [float(x) for x in embedding_str.split(',')]
                embedding_vector = np.array(embedding_list, dtype=np.float32)
            else:
                embedding_vector = np.array(emb['embedding'], dtype=np.float32)
                
            sensor_embeddings[channel] = embedding_vector
            sensor_stats[channel] = {
                'mean': emb['mean_value'],
                'variance': emb['variance'],
                'peak': emb['peak_value'],
                'outlier_count': emb['outlier_count'],
                'zero_crossing_rate': emb['zero_crossing_rate']
            }
            
        logger.debug(f"Processed embeddings for channels: {list(sensor_embeddings.keys())}")
        
        # 3. RAG를 통한 진단 패턴 검색
        matched_diagnoses = rag_service.search_diagnosis(
            sensor_embeddings, 
            threshold=10.0
        )
        
        logger.debug(f"Found {len(matched_diagnoses)} matching diagnoses")

        if not matched_diagnoses:
            raise HTTPException(
                status_code=404,
                detail="No matching diagnosis patterns found"
            )
        
        # 4. 검색 결과 로깅
        if embeddings_data.data:
            try:
                rag_service.log_search_results(
                    embeddings_data.data[0]['id'],
                    matched_diagnoses
                )
            except Exception as e:
                print(f"Warning: Failed to log search results: {str(e)}")
        
        # 각 축별 유사 임베딩 검색
        similar_channels = []
        for emb in embeddings_data.data:
            channel = emb['channel_name']
            similar = rag_service.search_similar(
                emb['embedding'],  # 문자열 형태의 임베딩을 직접 전달
                threshold=80.0
            )
            if similar:
                similar_channels.extend(similar)
                
        # 시스템 프롬프트 생성
        system_prompt = diagnosis_chain.create_system_prompt(similar_channels, sensor_stats)
        
        # 6. GPT를 통한 종합 진단 생성
        diagnosis = diagnosis_chain.generate_diagnosis(system_prompt)
        
        # 7. 각 채널별 진단 구성
        channel_diagnoses = []
        for diag in matched_diagnoses[:6]:  # 상위 6개만
            channel_diagnoses.append(ChannelDiagnosis(
                channel=diag['channel'],
                diagnosis=diag['diagnosis_text'],
                statistics=sensor_stats.get(diag['channel'], {}),
                severity=diag['severity'],
                similarity=diag['similarity']  # 유사도 점수 추가
            ))
        
        # 8. 진단 결과 DB 저장
        try:
            diagnosis_result = supabase.table('diagnosis').insert({
                "sensor_data_id": request.sensor_data_id,
                "user_id": request.user_id,
                "overall_diagnosis": diagnosis["overall_diagnosis"],
                "severity_level": diagnosis["severity_level"],
                "recommendations": diagnosis["recommendations"],
                "used_embeddings": matched_diagnoses,
                "system_prompt": system_prompt,
                
                # 각 축별 진단 저장
                "accx_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'AccX'), None),
                "accy_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'AccY'), None),
                "accz_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'AccZ'), None),
                "gyrx_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'GyrX'), None),
                "gyry_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'GyrY'), None),
                "gyrz_diagnosis": next((d['diagnosis_text'] for d in matched_diagnoses if d['channel'] == 'GyrZ'), None),
            }).execute()
        except Exception as e:
            print(f"Warning: Failed to save diagnosis result: {str(e)}")
            # 저장 실패해도 응답은 반환
            return DiagnosisResponse(
                diagnosis_id=None,  # DB 저장 실패
                sensor_data_id=request.sensor_data_id,
                channel_diagnoses=channel_diagnoses,
                overall_diagnosis=diagnosis["overall_diagnosis"],
                severity_level=diagnosis["severity_level"],
                recommendations=diagnosis["recommendations"],
                created_at=None
            )
        
        return DiagnosisResponse(
            diagnosis_id=diagnosis_result.data[0]['id'],
            sensor_data_id=request.sensor_data_id,
            channel_diagnoses=channel_diagnoses,
            overall_diagnosis=diagnosis["overall_diagnosis"],
            severity_level=diagnosis["severity_level"],
            recommendations=diagnosis["recommendations"],
            created_at=diagnosis_result.data[0]['created_at']
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in create_diagnosis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/sensor_data")
async def get_sensor_data():
    """업로드된 센서 데이터 목록 조회"""
    try:
        response = supabase.table('sensor_data').select("*").order('upload_time', desc=True).limit(10).execute()
        
        # 응답 데이터 가공
        sensor_data_list = []
        for data in response.data:
            sensor_data_list.append({
                "id": data["id"],
                "filename": data["filename"],
                "created_at": data["upload_time"],
                "status": data["status"],
                "row_count": data["row_count"]
            })
            
        return sensor_data_list
        
    except Exception as e:
        logger.error(f"Error fetching sensor data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sensor data: {str(e)}"
        )

# Uvicorn으로 서버 실행
if __name__ == "__main__":
    import uvicorn
    print(f"\n🚀 서버를 시작합니다...")
    print(f"📌 주소: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API 문서: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🛑 종료하려면 Ctrl+C를 누르세요.\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True  # 개발 중 자동 재시작
    )