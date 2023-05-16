import subprocess
import wave
from utils.init import config, deviceId, logger
import aiohttp, asyncio
# from main import lock_count

anomaly = ['roadkm', 'adult_jumping', 'hammer', 'adult_walking', 'adult_running', 'jumping', 'running']

def makeWavFile(filename, audioSampleSize, frames):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(config['audio']['channels'])
    wf.setsampwidth(audioSampleSize)
    wf.setframerate(config['audio']['rate'])
    wf.writeframes(b''.join(frames))
    wf.close()

async def send_wav(filename):
    # Send the wave file to the ML server
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            data = aiohttp.FormData()
            data.add_field('file',
                        open(filename, 'rb'),
                        filename=filename.split('/')[-1],
                        content_type='audio/wav')
            res = await session.post('%s?threshold=%s'%(config['files']['send_url'],
                            config['speaker']['detect_threshold']), data=data)
            logger.debug(await res.json())
            return res
        except Exception as e:
            logger.warning('Send audio None Receive Error - %s'%e)
            return None


async def process(filename):
    res = await send_wav(filename)
    if res is not None:
        if res.headers.get('content-type') != 'application/json':
             # contentent-type is not json but status 200 when the server is not work properly
            logger.warning('Send audio Invalid Response Error - %s'%res)
        else:
            event_res = await res.json()
            if (event_res['result'] in anomaly):
                logger.info('Stress Sound Detected!')
            

if __name__ == '__main__':
    filename = 'record_sounds/SmartSpeaker-11.wav'
    print(f"Send {filename}")
    asyncio.run(send_wav(filename))