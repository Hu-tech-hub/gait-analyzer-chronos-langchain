#!/usr/bin/env python3
"""
센서 진단 시스템 통합 실행 스크립트
백엔드와 프론트엔드 서버를 동시에 실행합니다.
"""

import subprocess
import sys
import time
import os
import signal
import webbrowser
from pathlib import Path

# 프로세스 저장용
processes = []

def cleanup(signum=None, frame=None):
    """프로세스 정리"""
    print("\n🛑 서버를 종료합니다...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            p.kill()
    print("✅ 종료 완료")
    sys.exit(0)

def check_port(port):
    """포트가 사용 중인지 확인"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def main():
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("🚀 센서 진단 시스템을 시작합니다...")
    
    # 경로 설정
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    
    # 포트 확인
    if check_port(8000):
        print("⚠️  포트 8000이 이미 사용 중입니다. 기존 프로세스를 종료하거나 다른 포트를 사용하세요.")
        return
    
    if check_port(8001):
        print("⚠️  포트 8001이 이미 사용 중입니다. 기존 프로세스를 종료하거나 다른 포트를 사용하세요.")
        return
    
    try:
        # 1. 백엔드 서버 시작 (출력을 직접 표시)
        print("\n📡 백엔드 서버 시작 중...")
        backend_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            cwd=backend_dir,
            stdout=sys.stdout,
            stderr=sys.stderr,
            universal_newlines=True
        )
        processes.append(backend_process)
        
        # 백엔드 시작 대기
        print("   백엔드 서버 준비 중...")
        time.sleep(5)  # 5초로 늘림
        
        # 백엔드 상태 확인
        if backend_process.poll() is not None:
            print("❌ 백엔드 서버 시작 실패!")
            print("   백엔드 로그를 확인하세요.")
            cleanup()
            return
        
        # 백엔드 헬스체크
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ 백엔드 서버 시작 완료 (http://localhost:8000)")
            else:
                print("⚠️  백엔드 서버가 응답하지 않습니다.")
        except:
            print("⚠️  백엔드 서버 연결 실패. 계속 진행합니다...")
        
        # 2. 프론트엔드 서버 시작
        print("\n🌐 프론트엔드 서버 시작 중...")
        frontend_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8001"],
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,  # 프론트엔드는 조용히
            stderr=subprocess.DEVNULL
        )
        processes.append(frontend_process)
        
        time.sleep(2)
        print("✅ 프론트엔드 서버 시작 완료 (http://localhost:8001)")
        
        # 3. 브라우저 자동 열기
        print("\n🌍 브라우저를 엽니다...")
        time.sleep(1)
        webbrowser.open("http://localhost:8001")
        
        print("\n✨ 시스템이 준비되었습니다!")
        print("📌 백엔드: http://localhost:8000")
        print("📌 프론트엔드: http://localhost:8001")
        print("\n종료하려면 Ctrl+C를 누르세요.\n")
        print("-" * 50)
        print("백엔드 서버 로그:")
        print("-" * 50)
        
        # 서버 실행 유지
        backend_process.wait()
            
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        cleanup()

if __name__ == "__main__":
    main()