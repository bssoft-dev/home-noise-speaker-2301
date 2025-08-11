#!/usr/bin/env python3
"""
오디오 플레이어 기능 테스트 스크립트
기존 음원 정지 후 새 음원 재생 기능을 테스트합니다.
"""

import time
import os
from utils.audio_player import play_audio_file, stop_current_playback
from utils.init import config

def test_audio_player():
    """오디오 플레이어 기능을 테스트합니다."""
    
    # 테스트할 음원 파일들
    sound_dir = config['files']['sound_dir']
    test_files = []
    
    # sounds 디렉토리에서 wav 파일들을 찾습니다
    if os.path.exists(sound_dir):
        for file in os.listdir(sound_dir):
            if file.endswith('.wav'):
                test_files.append(os.path.join(sound_dir, file))
    
    if not test_files:
        print("테스트할 wav 파일을 찾을 수 없습니다.")
        return
    
    print(f"테스트할 파일들: {test_files}")
    print("\n=== 오디오 플레이어 테스트 시작 ===")
    
    # 첫 번째 파일 재생
    print(f"\n1. 첫 번째 파일 재생: {test_files[0]}")
    play_audio_file(test_files[0])
    time.sleep(2)
    
    # 두 번째 파일 재생 (첫 번째 파일이 자동으로 정지되어야 함)
    if len(test_files) > 1:
        print(f"\n2. 두 번째 파일 재생: {test_files[1]}")
        print("   (첫 번째 파일이 자동으로 정지되어야 합니다)")
        play_audio_file(test_files[1])
        time.sleep(2)
    
    # 세 번째 파일 재생 (두 번째 파일이 자동으로 정지되어야 함)
    if len(test_files) > 2:
        print(f"\n3. 세 번째 파일 재생: {test_files[2]}")
        print("   (두 번째 파일이 자동으로 정지되어야 합니다)")
        play_audio_file(test_files[2])
        time.sleep(2)
    
    # 수동으로 정지
    print("\n4. 수동으로 정지")
    stop_current_playback()
    
    print("\n=== 테스트 완료 ===")
    print("모든 테스트가 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    test_audio_player() 