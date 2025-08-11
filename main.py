import pyaudio, alsaaudio
import os, subprocess
import asyncio
from asyncio import sleep as asleep
import aiohttp
from time import time, sleep
import threading
from collections import deque

from utils.init import config, deviceId, print_settings, logger
from utils import mute_alsa #mute_alsa removes many trivial warnings
from utils.websocket_streaming import start_websocket_streaming, stream_audio_data
from utils.audio_player import stop_current_playback, play_audio_file
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

# WebSocket 스트리밍을 위한 전역 버퍼
websocket_audio_buffer = deque(maxlen=100)  # 최대 100개 프레임 저장
websocket_buffer_lock = threading.Lock()

def check_audio_devices(p):
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        print((i, dev['name'], dev['maxInputChannels']), dev['defaultSampleRate'])

def initPyaudio() :
    # Set Speaker Volume
    m = alsaaudio.Mixer(control = config.get('audio', 'mixer_control'), cardindex = config.getint('audio', 'cardindex'))
    new_volume = config.getint('speaker', 'volume')
    for file in os.listdir('../'):
        if file.endswith('.vol'):
            new_volume = int(file.split('.')[0]) # Find previous volume
    m.setvolume(new_volume) # Set the volume to custom value
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
    
    # WebSocket 스트리밍 - 스레드 안전한 버퍼링
    if config.getboolean('options_using', 'websocket_streaming'):
        with websocket_buffer_lock:
            websocket_audio_buffer.append(in_data)
    
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
        
        # WebSocket 스트리밍 (음성 감지 모드에서도)
        if config.getboolean('options_using', 'websocket_streaming'):
            await stream_audio_data(audiodata)
        
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
    # WebSocket 스트리밍 태스크 시작
    websocket_task = None
    if config.getboolean('options_using', 'websocket_streaming'):
        websocket_task = await start_websocket_streaming()
        if websocket_task:
            logger.info("WebSocket 스트리밍이 시작되었습니다")
        else:
            logger.warning("WebSocket 스트리밍 시작 실패")
    
    # 기존 태스크들과 함께 실행
    tasks = [button_run(), heartbeat()]
    
    if config.getboolean('options_using', 'record_speech_only'):
        tasks.append(speech_stream(audioSampleSize))
    else:
        tasks.append(record_stream(stream, audioSampleSize))
    
    # WebSocket 스트리밍 처리 태스크 추가
    if config.getboolean('options_using', 'websocket_streaming'):
        tasks.append(websocket_streaming_task())
    
    # WebSocket 태스크도 추가 (있는 경우)
    if websocket_task:
        tasks.append(websocket_task)
    
    await asyncio.gather(*tasks)


async def websocket_streaming_task():
    """WebSocket 스트리밍 처리 태스크"""
    if not config.getboolean('options_using', 'websocket_streaming'):
        return
        
    logger.info("WebSocket 스트리밍 처리 태스크 시작")
    
    while True:
        try:
            # 버퍼에서 오디오 데이터 가져오기
            audio_data = None
            with websocket_buffer_lock:
                if websocket_audio_buffer:
                    audio_data = websocket_audio_buffer.popleft()
            
            if audio_data:
                await stream_audio_data(audio_data)
            
            # 짧은 간격으로 체크
            await asleep(0.01)  # 10ms
            
        except Exception as e:
            logger.error(f"WebSocket 스트리밍 태스크 오류: {e}")
            await asleep(1)


def welcome_sound():
    play_audio_file(config.get('speaker', 'welcome_wav'))

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
    if config.getboolean('options_using', 'websocket_streaming'):
        print(f'WebSocket 스트리밍: 활성화 ({config.get("websocket", "server_host")}:{config.get("websocket", "server_port")})')
    print('############################################################')
    # Print Every settings
    print_settings(config, deviceId)
    is_update = os.path.isfile('../update')
    if config.getboolean('options_using', 'use_welcome_sound') and (is_update == False):
        welcome_sound()
        sleep(3)
    stream, audioSampleSize = initPyaudio()

    # Main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coroutin_main(stream, audioSampleSize))
    loop.close()

