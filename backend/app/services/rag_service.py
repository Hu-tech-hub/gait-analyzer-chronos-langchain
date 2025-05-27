import numpy as np
import faiss
from typing import List, Dict, Tuple
from supabase import Client
import json

class RAGService:
    def __init__(self, supabase_client: Client, embedding_dim: int = 256):
        self.client = supabase_client
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatIP(embedding_dim)  # 내적 유사도
        self.knowledge_map = {}  # index -> diagnosis knowledge
        self._load_knowledge_base()
        
    def _load_knowledge_base(self):
        """진단 지식베이스 로드"""
        # DB에서 모든 진단 패턴 로드
        knowledge_data = self.client.table('diagnosis_knowledge').select("*").execute()
        
        vectors = []
        for idx, knowledge in enumerate(knowledge_data.data):
            try:
                # 문자열로 된 임베딩을 파싱
                if isinstance(knowledge['pattern_embedding'], str):
                    # 문자열에서 대괄호 제거하고 쉼표로 분리
                    embedding_str = knowledge['pattern_embedding'].strip('[]')
                    embedding_list = [float(x) for x in embedding_str.split(',')]
                    vector = np.array(embedding_list, dtype=np.float32)
                else:
                    vector = np.array(knowledge['pattern_embedding'], dtype=np.float32)
                
                # 임베딩 벡터 정규화
                vector = vector / np.linalg.norm(vector)
                vectors.append(vector)
                
                # 지식 맵에 저장
                self.knowledge_map[idx] = {
                    "id": knowledge['id'],
                    "channel": knowledge['channel_name'],
                    "diagnosis": knowledge['diagnosis_text'],
                    "severity": knowledge['severity'],
                    "condition_type": knowledge['condition_type'],
                    "pattern_stats": knowledge['pattern_stats']
                }
            except Exception as e:
                print(f"Error processing embedding for knowledge {knowledge['id']}: {str(e)}")
                continue
            
        # FAISS 인덱스에 추가
        if vectors:
            self.index.add(np.array(vectors))
            print(f"Loaded {len(vectors)} diagnosis patterns into RAG")
            
    def search_diagnosis(self, sensor_embeddings: Dict[str, np.ndarray], threshold: float = 80.0) -> List[Dict]:
        """센서 임베딩에 대한 진단 검색"""
        all_diagnoses = []
        
        for channel, embedding in sensor_embeddings.items():
            # 쿼리 벡터 정규화
            query_vector = embedding / np.linalg.norm(embedding)
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            
            # 유사 패턴 검색 (상위 5개)
            scores, indices = self.index.search(query_vector, k=5)
            
            # 결과 필터링 및 처리
            for score, idx in zip(scores[0], indices[0]):
                similarity = float(score * 100)  # 백분율로 변환
                
                if similarity >= threshold:
                    knowledge = self.knowledge_map.get(int(idx))
                    
                    # 채널이 일치하는 경우만 추가
                    if knowledge and knowledge['channel'] == channel:
                        all_diagnoses.append({
                            "channel": channel,
                            "diagnosis_text": knowledge['diagnosis'],
                            "severity": knowledge['severity'],
                            "condition_type": knowledge['condition_type'],
                            "similarity": similarity,
                            "pattern_stats": knowledge['pattern_stats']
                        })
                        
        # 유사도 기준 정렬
        all_diagnoses.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_diagnoses
    
    def log_search_results(self, query_embedding_id: str, diagnoses: List[Dict]):
        """검색 결과 로깅"""
        self.client.table('rag_log').insert({
            "query_embedding_id": query_embedding_id,
            "matched_diagnoses": diagnoses,
            "threshold": 80.0,
            "matched_count": len(diagnoses)
        }).execute()

    def search_similar(self, query_embedding: np.ndarray, k: int = 10, threshold: float = 80.0) -> List[Dict]:
        """유사 임베딩 검색"""
        try:
            # 문자열인 경우 파싱
            if isinstance(query_embedding, str):
                # 대괄호 제거 및 쉼표로 분리
                embedding_str = query_embedding.strip('[]')
                embedding_list = [float(x) for x in embedding_str.split(',')]
                query_embedding = np.array(embedding_list, dtype=np.float32)
            elif isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding, dtype=np.float32)
                
            # 쿼리 벡터 정규화
            query_vector = query_embedding / np.linalg.norm(query_embedding)
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            
            # 검색
            scores, indices = self.index.search(query_vector, k)
            
            # 결과 필터링 (유사도 80 이상)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                similarity = float(score * 100)  # 백분율로 변환
                if similarity >= threshold:
                    metadata = self.knowledge_map.get(int(idx), {})
                    results.append({
                        "embedding_id": metadata.get("id"),
                        "channel": metadata.get("channel"),
                        "similarity": similarity,
                        "stats": metadata.get("pattern_stats", {}),
                        "diagnosis_text": metadata.get("diagnosis", ""),
                        "severity": metadata.get("severity", "normal")
                    })
                    
            return results
        except Exception as e:
            print(f"Error in search_similar: {str(e)}")
            return []