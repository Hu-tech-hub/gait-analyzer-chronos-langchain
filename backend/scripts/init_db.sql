-- 0. 확장자 활성화(제일 먼저 실행)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 센서 데이터 원본 테이블
CREATE TABLE IF NOT EXISTS sensor_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    upload_time TIMESTAMP DEFAULT NOW(),
    row_count INTEGER,
    channel_count INTEGER,
    raw_data JSONB,
    user_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'uploaded'
);

-- 2. 임베딩 테이블
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_data_id UUID REFERENCES sensor_data(id) ON DELETE CASCADE,
    channel_name VARCHAR(50) NOT NULL,
    embedding vector(256),
    pooling_method VARCHAR(20) DEFAULT 'mean',
    mean_value FLOAT,
    variance FLOAT,
    peak_value FLOAT,
    min_value FLOAT,
    outlier_count INTEGER,
    zero_crossing_rate FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2.1 인덱스 추가 (중복 제거)
CREATE INDEX IF NOT EXISTS idx_channel ON embeddings(channel_name);
CREATE INDEX IF NOT EXISTS idx_sensor_data ON embeddings(sensor_data_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- 3. RAG 진단 지식베이스 (영어 진단 텍스트)
CREATE TABLE IF NOT EXISTS diagnosis_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_embedding VECTOR(256), -- 패턴의 임베딩
    channel_name VARCHAR(50), -- 관련 축
    diagnosis_text TEXT, -- 영어 진단 내용 (예: "He is limping to the left")
    severity VARCHAR(20), -- normal, warning, critical
    condition_type VARCHAR(100), -- limp, tremor, imbalance, etc.
    
    -- 패턴 특성 (이 진단이 적용되는 조건)
    pattern_stats JSONB, -- {"mean": [min, max], "variance": [min, max], ...}
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. RAG 검색 로그
CREATE TABLE IF NOT EXISTS rag_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_embedding_id UUID REFERENCES embeddings(id),
    search_time TIMESTAMP DEFAULT NOW(),
    matched_diagnoses JSONB, -- [{knowledge_id, diagnosis_text, similarity_score, channel}]
    threshold FLOAT DEFAULT 80.0,
    matched_count INTEGER
);

-- 5. 진단 결과
CREATE TABLE IF NOT EXISTS diagnosis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_data_id UUID REFERENCES sensor_data(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    
    -- 각 축별 진단 결과
    accx_diagnosis TEXT,
    accy_diagnosis TEXT,
    accz_diagnosis TEXT,
    gyrx_diagnosis TEXT,
    gyry_diagnosis TEXT,
    gyrz_diagnosis TEXT,
    
    -- 종합 진단
    overall_diagnosis TEXT,
    severity_level VARCHAR(20), -- normal, warning, critical
    recommendations TEXT[],
    
    -- 진단에 사용된 정보
    used_embeddings JSONB,
    system_prompt TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. 대화 로그
CREATE TABLE IF NOT EXISTS chat_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    diagnosis_id UUID REFERENCES diagnosis(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    role VARCHAR(20), -- user, assistant, system
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 추가 인덱스들
CREATE INDEX IF NOT EXISTS idx_diagnosis_knowledge_vector ON diagnosis_knowledge USING ivfflat (pattern_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_diagnosis_user ON diagnosis(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_diagnosis ON chat_log(diagnosis_id);
CREATE INDEX IF NOT EXISTS idx_diagnosis_knowledge_channel ON diagnosis_knowledge(channel_name);
CREATE INDEX IF NOT EXISTS idx_diagnosis_knowledge_condition ON diagnosis_knowledge(condition_type);