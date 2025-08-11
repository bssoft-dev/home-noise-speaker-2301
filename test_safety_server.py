#!/usr/bin/env python3
"""
Safety Server 시뮬레이터
WebSocket 스트리밍 테스트용 (FastAPI 기반)
"""
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import time

# FastAPI 앱 생성
app = FastAPI(title="Safety Server Simulator")

# 방 관리
rooms = {}
connected_clients = {}

@app.post("/v1/create_room")
async def create_room(request: dict):
    room_name = request.get("room_name")
    if room_name:
        rooms[room_name] = {
            "created_at": time.time(),
            "clients": []
        }
        return {"message": f"Room '{room_name}' created successfully"}
    return {"error": "Invalid room name"}, 400

@app.get("/v1/rooms")
async def get_rooms():
    return {"rooms": list(rooms.keys())}

@app.get("/")
async def root():
    return {
        "message": "Safety Server Simulator",
        "rooms": len(rooms),
        "clients": len(connected_clients)
    }

# WebSocket 엔드포인트
@app.websocket("/ws/room/{room_name}/{sample_rate}/{dtype}/{device_id}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, sample_rate: int, dtype: str, device_id: str):
    await websocket.accept()
    print(f"✅ 클라이언트 연결: {device_id} -> 방: {room_name} (rate: {sample_rate}, type: {dtype})")
    
    # 클라이언트 등록
    client_info = {
        "device_id": device_id,
        "room_name": room_name,
        "sample_rate": sample_rate,
        "dtype": dtype,
        "connected_at": time.time(),
        "websocket": websocket
    }
    connected_clients[device_id] = client_info
    
    # 방에 클라이언트 추가
    if room_name not in rooms:
        rooms[room_name] = {"created_at": time.time(), "clients": []}
    rooms[room_name]["clients"].append(device_id)
    
    try:
        frame_count = 0
        bytes_received = 0
        start_time = time.time()
        
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_bytes()
            frame_count += 1
            bytes_received += len(data)
            
            # 통계 출력 (100프레임마다)
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                duration = frame_count * 0.064  # 64ms per frame
                rate = frame_count / elapsed if elapsed > 0 else 0
                print(f"[{device_id}] 📊 프레임: {frame_count}, 데이터: {bytes_received/1024:.1f}KB, 속도: {rate:.1f}fps")
            
            # 에코백 (테스트용 - 10프레임마다)
            if frame_count % 50 == 0:
                await websocket.send_bytes(data)
                
    except WebSocketDisconnect:
        print(f"❌ 클라이언트 연결 종료: {device_id}")
    except Exception as e:
        print(f"⚠️ WebSocket 오류 [{device_id}]: {e}")
    finally:
        # 클라이언트 정리
        if device_id in connected_clients:
            del connected_clients[device_id]
        
        if room_name in rooms and device_id in rooms[room_name]["clients"]:
            rooms[room_name]["clients"].remove(device_id)
            
        print(f"🧹 클라이언트 정리됨: {device_id}")

if __name__ == "__main__":
    print("🚀 Safety Server 시뮬레이터 시작 (FastAPI)")
    uvicorn.run(app, host="0.0.0.0", port=24015, log_level="info") 