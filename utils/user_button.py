from evdev import InputDevice, ecodes
import asyncio, subprocess
from utils.init import config
from utils.audio_player import stop_current_playback, play_audio_file


def when_long_press():
    '''
    길게 눌렀을 때 WIFI 설정모드로 진입
    '''
    #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
    process = subprocess.Popen('./scripts/start_ap_server.sh', stdout=subprocess.PIPE, shell=True)
    return process
    
def when_short_press():
    # 기존 음원 정지 후 새 음원 재생
    play_audio_file(config['speaker']['alarm_wav'])

async def button_run(hold_time=0.5):
    key = InputDevice("/dev/input/event0") # user버튼
    hold_count = 0
    hold_count_threshold = hold_time*10
    #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
    process = subprocess.Popen('sleep 0.1', stdout=subprocess.PIPE, shell=True)
    print("Button is ready")
    async for event in key.async_read_loop():
        if event.type == ecodes.EV_KEY and process.poll() is not None:
            if event.value == 2: ## button hold
                hold_count += 1
            if event.value == 0: ## button up
                if hold_count > hold_count_threshold:
                    when_long_press()
                else:
                    when_short_press()
                hold_count = 0

if __name__ == '__main__':
    asyncio.run(button_run())