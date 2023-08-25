from evdev import InputDevice, ecodes
import asyncio, subprocess
from utils.init import config


def when_long_press():
    '''
    길게 눌렀을 때 WIFI 설정모드로 진입
    '''
    #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
    process = subprocess.Popen('./scripts/start_ap_server.sh', stdout=subprocess.PIPE, shell=True)
    return process
    
def when_short_press():
    process = subprocess.Popen(['aplay', '-D', f'plughw:{config["audio"]["cardindex"]},{config["audio"]["deviceindex"]}', '-d', config['speaker']['alarm_duration'] ,
                        config['speaker']['alarm_wav']])
    return process

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