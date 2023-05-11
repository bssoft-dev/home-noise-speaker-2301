import pyaudio, alsaaudio
import os
import asyncio
from asyncio import sleep
import aiohttp

from utils.init import config, deviceId, print_settings, logger
from utils import mute_alsa #mute_alsa removes many trivial warnings
import wav_packaging

nBundle = config['files']['num_sending_bundle']
num_record_frames = config['audio']['num_frame']*nBundle
gRecord_frames = [b'']*num_record_frames # Initialize num_record_frames length empty byte array
  

def initPyaudio() :
    # Set Speaker Volume
    m = alsaaudio.Mixer(control='Playback', cardindex=0)
    m.setvolume(int(config['speaker']['volume'])) # Set the volume to custom value
    # current_volume = m.getvolume() # Get the current Volume
    # Initialize the PyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                channels=config['audio']['channels'],
                rate=config['audio']['rate'],
                input=True,
                frames_per_buffer=config['audio']['chunk'],
                stream_callback=record_callback)
    audioSampleSize = p.get_sample_size(pyaudio.paInt16)
    return (stream, audioSampleSize)

def record_callback(in_data, frame_count, time_info, status):
    gRecord_frames.append(in_data)
    del gRecord_frames[0]
    return (in_data, pyaudio.paContinue)  

# def lock_count(asyncState, lock=False):
# # scream result by alarm sound will be ignored with this locking mechanism
#     if lock:
#         asyncState.alarm_lock = int(config['speaker']['alarm_duration']) + config['files']['sending_record_seconds']
#     elif asyncState.alarm_lock == 0:
#         pass
#     else:
#         count = asyncState.alarm_lock - 1
#         asyncState.alarm_lock = count

async def heartbeat():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                await session.get(f"{config['device']['heartbeat_url']}/{deviceId}/heartbeat")
            except Exception as e:
                logger.warning('Heartbeat - %s'%e)
        await sleep(config['device']['heartbeat_interval'])

async def audio_process(stream, audioSampleSize):
    nfile = 0
    isSend = False
    count = 0
    while(True):
        try:
            logger.debug(count)
            count += 1
            if (isSend==False) and (nfile == nBundle-1):
                isSend = True
            # Record with non-blocking mode of pyaudio
            stream.stop_stream()
            if isSend:
                filename = '%s/%s-%d.wav'%(config['files']['record_dir'], deviceId, nfile)
                wav_packaging.makeWavFile(filename, audioSampleSize, gRecord_frames)
                await wav_packaging.process(filename)
            stream.start_stream()
            # Record sound with duration of config['audio']['record_seconds']
            await sleep(config['audio']['record_seconds'])
            nfile += 1
            if nfile == config['files']['num_save'] :
                nfile = 0
        except KeyboardInterrupt:
            stream.stop_stream()
            stream.close()
            quit()

async def coroutin_main(stream, audioSampleSize):
    await asyncio.gather(heartbeat(), audio_process(stream, audioSampleSize))

if __name__ == '__main__':
    # Log starting
    logger.info('##############################################')
    logger.info('BS soft Corporation. SmartSpeaker is Started.')

    # # Start Welcome Light
    # subprocess.Popen(['python', 'utils/pixels.py', 'welcome_light'])
    # Welcome Message
    print('')
    print('############################################################')
    print('SmartSpeaker - Audio Recording and Play System V 0.1')
    print('############################################################')
    # Print Every settings
    print_settings(config, deviceId)

    # Initialize the directory
    os.makedirs(config['files']['record_dir'], exist_ok=True)
    
    stream, audioSampleSize = initPyaudio()

    # Main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coroutin_main(stream, audioSampleSize))
    loop.close()
