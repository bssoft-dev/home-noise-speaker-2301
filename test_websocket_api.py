#!/usr/bin/env python3
"""
WebSocket API 테스트 클라이언트
"""
import requests
import json

BASE_URL = "http://localhost"  # 기본 포트 80

def get_config():
    """현재 WebSocket 설정 조회"""
    try:
        response = requests.get(f"{BASE_URL}/api/websocket/config")
        if response.status_code == 200:
            config = response.json()
            print("📋 현재 WebSocket 설정:")
            for key, value in config.items():
                print(f"   {key}: {value}")
            return config
        else:
            print(f"❌ 설정 조회 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return None

def get_status():
    """WebSocket 스트리밍 상태 조회"""
    try:
        response = requests.get(f"{BASE_URL}/api/websocket/status")
        if response.status_code == 200:
            status = response.json()
            print("📊 WebSocket 스트리밍 상태:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            return status
        else:
            print(f"❌ 상태 조회 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return None

def update_config(config_data):
    """WebSocket 설정 업데이트"""
    try:
        response = requests.post(f"{BASE_URL}/api/websocket/config", json=config_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 설정 업데이트: {result['message']}")
            if result['success']:
                print("📋 업데이트된 설정:")
                for key, value in result['updated_config'].items():
                    print(f"   {key}: {value}")
            return result
        else:
            print(f"❌ 설정 업데이트 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return None

def toggle_streaming():
    """WebSocket 스트리밍 토글"""
    try:
        response = requests.post(f"{BASE_URL}/api/websocket/toggle")
        if response.status_code == 200:
            result = response.json()
            print(f"🔄 스트리밍 토글: {result['message']}")
            print(f"   활성화 상태: {result['enabled']}")
            return result
        else:
            print(f"❌ 토글 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return None

def reconnect():
    """WebSocket 재연결"""
    try:
        response = requests.post(f"{BASE_URL}/api/websocket/reconnect")
        if response.status_code == 200:
            result = response.json()
            print(f"🔄 재연결: {result['message']}")
            if 'url' in result:
                print(f"   연결 URL: {result['url']}")
            return result
        else:
            print(f"❌ 재연결 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return None

def main():
    print("🎵 WebSocket API 테스트 클라이언트")
    print("=" * 50)
    
    while True:
        print("\n📋 사용 가능한 명령:")
        print("1. 설정 조회 (config)")
        print("2. 상태 조회 (status)")
        print("3. 설정 업데이트 (update)")
        print("4. 스트리밍 토글 (toggle)")
        print("5. 재연결 (reconnect)")
        print("6. 종료 (quit)")
        
        choice = input("\n명령을 입력하세요: ").strip().lower()
        
        if choice in ['1', 'config']:
            get_config()
        
        elif choice in ['2', 'status']:
            get_status()
        
        elif choice in ['3', 'update']:
            print("\n설정할 항목을 입력하세요 (빈 값은 변경 안함):")
            
            config_data = {}
            
            host = input("서버 호스트 (현재: localhost): ").strip()
            if host:
                config_data['server_host'] = host
            
            port = input("서버 포트 (현재: 24015): ").strip()
            if port:
                try:
                    config_data['server_port'] = int(port)
                except ValueError:
                    print("❌ 포트는 숫자여야 합니다")
                    continue
            
            room = input("방 이름 (현재: smart-speaker-room): ").strip()
            if room:
                config_data['room_name'] = room
            
            interval = input("스트리밍 간격 초 (현재: 0.064): ").strip()
            if interval:
                try:
                    config_data['streaming_interval'] = float(interval)
                except ValueError:
                    print("❌ 간격은 숫자여야 합니다")
                    continue
            
            enabled = input("활성화 (y/n, 빈 값은 변경 안함): ").strip().lower()
            if enabled in ['y', 'yes', 'true', '1']:
                config_data['enabled'] = True
            elif enabled in ['n', 'no', 'false', '0']:
                config_data['enabled'] = False
            
            if config_data:
                update_config(config_data)
            else:
                print("❌ 변경할 설정이 없습니다")
        
        elif choice in ['4', 'toggle']:
            toggle_streaming()
        
        elif choice in ['5', 'reconnect']:
            reconnect()
        
        elif choice in ['6', 'quit', 'exit']:
            print("👋 종료합니다")
            break
        
        else:
            print("❌ 올바르지 않은 명령입니다")

if __name__ == "__main__":
    main() 