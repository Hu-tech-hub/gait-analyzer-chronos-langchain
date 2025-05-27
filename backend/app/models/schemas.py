from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class UploadResponse(BaseModel):
    sensor_data_id: str
    filename: str
    row_count: int
    channel_count: int
    status: str

class DiagnosisRequest(BaseModel):
    sensor_data_id: str
    user_id: Optional[str] = None

class ChannelDiagnosis(BaseModel):
    channel: str
    diagnosis: str
    statistics: Dict[str, float]
    severity: str
    similarity: float

class DiagnosisResponse(BaseModel):
    diagnosis_id: str
    sensor_data_id: str
    channel_diagnoses: List[ChannelDiagnosis]
    overall_diagnosis: str
    severity_level: str
    recommendations: List[str]
    created_at: datetime

class ChatMessage(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    diagnosis_id: str
    message: str
    user_id: Optional[str] = None
