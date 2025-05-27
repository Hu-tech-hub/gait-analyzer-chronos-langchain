from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser
import json

class DiagnosisChain:
    def __init__(self, openai_api_key: str):
        """진단 체인 초기화"""
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.2,
            openai_api_key=openai_api_key
        )
        
    def create_system_prompt(self, diagnoses: List[Dict], sensor_stats: Dict) -> str:
        """진단 텍스트와 센서 통계를 기반으로 시스템 프롬프트 생성"""
        prompt = """You are an expert gait analysis system specializing in 6-axis sensor data (3-axis accelerometer and 3-axis gyroscope).

Based on the sensor pattern analysis, the following conditions were detected:

**Detected Conditions (similarity > 80%):**
"""
        # 진단 텍스트 추가
        for diag in diagnoses:
            prompt += f"\n- {diag['diagnosis_text']} (Severity: {diag['severity']}, Confidence: {diag['similarity']:.1f}%)"
            
        prompt += "\n\n**Raw Sensor Statistics:**\n"
        
        # 원본 센서 통계 추가
        for channel, stats in sensor_stats.items():
            prompt += f"\n{channel}:"
            prompt += f"\n  - Mean: {stats['mean']:.4f}"
            prompt += f"\n  - Variance: {stats['variance']:.4f}"
            prompt += f"\n  - Peak: {stats['peak']:.4f}"
            prompt += f"\n  - Outliers: {stats['outlier_count']}"
            prompt += f"\n  - Zero-crossing rate: {stats['zero_crossing_rate']:.4f}"
            
        prompt += """

**Diagnostic Guidelines:**
1. Analyze the combination of detected conditions
2. Consider the severity levels (normal < warning < critical)
3. Identify primary and secondary issues
4. Provide specific recommendations based on the conditions
5. Consider the interaction between different axes

Please provide a comprehensive diagnosis in the following format:
1. Primary Condition
2. Secondary Findings
3. Overall Gait Assessment
4. Specific Recommendations
5. Follow-up Suggestions"""
        
        return prompt
    
    def generate_diagnosis(self, system_prompt: str, user_query: str = "") -> Dict:
        """진단 생성"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query if user_query else "Based on the detected conditions and sensor statistics, please provide a comprehensive gait analysis diagnosis.")
        ]
        
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        response = chain.run({})
        
        # 진단 결과 구조화
        severity = self._determine_overall_severity(response)
        recommendations = self._extract_recommendations(response)
        
        return {
            "overall_diagnosis": response,
            "severity_level": severity,
            "recommendations": recommendations
        }
    
    def _determine_overall_severity(self, diagnosis: str) -> str:
        """전체 진단의 심각도 결정"""
        diagnosis_lower = diagnosis.lower()
        
        critical_keywords = ["critical", "severe", "immediate", "urgent", "parkinson", "high risk"]
        warning_keywords = ["warning", "moderate", "caution", "monitor", "irregular", "compensation"]
        
        if any(keyword in diagnosis_lower for keyword in critical_keywords):
            return "critical"
        elif any(keyword in diagnosis_lower for keyword in warning_keywords):
            return "warning"
        return "normal"
    
    def _extract_recommendations(self, diagnosis: str) -> List[str]:
        """진단에서 권장사항 추출"""
        recommendations = []
        
        # 진단 텍스트를 줄 단위로 분리
        lines = diagnosis.split('\n')
        
        # "Recommendations" 섹션 찾기
        in_recommendations = False
        for line in lines:
            if "recommendation" in line.lower():
                in_recommendations = True
                continue
            elif "follow-up" in line.lower():
                break
                
            if in_recommendations and line.strip():
                # 번호나 불릿 포인트 제거
                clean_line = line.strip().lstrip('•-*0123456789. ')
                if clean_line:
                    recommendations.append(clean_line)
                    
        # 권장사항이 없으면 기본값 추가
        if not recommendations:
            recommendations = [
                "Continue monitoring gait patterns",
                "Consult with a healthcare professional if symptoms persist",
                "Ensure proper sensor calibration"
            ]
            
        return recommendations[:5]  # 최대 5개
    
    def _extract_conditions(self, diagnosis: str) -> List[str]:
        """진단에서 검출된 상태 추출"""
        conditions = []
        
        # 진단 텍스트에서 조건 키워드 찾기
        condition_keywords = [
            "limping", "tremor", "instability", "imbalance", 
            "shuffling", "irregular", "compensation", "impact"
        ]
        
        diagnosis_lower = diagnosis.lower()
        for keyword in condition_keywords:
            if keyword in diagnosis_lower:
                conditions.append(keyword)
                
        return conditions