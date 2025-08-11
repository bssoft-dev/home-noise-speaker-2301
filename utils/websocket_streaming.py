"""
WebSocket 실시간 오디오 스트리밍 모듈
Safety Server와 연결하여 실시간 오디오 데이터 전송
"""
import asyncio
import websockets
import numpy as np
import time
from datetime import datetime
from typing import Optional
import aiohttp
from utils.init import config, deviceId, logger

class WebSocketStreamer:
    def __init__(self):
        self.server_host = config.get('websocket', 'server_host')
        self.server_port = config.getint('websocket', 'server_port')
        self.room_name = config.get('websocket', 'room_name')
        self.device_id = deviceId
        self.sample_rate = config.getint('audio', 'rate')
        self.chunk_size = config.getint('audio', 'chunk')
        self.streaming_interval = config.getfloat('websocket', 'streaming_interval')
        
        # WebSocket URL 구성
        if self.server_host.startswith('https://'):
            protocol = 'wss'
            host = self.server_host.replace('https://', '')
        elif self.server_host.startswith('http://'):
            protocol = 'ws'
            host = self.server_host.replace('http://', '')
        else:
            protocol = 'ws'
            host = self.server_host
            
        if self.server_port == 0:
            self.ws_url = f"{protocol}://{host}/ws/room/{self.room_name}/{self.sample_rate}/int16/{self.device_id}"
        else:
            self.ws_url = f"{protocol}://{host}:{self.server_port}/ws/room/{self.room_name}/{self.sample_rate}/int16/{self.device_id}"
        
        # 연결 상태 및 통계
        self.websocket = None
        self.is_connected = False
        self.sent_frames = 0
        self.connection_retries = 0
        self.max_retries = 5
        
        # 오디오 버퍼
        self.stream_buffer = []
        self.buffer_lock = asyncio.Lock()
        
        logger.info(f"WebSocket Streamer 초기화: {self.ws_url}")

    async def create_room(self):
        """Safety Server에 방 생성 요청"""
        if self.server_host.startswith('https://'):
            protocol = 'https'
            host = self.server_host.replace('https://', '')
        elif self.server_host.startswith('http://'):
            protocol = 'http'
            host = self.server_host.replace('http://', '')
        else:
            protocol = 'http'
            host = self.server_host
            
        if self.server_port == 0:
            create_url = f"{protocol}://{host}/v1/create_room"
        else:
            create_url = f"{protocol}://{host}:{self.server_port}/v1/create_room"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(create_url, json={"room_name": self.room_name}) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"방 생성 성공: {result.get('message', 'Success')}")
                    elif response.status == 409:
                        # 방이 이미 존재하는 경우
                        logger.info(f"방이 이미 존재함: {self.room_name}")
                    else:
                        logger.warning(f"방 생성 응답 코드: {response.status}")
            except Exception as e:
                logger.warning(f"방 생성 요청 실패 (이미 존재할 수 있음): {e}")

    async def connect(self):
        """WebSocket 서버에 연결"""
        try:
            # 먼저 방 생성 시도 (실패해도 연결은 계속 진행)
            try:
                await self.create_room()
            except Exception as e:
                logger.warning(f"방 생성 실패했지만 연결을 계속 시도합니다: {e}")
            
            # WebSocket 연결
            logger.info(f"WebSocket 연결 시도: {self.ws_url}")
            self.websocket = await websockets.connect(
                self.ws_url,
                max_size=None,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            self.connection_retries = 0
            logger.info("WebSocket 연결 성공!")
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """WebSocket 연결 종료"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("WebSocket 연결 종료")
            except:
                pass
        self.is_connected = False
        self.websocket = None

    async def reconnect(self):
        """재연결 시도"""
        if self.connection_retries >= self.max_retries:
            logger.error(f"최대 재연결 시도 횟수 초과 ({self.max_retries})")
            return False
            
        self.connection_retries += 1
        logger.info(f"재연결 시도 {self.connection_retries}/{self.max_retries}")
        
        await self.disconnect()
        await asyncio.sleep(2 ** self.connection_retries)  # 지수 백오프
        
        return await self.connect()

    async def add_audio_data(self, audio_data: bytes):
        """오디오 데이터를 스트리밍 버퍼에 추가"""
        if not self.is_connected:
            return
            
        async with self.buffer_lock:
            self.stream_buffer.append(audio_data)
            
            # 버퍼가 너무 크면 오래된 데이터 제거 (메모리 보호)
            if len(self.stream_buffer) > 100:  # 약 6.4초분량
                self.stream_buffer.pop(0)

    async def streaming_loop(self):
        """실시간 스트리밍 루프"""
        logger.info("WebSocket 스트리밍 시작")
        
        while True:
            try:
                if not self.is_connected:
                    if not await self.reconnect():
                        await asyncio.sleep(5)
                        continue
                
                # 버퍼에서 오디오 데이터 가져오기
                audio_data = None
                async with self.buffer_lock:
                    if self.stream_buffer:
                        audio_data = self.stream_buffer.pop(0)
                
                if audio_data:
                    try:
                        await self.websocket.send(audio_data)
                        self.sent_frames += 1
                        
                        # 통계 로깅 (1000프레임마다)
                        if self.sent_frames % 1000 == 0:
                            logger.info(f"WebSocket 전송 프레임: {self.sent_frames}")
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket 연결이 닫힘")
                        self.is_connected = False
                    except Exception as e:
                        logger.error(f"WebSocket 전송 오류: {e}")
                        self.is_connected = False
                
                # 스트리밍 간격 유지
                await asyncio.sleep(self.streaming_interval)
                
            except asyncio.CancelledError:
                logger.info("WebSocket 스트리밍 태스크 취소됨")
                break
            except Exception as e:
                logger.error(f"스트리밍 루프 오류: {e}")
                await asyncio.sleep(1)
        
        await self.disconnect()

    async def start_streaming(self):
        """스트리밍 시작"""
        if not config.getboolean('options_using', 'websocket_streaming'):
            logger.info("WebSocket 스트리밍이 비활성화됨")
            return None
            
        # 초기 연결
        if await self.connect():
            # 스트리밍 태스크 시작
            streaming_task = asyncio.create_task(self.streaming_loop())
            logger.info("WebSocket 스트리밍 태스크 시작됨")
            return streaming_task
        else:
            logger.error("WebSocket 초기 연결 실패")
            return None

    def update_config(self, server_host=None, server_port=None, room_name=None, streaming_interval=None):
        """WebSocket 설정을 동적으로 업데이트"""
        updated = False
        
        if server_host and server_host != self.server_host:
            self.server_host = server_host
            updated = True
        
        if server_port and server_port != self.server_port:
            self.server_port = server_port
            updated = True
        
        if room_name and room_name != self.room_name:
            self.room_name = room_name
            updated = True
        
        if streaming_interval and streaming_interval != self.streaming_interval:
            self.streaming_interval = streaming_interval
            updated = True
        
        if updated:
            # WebSocket URL 재구성
            if self.server_host.startswith('https://'):
                protocol = 'wss'
                host = self.server_host.replace('https://', '')
            elif self.server_host.startswith('http://'):
                protocol = 'ws'
                host = self.server_host.replace('http://', '')
            else:
                protocol = 'ws'
                host = self.server_host
                
            if self.server_port == 0:
                self.ws_url = f"{protocol}://{host}/ws/room/{self.room_name}/{self.sample_rate}/int16/{self.device_id}"
            else:
                self.ws_url = f"{protocol}://{host}:{self.server_port}/ws/room/{self.room_name}/{self.sample_rate}/int16/{self.device_id}"
            logger.info(f"WebSocket 설정 업데이트됨: {self.ws_url}")
            
            # 연결되어 있다면 재연결 필요
            if self.is_connected:
                logger.info("설정 변경으로 인한 재연결 필요")
        
        return updated

    def get_statistics(self):
        """스트리밍 통계 반환"""
        return {
            "connected": self.is_connected,
            "sent_frames": self.sent_frames,
            "buffer_size": len(self.stream_buffer),
            "connection_retries": self.connection_retries
        }

# 전역 스트리머 인스턴스
_websocket_streamer = None

def get_websocket_streamer():
    """WebSocket 스트리머 싱글톤 인스턴스 반환"""
    global _websocket_streamer
    if _websocket_streamer is None:
        _websocket_streamer = WebSocketStreamer()
    return _websocket_streamer

async def start_websocket_streaming():
    """WebSocket 스트리밍 시작 (편의 함수)"""
    streamer = get_websocket_streamer()
    return await streamer.start_streaming()

async def stream_audio_data(audio_data: bytes):
    """오디오 데이터 스트리밍 (편의 함수)"""
    if config.getboolean('options_using', 'websocket_streaming'):
        streamer = get_websocket_streamer()
        await streamer.add_audio_data(audio_data) 