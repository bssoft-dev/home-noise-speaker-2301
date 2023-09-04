import pyaudio, alsaaudio
import os, subprocess
import asyncio
from asyncio import sleep as asleep
import aiohttp
from time import time, sleep

from utils.init import config, deviceId, print_settings, logger
from utils import mute_alsa #mute_alsa removes many trivial warnings
import wav_packaging
if config.getboolean('options_using', 'record_speech_only'):
    from bs_sound_utils.get_speech import get_speech_from_mic

if config.get('audio', 'audio_card') == 'core_v2':
    from utils.user_button import button_run
else:
    from utils.hat_button import button_run
    

nBundle = config.getint('files', 'num_sending_bundle')
if not config.getboolean('options_using', 'send_recorded_file'):
    num_record_frames = config.getint('audio', 'num_frame')
else:
    num_record_frames = config.getint('audio', 'num_frame')*nBundle
gRecord_frames = [b'']*num_record_frames # Initialize num_record_frames length empty byte array

def check_audio_devices(p):
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        print((i, dev['name'], dev['maxInputChannels']), dev['defaultSampleRate'])

def initPyaudio() :
    # Set Speaker Volume
    m = alsaaudio.Mixer(control = config.get('audio', 'mixer_control'), cardindex = config.getint('audio', 'cardindex'))
    m.setvolume(config.getint('speaker', 'volume')) # Set the volume to custom value
    # current_volume = m.getvolume() # Get the current Volume
    # Initialize the PyAudio
    p = pyaudio.PyAudio()
    # check_audio_devices(p)
    stream = p.open(format=pyaudio.paInt16,
                channels=config.getint('audio', 'channels'),
                rate=config.getint('audio', 'rate'),
                input=True,
                frames_per_buffer=config.getint('audio', 'chunk'),
                stream_callback=record_callback)
    audioSampleSize = p.get_sample_size(pyaudio.paInt16)
    return (stream, audioSampleSize)


def record_callback(in_data, frame_count, time_info, status):
    gRecord_frames.append(in_data)
    del gRecord_frames[0]
    return (in_data, pyaudio.paContinue)


async def heartbeat():
    if config.getboolean('options_using', 'send_heartbeat'):
        while True:
            async with aiohttp.ClientSession() as session:
                try:
                    await session.get('{}/{}/heartbeat'.format(config.get('device', 'heartbeat_url'), deviceId))
                except Exception as e:
                    logger.warning('Heartbeat - %s'%e)
            await asleep(config.getint('device', 'heartbeat_interval'))


async def speech_stream(audioSampleSize):
    nfile = 0
    while(True):
        if config.getint('files', 'num_file_save') != -1:
            filename = os.path.join(config.get('files', 'record_dir'), f'{deviceId}-{nfile}.wav')
        else:
            filename = os.path.join(config.get('files', 'record_dir'), f'{int(time())}.wav')
        audiodata = get_speech_from_mic()
        wav_packaging.makeWavFile(filename, audioSampleSize, audiodata, dtype='int')
        if config.getboolean('options_using', 'send_recorded_file'):
            await wav_packaging.process(filename)
        nfile += 1

async def record_stream(stream, audioSampleSize):
    nfile = 0
    isSend = False
    count = 0
    send_recorded_file = config.getboolean('options_using', 'send_recorded_file')
    while(True):
        try:
            # logger.debug(count)
            count += 1
            if (isSend==False) and (nfile == nBundle-1):
                isSend = True
            if config.getint('files', 'num_file_save') == -1:
                filename = os.path.join(config.get('files', 'record_dir'), f'{int(time())}.wav')
            else:
                nfile += 1
                if nfile == config.getint('files', 'num_file_save') :
                    nfile = 0
                filename = os.path.join(config.get('files', 'record_dir'), f'{deviceId}-{nfile}.wav')
            # Record with non-blocking mode of pyaudio
            stream.stop_stream()
            if not send_recorded_file and count != 1:
                wav_packaging.makeWavFile(filename, audioSampleSize, gRecord_frames)
            elif isSend:
                wav_packaging.makeWavFile(filename, audioSampleSize, gRecord_frames)
                await wav_packaging.send_process(filename)
            stream.start_stream()
            # Record sound with duration of config.get('audio']['record_seconds']
            await asleep(config.getint('files', 'record_seconds'))
        except KeyboardInterrupt:
            stream.stop_stream()
            stream.close()
            quit()

async def coroutin_main(stream, audioSampleSize):
    if config.getboolean('options_using', 'record_speech_only'):
        await asyncio.gather(button_run(), heartbeat(), speech_stream(audioSampleSize))
    else:
        await asyncio.gather(button_run(), heartbeat(), record_stream(stream, audioSampleSize))


def welcome_sound():
    subprocess.Popen([
        'aplay', 
        '-D', 
        f'plughw:{config.get("audio", "cardindex")},{config.get("audio", "deviceindex")}', 
        config.get('speaker', 'welcome_wav')
        ])

if __name__ == '__main__':
    # Log starting
    logger.info('##############################################')
    logger.info(f'BS soft Corporation. {config.get("device", "name")} is Started.')

    # Start Welcome Light
    subprocess.Popen(['python3', 'utils/pixels.py', 'welcome_light'])
    # Welcome Message
    print('')
    print('############################################################')
    print(f'BS soft Corporation. {config.get("device", "name")} V{config.get("device", "version")} is Started.')
    print('############################################################')
    # Print Every settings
    print_settings(config, deviceId)
    if config.getboolean('options_using', 'use_welcome_sound'):
        welcome_sound()
        sleep(3)
    stream, audioSampleSize = initPyaudio()

    # Main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coroutin_main(stream, audioSampleSize))
    loop.close()

