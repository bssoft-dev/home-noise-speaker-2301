import subprocess
import wave
from utils.init import config, deviceId, logger
import aiohttp, asyncio, alsaaudio
# from main import lock_count

anomaly = ['adult_jumping']

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
            res = await session.post(config['files']['send_url'], data=data)
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
                logger.info(f"event: {event_res['result']}")
                if event_res['power'] == '1.00':
                    m = alsaaudio.Mixer(control=config['audio']['mixer_control'], cardindex=config['audio']['cardindex'])
                    m.setvolume(100) # Set the volume to custom value
                else:
                    m = alsaaudio.Mixer(control=config['audio']['mixer_control'], cardindex=config['audio']['cardindex'])
                    m.setvolume(70) # Set the volume to custom value
                subprocess.Popen(['aplay', '-D', f"hw:{config['audio']['cardindex']},1", "-d", '6', "/home/respeaker/home-noise-speaker-2301/sounds/singingball.wav" ])
            

if __name__ == '__main__':
    filename = 'record_sounds/SmartSpeaker-11.wav'
    print(f"Send {filename}")
    asyncio.run(send_wav(filename))
