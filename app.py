from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import asyncio, os, subprocess, alsaaudio, shutil, requests
from asyncio import sleep
import uvicorn

from models import Mixin
from utils.init import config
from utils.files import create_vol_file, change_audio_order
from utils.log_conf import app_log_conf
from bs_sound_utils.sound_mix import mix_by_ratio
from main import initPyaudio, heartbeat, record_stream, welcome_sound
if config.get('audio', 'audio_card') == 'core_v2':
    from utils.user_button import button_run
else:
    from utils.hat_button import button_run

app = FastAPI(
    title="Smart Speaker",
    description="스마트 스피커 API 페이지입니다.",
    version=config['device']['version']
)

record_dir = config['files']['record_dir']
prepared_dir = config['files']['sound_dir']


@app.on_event("startup")
async def startup():
    os.makedirs(record_dir, exist_ok=True)
    is_update = os.path.isfile('../update')
    if config.getboolean('options_using', 'use_welcome_sound') and (is_update == False):
        welcome_sound()
        await sleep(3)
    stream, samplesize = initPyaudio() 
    asyncio.gather(button_run(), heartbeat(), record_stream(stream, samplesize))
    
@app.get('/')
async def home():
    readySoundItems=''
    for file in os.listdir(prepared_dir):
        readySoundItems = readySoundItems + f"""<div> {file} <button onclick="playRequest('ready', '{file}')">실행</button> </div><br>"""
    recordedItems=''
    files = os.listdir(record_dir)
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(record_dir, x)), reverse=True)
    
    for file in sorted_files:
        recordedItems = recordedItems + f"""<div> {file} <button onclick="playRequest('record', '{file}')">실행</button> </div><br>"""
    scriptStr="""
        <script>
            function playRequest(type, file){
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/control/play/'+type+'/'+file, true);
                xhr.onload = function(){}; //응답값 무시
                xhr.send();
                }
            function stopRequest(type, file){
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/control/stop', true);
                xhr.onload = function(){}; //응답값 무시
                xhr.send();
                }
        </script>
    """
    htmlStr = f"""
        <html>
            <head>
                <title>Smart Speaker Page</title>
            </head>
            <body>
                <h1>음원 플레이 페이지</h1>
                <div> <button onclick="stopRequest()">재생 중인 음원 중지</button> </div>
                <h2>재생 음원</h2>
                {readySoundItems}
                <h2>녹음 음원</h2>
                {recordedItems}
                {scriptStr}
            </body>
        </html>
    """
    return HTMLResponse(htmlStr)

@app.get('/control/play/{reqType}/{wavfile}')
async def playWav(reqType, wavfile):
    if reqType == 'ready':
        subprocess.Popen(['./utils/repeat_play.sh', config['audio']['cardindex'], config['audio']['deviceindex'], os.path.join(prepared_dir, wavfile) ])
        # subprocess.Popen(['aplay', '-D', f"plughw:{config['audio']['cardindex']},{config['audio']['deviceindex']}", os.path.join(prepared_dir, wavfile) ])
    else:
        subprocess.Popen(['./utils/repeat_play.sh', config['audio']['cardindex'], config['audio']['deviceindex'], os.path.join(record_dir, wavfile) ])
        # subprocess.Popen(['aplay', '-D', f"plughw:{config['audio']['cardindex']},{config['audio']['deviceindex']}", os.path.join(record_dir,wavfile) ])

@app.get('/control/stop')
async def playWav():
    subprocess.Popen(['pkill', '-9', 'repeat_play' ])
    subprocess.Popen(['pkill', '-9', 'aplay' ])

@app.get('/control/volume/{value}')
async def control_volume(value: int):
    m = alsaaudio.Mixer(control=config.get('audio', 'mixer_control'), cardindex=config.getint('audio', 'cardindex'))
    m.setvolume(value) # Set the volume to custom value
    create_vol_file(value)
    return "ok"

@app.get('/api/status/volume')
async def check_volume_level():
    m = alsaaudio.Mixer(control=config.get('audio', 'mixer_control'), cardindex=config.getint('audio', 'cardindex'))
    current_volume = m.getvolume() # Get the current Volume
    return {"res": current_volume[0]}
    
@app.get('/api/playlist')
async def playlist():
    files = os.listdir(prepared_dir)
    files.sort()
    sourted_files = change_audio_order(files)
    return sorted_files

@app.post('/api/mix/preview')
async def mix_and_preview_wavfiles(mix : Mixin):
    filename = mix_by_ratio(mix.files, mix.ratio)
    subprocess.Popen(['aplay', '-D', f"plughw:{config['audio']['cardindex']},{config['audio']['deviceindex']}", filename ])
    return filename

@app.post('/api/mix/save/{savename}')
async def mix_and_preview_wavfiles(savename: str, mix : Mixin):
    savename = f"{savename}.wav"
    filename = mix_by_ratio(mix.files, mix.ratio)
    result_file = os.path.join(prepared_dir, savename)
    shutil.move(filename, result_file)
    files = {'file': (savename, open(result_file, 'rb'), 'audio/wav')}
    res = requests.post("https://home-therapy.bs-soft.co.kr/api/upload-mixedfile", files=files)
    return {"result": res.text} 

if __name__ == '__main__':
    uvicorn.run("app:app", host='0.0.0.0', port=23019, reload=True, log_config=app_log_conf, log_level='info')
