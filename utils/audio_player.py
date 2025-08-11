import subprocess
from utils.init import config

# 현재 재생 중인 프로세스를 추적하는 전역 변수
current_playback_process = None

def stop_current_playback():
    """현재 재생 중인 음원을 정지합니다."""
    global current_playback_process
    
    # 현재 재생 중인 프로세스가 있으면 정지
    if current_playback_process is not None:
        try:
            current_playback_process.terminate()
            current_playback_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            current_playback_process.kill()
        except Exception as e:
            print(f"프로세스 정지 중 오류: {e}")
        finally:
            current_playback_process = None
    
    # aplay 프로세스들도 강제 종료
    try:
        subprocess.run(['pkill', '-9', 'aplay'], check=False)
        subprocess.run(['pkill', '-9', 'repeat_play'], check=False)
    except Exception as e:
        print(f"aplay 프로세스 정지 중 오류: {e}")

def play_audio_file(filename):
    """음원 파일을 재생합니다. 기존 재생 중인 음원은 정지합니다."""
    global current_playback_process
    
    # 기존 재생 중인 음원 정지
    stop_current_playback()
    
    # 새 음원 재생
    try:
        current_playback_process = subprocess.Popen([
            'aplay', 
            '-D', f"plughw:{config['audio']['cardindex']},{config['audio']['deviceindex']}", 
            filename
        ])
        return current_playback_process
    except Exception as e:
        print(f"음원 재생 중 오류: {e}")
        return None 