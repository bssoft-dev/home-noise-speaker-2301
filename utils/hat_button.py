import RPi.GPIO as GPIO
from asyncio import sleep
import subprocess

BUTTON = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON, GPIO.IN)

def when_press():
    # '''
    # 버튼 눌렀을 때 WIFI 설정모드로 진입
    # '''
    # #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
    print('Button Pressed')
    process = subprocess.Popen('./scripts/start_ap_server.sh', stdout=subprocess.PIPE, shell=True)
    return process

async def button_run():
   while True:
       state = GPIO.input(BUTTON)
       if not (state): # button is pressed
           when_press()
       await sleep(0.1)