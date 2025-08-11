from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import asyncio, os, subprocess, alsaaudio, shutil, requests
from asyncio import sleep
import uvicorn

from models import Mixin
from utils.init import config
from utils.files import create_vol_file
from utils.log_conf import app_log_conf
from utils.websocket_streaming import start_websocket_streaming, get_websocket_streamer
from bs_sound_utils.sound_mix import mix_by_ratio
from main import initPyaudio, heartbeat, record_stream, welcome_sound, websocket_streaming_task
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
    
    # WebSocket 스트리밍 태스크 시작
    if config.getboolean('options_using', 'websocket_streaming'):
        # 백그라운드에서 WebSocket 스트리밍 시작
        asyncio.create_task(start_websocket_streaming())
        # WebSocket 스트리밍 처리 태스크 시작
        asyncio.create_task(websocket_streaming_task())
    
    # 기존 태스크들을 백그라운드에서 실행
    asyncio.create_task(button_run())
    asyncio.create_task(heartbeat())
    asyncio.create_task(record_stream(stream, samplesize))
    
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
    
    # WebSocket 스트리밍 상태 정보
    websocket_status = ""
    if config.getboolean('options_using', 'websocket_streaming'):
        streamer = get_websocket_streamer()
        stats = streamer.get_statistics()
        status_color = "green" if stats["connected"] else "red"
        websocket_status = f"""
        <h2>WebSocket 스트리밍 상태</h2>
        <div style="color: {status_color};">
            연결 상태: {'연결됨' if stats["connected"] else '연결 안됨'}<br>
            전송 프레임: {stats["sent_frames"]}<br>
            버퍼 크기: {stats["buffer_size"]}<br>
            재연결 시도: {stats["connection_retries"]}<br>
            서버: {config.get('websocket', 'server_host')}:{config.get('websocket', 'server_port')}<br>
            방 이름: {config.get('websocket', 'room_name')}
        </div>
        <button onclick="refreshStatus()">상태 새로고침</button>
        <button onclick="toggleWebSocket()">스트리밍 토글</button>
        <button onclick="reconnectWebSocket()">재연결</button><br><br>
        
        <h3>WebSocket 설정</h3>
        <div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
            서버 호스트: <input type="text" id="serverHost" value="{config.get('websocket', 'server_host')}" style="width: 200px;"><br><br>
            서버 포트: <input type="number" id="serverPort" value="{config.get('websocket', 'server_port')}" style="width: 100px;"><br><br>
            방 이름: <input type="text" id="roomName" value="{config.get('websocket', 'room_name')}" style="width: 200px;"><br><br>
            스트리밍 간격(초): <input type="number" step="0.001" id="streamingInterval" value="{config.get('websocket', 'streaming_interval')}" style="width: 100px;"><br><br>
            <button onclick="updateWebSocketConfig()">설정 업데이트</button>
        </div><br>
        """
    else:
        websocket_status = """
        <h2>WebSocket 스트리밍</h2>
        <div style="color: gray;">스트리밍이 비활성화되어 있습니다</div>
        <button onclick="toggleWebSocket()">스트리밍 활성화</button><br><br>
        """
    
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
            function refreshStatus(){
                location.reload();
                }
            
            function toggleWebSocket(){
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/websocket/toggle', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function(){
                    if(xhr.status === 200){
                        var response = JSON.parse(xhr.responseText);
                        alert(response.message);
                        location.reload();
                    } else {
                        alert('토글 실패');
                    }
                };
                xhr.send();
            }
            
            function reconnectWebSocket(){
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/websocket/reconnect', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function(){
                    if(xhr.status === 200){
                        var response = JSON.parse(xhr.responseText);
                        alert(response.message);
                        location.reload();
                    } else {
                        alert('재연결 실패');
                    }
                };
                xhr.send();
            }
            
            function updateWebSocketConfig(){
                var config = {
                    server_host: document.getElementById('serverHost').value,
                    server_port: parseInt(document.getElementById('serverPort').value),
                    room_name: document.getElementById('roomName').value,
                    streaming_interval: parseFloat(document.getElementById('streamingInterval').value)
                };
                
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/websocket/config', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function(){
                    if(xhr.status === 200){
                        var response = JSON.parse(xhr.responseText);
                        alert(response.message);
                        if(response.success){
                            location.reload();
                        }
                    } else {
                        alert('설정 업데이트 실패');
                    }
                };
                xhr.send(JSON.stringify(config));
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
                {websocket_status}
                <h2>재생 음원</h2>
                {readySoundItems}
                <h2>녹음 음원</h2>
                {recordedItems}
                {scriptStr}
            </body>
        </html>
    """
    return HTMLResponse(htmlStr)

@app.get('/api/websocket/status')
async def websocket_status():
    """WebSocket 스트리밍 상태 API"""
    if not config.getboolean('options_using', 'websocket_streaming'):
        return {"enabled": False, "message": "WebSocket 스트리밍이 비활성화됨"}
    
    streamer = get_websocket_streamer()
    stats = streamer.get_statistics()
    
    return {
        "enabled": True,
        "connected": stats["connected"],
        "sent_frames": stats["sent_frames"],
        "buffer_size": stats["buffer_size"],
        "connection_retries": stats["connection_retries"],
        "server_host": config.get('websocket', 'server_host'),
        "server_port": config.get('websocket', 'server_port'),
        "room_name": config.get('websocket', 'room_name')
    }

@app.get('/api/websocket/config')
async def get_websocket_config():
    """현재 WebSocket 설정 조회"""
    return {
        "server_host": config.get('websocket', 'server_host'),
        "server_port": config.getint('websocket', 'server_port'),
        "room_name": config.get('websocket', 'room_name'),
        "streaming_interval": config.getfloat('websocket', 'streaming_interval'),
        "enabled": config.getboolean('options_using', 'websocket_streaming')
    }

@app.post('/api/websocket/config')
async def update_websocket_config(request: dict):
    """WebSocket 설정 업데이트"""
    try:
        # 설정 업데이트
        if 'server_host' in request:
            config.set('websocket', 'server_host', str(request['server_host']))
        
        if 'server_port' in request:
            config.set('websocket', 'server_port', str(request['server_port']))
        
        if 'room_name' in request:
            config.set('websocket', 'room_name', str(request['room_name']))
        
        if 'streaming_interval' in request:
            config.set('websocket', 'streaming_interval', str(request['streaming_interval']))
        
        if 'enabled' in request:
            config.set('options_using', 'websocket_streaming', 'on' if request['enabled'] else 'off')
        
        # 설정 파일에 저장
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        
        return {
            "success": True,
            "message": "WebSocket 설정이 업데이트되었습니다. 재시작 후 적용됩니다.",
            "updated_config": {
                "server_host": config.get('websocket', 'server_host'),
                "server_port": config.getint('websocket', 'server_port'),
                "room_name": config.get('websocket', 'room_name'),
                "streaming_interval": config.getfloat('websocket', 'streaming_interval'),
                "enabled": config.getboolean('options_using', 'websocket_streaming')
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"설정 업데이트 실패: {str(e)}"
        }

@app.post('/api/websocket/reconnect')
async def websocket_reconnect():
    """WebSocket 연결 재시작"""
    try:
        if not config.getboolean('options_using', 'websocket_streaming'):
            return {
                "success": False,
                "message": "WebSocket 스트리밍이 비활성화되어 있습니다"
            }
        
        streamer = get_websocket_streamer()
        
        # 기존 연결 종료
        await streamer.disconnect()
        
        # 새로운 연결 시도
        success = await streamer.connect()
        
        if success:
            return {
                "success": True,
                "message": "WebSocket 재연결 성공",
                "url": streamer.ws_url
            }
        else:
            return {
                "success": False,
                "message": "WebSocket 재연결 실패"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"재연결 중 오류: {str(e)}"
        }

@app.post('/api/websocket/toggle')
async def toggle_websocket_streaming():
    """WebSocket 스트리밍 활성화/비활성화 토글"""
    try:
        current_state = config.getboolean('options_using', 'websocket_streaming')
        new_state = not current_state
        
        config.set('options_using', 'websocket_streaming', 'on' if new_state else 'off')
        
        # 설정 파일에 저장
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        
        # 스트리밍 제어
        if new_state:
            # 활성화 시도
            streamer = get_websocket_streamer()
            success = await streamer.connect()
            message = "WebSocket 스트리밍이 활성화되었습니다" if success else "활성화했지만 연결에 실패했습니다"
        else:
            # 비활성화
            streamer = get_websocket_streamer()
            await streamer.disconnect()
            message = "WebSocket 스트리밍이 비활성화되었습니다"
        
        return {
            "success": True,
            "enabled": new_state,
            "message": message
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"토글 중 오류: {str(e)}"
        }

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
    return files

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
    uvicorn.run("app:app", host='0.0.0.0', port=80, reload=True, log_config=app_log_conf, log_level='info')
