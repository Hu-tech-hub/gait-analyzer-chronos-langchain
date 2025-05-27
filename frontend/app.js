const API_BASE_URL = 'http://localhost:8000';

let currentSensorDataId = null;
let currentDiagnosisId = null;

async function uploadCSV() {
    console.log('Upload button clicked');
    
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('파일을 선택해주세요.');
        return;
    }
    
    console.log('File selected:', file.name);
    
    const formData = new FormData();
    formData.append('file', file);
    
    // 상태 표시
    document.getElementById('uploadStatus').innerHTML = '<p>업로드 중...</p>';
    
    try {
        console.log('Sending request to:', `${API_BASE_URL}/upload_csv`);
        
        const response = await fetch(`${API_BASE_URL}/upload_csv`, {
            method: 'POST',
            body: formData
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`업로드 실패: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Upload response:', data);
        
        currentSensorDataId = data.sensor_data_id;
        
        document.getElementById('uploadStatus').innerHTML = `
            <p>✅ 업로드 완료</p>
            <p>파일명: ${data.filename}</p>
            <p>데이터 행수: ${data.row_count}</p>
            <p>채널 수: ${data.channel_count}</p>
        `;
        
        // 자동으로 진단 시작
        await createDiagnosis();
        
    } catch (error) {
        console.error('Upload error:', error);
        document.getElementById('uploadStatus').innerHTML = 
            `<p style="color: red;">❌ 업로드 실패: ${error.message}</p>`;
    }
}

async function createDiagnosis() {
    if (!currentSensorDataId) {
        console.error('No sensor data ID');
        return;
    }
    
    console.log('Creating diagnosis for:', currentSensorDataId);
    
    try {
        const response = await fetch(`${API_BASE_URL}/diagnosis`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sensor_data_id: currentSensorDataId
            })
        });
        
        console.log('Diagnosis response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Diagnosis error:', errorText);
            throw new Error('진단 실패');
        }
        
        const data = await response.json();
        console.log('Diagnosis data:', data);
        
        currentDiagnosisId = data.diagnosis_id;
        
        // 진단 결과 표시
        document.querySelector('.diagnosis-section').style.display = 'block';
        document.getElementById('diagnosisResult').innerHTML = `
            <h3 class="severity-${data.severity_level}">
                진단 결과: ${data.severity_level.toUpperCase()}
            </h3>
            <div>
                <h4>종합 진단:</h4>
                <p>${data.overall_diagnosis}</p>
            </div>
            <div>
                <h4>권장사항:</h4>
                <ul>
                    ${data.recommendations.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `;
        
        // 채팅 섹션 표시
        document.querySelector('.chat-section').style.display = 'block';
        
    } catch (error) {
        console.error('Diagnosis error:', error);
        alert(`진단 실패: ${error.message}`);
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message || !currentDiagnosisId) return;
    
    // 사용자 메시지 표시
    addMessage(message, 'user');
    input.value = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                diagnosis_id: currentDiagnosisId,
                message: message
            })
        });
        
        if (!response.ok) throw new Error('메시지 전송 실패');
        
        const data = await response.json();
        addMessage(data.response, 'assistant');
        
    } catch (error) {
        addMessage(`오류: ${error.message}`, 'assistant');
    }
}

function addMessage(content, role) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Enter 키 지원
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, API URL:', API_BASE_URL);
    
    // 업로드 버튼에 이벤트 리스너 추가
    const uploadBtn = document.querySelector('button[onclick="uploadCSV()"]');
    if (uploadBtn) {
        console.log('Upload button found');
    } else {
        console.error('Upload button not found!');
    }
    
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});