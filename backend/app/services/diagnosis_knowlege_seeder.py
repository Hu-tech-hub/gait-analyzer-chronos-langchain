import numpy as np
from typing import List, Dict
from app.utils.db_client import get_supabase_client
from app.services.chronos_embedder import ChronosEmbedder
from app.config import settings

class DiagnosisKnowledgeSeeder:
    """진단 지식베이스 초기 데이터 생성"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.embedder = ChronosEmbedder(settings.CHRONOS_MODEL, settings.DEVICE)
        
    def seed_knowledge_base(self):
        """진단 지식 초기 데이터 삽입"""
        
        # 가속도계 진단 패턴
        acc_patterns = [
            {
                "channel": "AccX",
                "diagnosis": "He is limping to the left",
                "severity": "warning",
                "condition": "left_limp",
                "pattern_stats": {
                    "mean": [0.05, 0.15],
                    "variance": [0.06, 0.12],
                    "peak": [0.8, 1.5]
                }
            },
            {
                "channel": "AccX", 
                "diagnosis": "He is limping to the right",
                "severity": "warning",
                "condition": "right_limp",
                "pattern_stats": {
                    "mean": [-0.15, -0.05],
                    "variance": [0.06, 0.12],
                    "peak": [0.8, 1.5]
                }
            },
            {
                "channel": "AccY",
                "diagnosis": "Irregular gait pattern detected",
                "severity": "warning", 
                "condition": "irregular_gait",
                "pattern_stats": {
                    "variance": [0.1, 0.2],
                    "zero_crossing_rate": [0.4, 0.6]
                }
            },
            {
                "channel": "AccZ",
                "diagnosis": "Excessive vertical impact during walking",
                "severity": "critical",
                "condition": "high_impact",
                "pattern_stats": {
                    "peak": [2.5, 5.0],
                    "mean": [1.2, 2.0]
                }
            },
            {
                "channel": "AccZ",
                "diagnosis": "Shuffling gait with minimal lift",
                "severity": "warning",
                "condition": "shuffling",
                "pattern_stats": {
                    "variance": [0.0, 0.02],
                    "peak": [0.0, 0.5]
                }
            }
        ]
        
        # 자이로스코프 진단 패턴
        gyro_patterns = [
            {
                "channel": "GyrX",
                "diagnosis": "Tremor detected in forward-backward motion",
                "severity": "warning",
                "condition": "tremor_x",
                "pattern_stats": {
                    "variance": [15, 30],
                    "zero_crossing_rate": [0.5, 0.8]
                }
            },
            {
                "channel": "GyrY",
                "diagnosis": "Lateral instability observed",
                "severity": "critical",
                "condition": "lateral_instability",
                "pattern_stats": {
                    "peak": [100, 200],
                    "outlier_count": [10, 50]
                }
            },
            {
                "channel": "GyrZ",
                "diagnosis": "Rotational imbalance during turns",
                "severity": "warning",
                "condition": "rotational_imbalance",
                "pattern_stats": {
                    "mean": [10, 30],
                    "variance": [20, 50]
                }
            },
            {
                "channel": "GyrX",
                "diagnosis": "Parkinson's-like tremor pattern",
                "severity": "critical",
                "condition": "parkinsonian_tremor",
                "pattern_stats": {
                    "variance": [25, 50],
                    "zero_crossing_rate": [0.6, 0.9],
                    "peak": [50, 100]
                }
            },
            {
                "channel": "GyrY",
                "diagnosis": "Balance compensation in medial-lateral direction",
                "severity": "warning",
                "condition": "balance_compensation",
                "pattern_stats": {
                    "mean": [5, 15],
                    "variance": [10, 25]
                }
            }
        ]
        
        # 모든 패턴에 대해 임베딩 생성 및 저장
        all_patterns = acc_patterns + gyro_patterns
        
        for pattern in all_patterns:
            # 패턴에 맞는 합성 데이터 생성
            synthetic_data = self._generate_synthetic_pattern(
                pattern["channel"], 
                pattern["pattern_stats"]
            )
            
            # 임베딩 생성
            embedding, _ = self.embedder.embed_channel(synthetic_data)
            
            # DB에 저장
            self.supabase.table('diagnosis_knowledge').insert({
                "pattern_embedding": embedding.tolist(),
                "channel_name": pattern["channel"],
                "diagnosis_text": pattern["diagnosis"],
                "severity": pattern["severity"],
                "condition_type": pattern["condition"],
                "pattern_stats": pattern["pattern_stats"]
            }).execute()
            
            print(f"Added: {pattern['diagnosis']}")
    
    def _generate_synthetic_pattern(self, channel: str, stats: Dict) -> np.ndarray:
        """통계 특성에 맞는 합성 데이터 생성"""
        np.random.seed(42)  # 재현성을 위해
        
        # 기본 200개 샘플
        n_samples = 200
        
        # 평균값 설정
        if "mean" in stats:
            mean = np.mean(stats["mean"])
        else:
            mean = 0.0
            
        # 분산값 설정
        if "variance" in stats:
            std = np.sqrt(np.mean(stats["variance"]))
        else:
            std = 1.0
            
        # 기본 신호 생성
        data = np.random.normal(mean, std, n_samples)
        
        # 피크값 추가
        if "peak" in stats:
            peak_indices = np.random.choice(n_samples, size=5, replace=False)
            peak_value = np.mean(stats["peak"])
            data[peak_indices] = peak_value * np.random.choice([-1, 1], size=5)
            
        # 영점 교차율 조정을 위한 주파수 성분 추가
        if "zero_crossing_rate" in stats:
            zcr_target = np.mean(stats["zero_crossing_rate"])
            freq = zcr_target * 10  # 대략적인 주파수
            t = np.linspace(0, 20, n_samples)
            data += 0.1 * np.sin(2 * np.pi * freq * t)
            
        return data

# 사용 예시
if __name__ == "__main__":
    seeder = DiagnosisKnowledgeSeeder()
    seeder.seed_knowledge_base()
    print("진단 지식베이스 초기화 완료!")