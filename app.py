from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import asyncio, os, subprocess, alsaaudio

from utils.init import config
from main import initPyaudio, heartbeat, audio_process
from utils.user_button import button_run

app = FastAPI(
    title="Smart Speaker",
    description="스마트 스피커 API 페이지입니다.",
    version="0.0.1"
)

record_dir = config['files']['record_dir']
prepared_dir = config['files']['sound_dir']


@app.on_event("startup")
async def startup():
    os.makedirs(record_dir, exist_ok=True)
    stream, samplesize = initPyaudio()
    asyncio.gather(button_run(), heartbeat(), audio_process(stream, samplesize))
    
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
        subprocess.Popen(['aplay', '-D', f"hw:{config['audio']['cardindex']},1", os.path.join(prepared_dir, wavfile) ])
    else:
        subprocess.Popen(['aplay', '-D', f"hw:{config['audio']['cardindex']},1", os.path.join(record_dir,wavfile) ])

@app.get('/control/stop')
async def playWav():
    subprocess.Popen(['pkill', '-9', 'aplay' ])

@app.get('/control/volume/{value}')
async def control_volume(value: int):
    m = alsaaudio.Mixer(control=config['audio']['mixer_control'], cardindex=config['audio']['cardindex'])
    m.setvolume(value) # Set the volume to custom value
    return "ok"

@app.get('/api/status/volume')
async def check_volume_level():
    m = alsaaudio.Mixer(control=config['audio']['mixer_control'], cardindex=config['audio']['cardindex'])
    current_volume = m.getvolume() # Get the current Volume
    return {"res": current_volume[0]}
    
@app.get('/api/playlist')
async def playlist():
    files = os.listdir(prepared_dir)
    return files