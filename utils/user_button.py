from evdev import InputDevice, ecodes
import asyncio, subprocess


async def button_run():
    key = InputDevice("/dev/input/event0") # user버튼
    hold_count = 0
    hold_threshold = 5
    #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
    process = subprocess.Popen('sleep 0.1', stdout=subprocess.PIPE, shell=True)
    print("Button is ready")
    async for event in key.async_read_loop():
        if event.type == ecodes.EV_KEY and process.poll() is not None:
            if event.value == 2: ## button hold
                hold_count += 1
            if event.value == 0: ## button up
                if hold_count > hold_threshold:
                    #! popen 주의 - stdout과 shell 옵션이 있어야만 poll 메서드를 문제없이 사용가능
                    process = subprocess.Popen('./utils/ap_server.sh', stdout=subprocess.PIPE, shell=True)
                hold_count = 0

if __name__ == '__main__':
    asyncio.run(button_run())