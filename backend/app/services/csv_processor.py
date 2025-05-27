import pandas as pd
import numpy as np
from typing import Tuple

class CSVProcessor:
    @staticmethod
    def validate_sensor_data(df: pd.DataFrame) -> Tuple[bool, str]:
        """센서 데이터 유효성 검증"""
        required_columns = ['AccX', 'AccY', 'AccZ', 'GyrX', 'GyrY', 'GyrZ']
        
        # 필수 컬럼 확인
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
            
        # 데이터 길이 확인
        if len(df) < 100:
            return False, "Data length is too short (minimum 100 samples required)"
            
        # 데이터 타입 확인
        for col in required_columns:
            if not np.issubdtype(df[col].dtype, np.number):
                return False, f"Column {col} contains non-numeric data"
                
        return True, "Data is valid"
        
    @staticmethod
    def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
        """센서 데이터 전처리"""
        # 결측치 처리 (forward fill 후 남은 결측치는 0으로)
        df = df.ffill().fillna(0)
        
        # 이상치 제거 (평균에서 3 표준편차 이상 벗어난 값)
        for col in df.columns:
            mean = df[col].mean()
            std = df[col].std()
            df[col] = df[col].clip(mean - 3*std, mean + 3*std)
            
        # 정규화 (-1 ~ 1 범위로)
        for col in df.columns:
            max_val = df[col].abs().max()
            if max_val > 0:
                df[col] = df[col] / max_val
                
        return df
