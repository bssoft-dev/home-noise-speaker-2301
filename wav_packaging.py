import subprocess
import wave
from utils.init import config, deviceId, logger
import aiohttp, asyncio
#from main import lock_count


def makeWavFile(filename, audioSampleSize, frames, dtype = 'byte'):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(config.getint('audio', 'channels'))
    wf.setsampwidth(audioSampleSize)
    wf.setframerate(config.getint('audio', 'rate'))
    if dtype == 'byte':
        wf.writeframes(b''.join(frames))
    else:
        wf.writeframes(frames)
    wf.close()

    
async def send_wav(filename):
    # async with aiofiles.open(filename, 'rb') as sf:
        # Send the wave file to the ML server
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            data = aiohttp.FormData()
            data.add_field('file',
                        open(filename, 'rb'),
                        filename=filename.split('/')[-1],
                        content_type='audio/wav')
            res = await session.post(f"{config['files']['send_url']}?threshold={config['speaker']['detect_threshold']}", data=data)
            return res
        except Exception as e:
            logger.warning(f'Send audio - {e}')
            return None

async def send_process(filename):
    res = await send_wav(filename)
    if res is not None:
        if res.headers.get('content-type') != 'application/json':
             # contentent-type is not json but status 200 when the server is not work properly
            logger.warning(f'Send audio - {res}')
        else:
            event_res = await res.json()
            print(f'{event_res["speaker"]}: {event_res["result"]}')
            if (event_res['speaker'] == '성훈' and event_res['result'].startswith(' 안녕하세요') and config['speaker']['use_alarm'] == 'true'):
                logger.info('Voice Detected!')
                # Light the LED
                subprocess.Popen(['python3', 'utils/pixels.py', 'alarm_light'])
                subprocess.Popen(['aplay', '-D', f'plughw:{config["audio"]["cardindex"]},{config["audio"]["deviceindex"]}', '-d', config['speaker']['alarm_duration'] ,
                        config['speaker']['alarm_wav']])
                return 'restart'
    else:
        logger.warning('Send audio result is None - maybe network error')
            

if __name__ == '__main__':
    filename = 'record_sounds/voiceRecog-19.wav'
    print(f"Send {filename}")
    asyncio.run(send_wav(filename))
