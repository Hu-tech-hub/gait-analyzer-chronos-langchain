import torch
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from chronos import BaseChronosPipeline

class ChronosEmbedder:
    def __init__(self, model_name: str, device: str):
        self.pipeline = BaseChronosPipeline.from_pretrained(
            model_name,
            device_map=device,
            torch_dtype=torch.bfloat16 if device != "cpu" else torch.float32,
        )
        
    def embed_channel(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """단일 채널 데이터 임베딩 및 통계 계산"""
        # 텐서 변환
        context = torch.tensor(data, dtype=torch.float32).unsqueeze(0)
        
        # 임베딩 생성
        embeddings, _ = self.pipeline.embed(context)
        
        # 시계열 차원 평균 풀링 [1, L, 256] -> [1, 256]
        pooled_embedding = embeddings.mean(dim=1).squeeze(0).numpy()
        
        # 통계 계산
        stats = {
            "mean": float(np.mean(data)),
            "variance": float(np.var(data)),
            "peak": float(np.max(np.abs(data))),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "outlier_count": int(np.sum(np.abs(data - np.mean(data)) > 3 * np.std(data))),
            "zero_crossing_rate": float(np.sum(np.diff(np.sign(data)) != 0) / len(data))
        }
        
        return pooled_embedding, stats
    
    def process_sensor_data(self, df: pd.DataFrame) -> Dict:
        """6축 센서 데이터 전체 처리"""
        channels = ['AccX', 'AccY', 'AccZ', 'GyrX', 'GyrY', 'GyrZ']
        results = {}
        
        for channel in channels:
            if channel in df.columns:
                embedding, stats = self.embed_channel(df[channel].values)
                results[channel] = {
                    "embedding": embedding,
                    "stats": stats
                }
                
        return results
