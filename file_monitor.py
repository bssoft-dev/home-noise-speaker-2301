#!/usr/bin/env python3
"""
record_sounds 폴더 파일 변화 모니터링 스크립트
새 파일 생성, 파일 수정, 파일 삭제를 감지하여 로그로 출력
"""
import os
import time
import logging
import requests
import random
import configparser
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import defaultdict
from supabase import create_client, Client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('file_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """config.ini 파일에서 설정 로드"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
        logger.info(f"✅ 설정 파일 로드 성공: {config_file}")
        return config
    else:
        logger.error(f"❌ 설정 파일을 찾을 수 없습니다: {config_file}")
        return None

class RecordFileHandler(FileSystemEventHandler):
    """record_sounds 폴더의 파일 변화를 처리하는 핸들러"""
    
    def __init__(self, watch_path):
        self.watch_path = watch_path
        self.file_sizes = {}  # 파일 크기 추적
        self.file_timestamps = {}  # 파일 타임스탬프 추적
        self.pending_changes = defaultdict(dict)  # 대기 중인 변화들
        self.debounce_time = 0.5  # 디바운스 시간 (초)
        self.api_url = "http://api-2424.bs-soft.co.kr/predict"
        self.app_server_url = "http://localhost"  # app.py 서버 URL
        self.sound_dir = "./sounds"  # ready 음원 폴더
        
        # 설정 파일 로드
        self.config = load_config()
        
        # Supabase 설정 (환경변수 우선, 설정 파일 차선)
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        # 환경변수가 없으면 설정 파일에서 로드
        if not self.supabase_url or not self.supabase_key:
            if self.config and 'supabase' in self.config:
                self.supabase_url = self.config.get('supabase', 'url', fallback='your-supabase-url')
                self.supabase_key = self.config.get('supabase', 'key', fallback='your-supabase-key')
                logger.info("📋 Supabase 설정을 config.ini에서 로드했습니다")
            else:
                self.supabase_url = 'your-supabase-url'
                self.supabase_key = 'your-supabase-key'
                logger.warning("⚠️ Supabase 설정을 찾을 수 없습니다")
        
        self.supabase: Client = None
        
        # Supabase 클라이언트 초기화
        self._init_supabase()
        
        logger.info(f"파일 모니터링 시작: {watch_path}")
        logger.info(f"API 엔드포인트: {self.api_url}")
        logger.info(f"앱 서버 URL: {self.app_server_url}")
        logger.info(f"Supabase URL: {self.supabase_url}")
    
    def _init_supabase(self):
        """Supabase 클라이언트 초기화"""
        try:
            if self.supabase_url != 'your-supabase-url' and self.supabase_key != 'your-supabase-key':
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ Supabase 클라이언트 초기화 성공")
            else:
                logger.warning("⚠️ Supabase 설정이 없습니다. config.ini 또는 환경변수를 설정해주세요.")
        except Exception as e:
            logger.error(f"❌ Supabase 초기화 실패: {str(e)}")
    
    def _load_sound_settings(self):
        """Supabase에서 음원 설정 로드 (실시간)"""
        try:
            if not self.supabase:
                logger.warning("⚠️ Supabase 클라이언트가 초기화되지 않았습니다")
                return {}
            
            logger.debug("📋 Supabase에서 음원 설정 실시간 로드 중...")
            
            # noise_level_settings 테이블에서 설정 가져오기
            response = self.supabase.table('noise_level_settings').select('*').execute()
            
            sound_settings = {}
            if response.data:
                for setting in response.data:
                    noise_level = setting.get('noise_level')
                    sound_type = setting.get('sound_type')
                    sound_files = setting.get('sound_files', [])
                    enabled = setting.get('enabled', True)
                    
                    if enabled and sound_files:
                        # 같은 노이즈 레벨에 여러 설정이 있을 수 있으므로 리스트로 관리
                        if noise_level not in sound_settings:
                            sound_settings[noise_level] = []
                        
                        sound_settings[noise_level].append({
                            'sound_type': sound_type,
                            'sound_files': sound_files
                        })
                        logger.debug(f"   📊 {noise_level}: {sound_type} ({len(sound_files)}개 파일)")
                
                logger.debug(f"✅ 실시간 음원 설정 로드 완료 ({len(sound_settings)}개 레벨)")
            else:
                logger.warning("⚠️ Supabase에서 설정을 찾을 수 없습니다")
            
            return sound_settings
                
        except Exception as e:
            logger.error(f"❌ 음원 설정 로드 실패: {str(e)}")
            return {}
    
    def get_sound_for_noise_level(self, noise_level, noise_type):
        """소음 레벨에 따른 음원 선택 (실시간 DB 체크)"""
        try:
            # 매번 실시간으로 설정 로드
            sound_settings = self._load_sound_settings()
            
            if not sound_settings:
                logger.warning("⚠️ 음원 설정이 없습니다. 재생하지 않습니다.")
                return None
            
            # 해당 레벨의 설정 확인
            if noise_level not in sound_settings:
                logger.warning(f"⚠️ {noise_level} 레벨에 대한 설정이 없습니다. 재생하지 않습니다.")
                return None
            
            logger.info(f"🔍 음원 설정: {sound_settings}")
            
            # 해당 레벨의 모든 설정 가져오기
            level_settings = sound_settings[noise_level]
            
            if not level_settings:
                logger.warning(f"⚠️ {noise_level} 레벨에 설정된 음원이 없습니다. 재생하지 않습니다.")
                return None
            
            # 여러 설정 중 sound_type이 noise_type과 일치하는 설정 선택
            selected_setting = next((setting for setting in level_settings if setting['sound_type'] == noise_type), None)
            
            # 일치하는 설정이 없는 경우 처리
            if selected_setting is None:
                logger.warning(f"⚠️ {noise_level} 레벨에서 '{noise_type}' 유형의 설정을 찾을 수 없습니다.")
                logger.info(f"   📋 사용 가능한 유형: {[setting['sound_type'] for setting in level_settings]}")
                return None
            
            sound_files = selected_setting['sound_files']
            
            if not sound_files:
                logger.warning(f"⚠️ {noise_level} 레벨에 설정된 음원이 없습니다. 재생하지 않습니다.")
                return None
            
            # 설정된 음원 중에서 랜덤 선택
            selected_file = random.choice(sound_files)
            
            # 파일이 실제로 존재하는지 확인
            if not os.path.exists(os.path.join(self.sound_dir, selected_file)):
                logger.warning(f"⚠️ 설정된 음원 파일이 존재하지 않습니다: {selected_file}. 재생하지 않습니다.")
                return None
            
            logger.info(f"🎵 {noise_level} 레벨 음원 선택: {selected_file} ({selected_setting['sound_type']})")
            return selected_file
            
        except Exception as e:
            logger.error(f"❌ 음원 선택 중 오류: {str(e)}")
            return None
    
    def get_random_sound_file(self):
        """sounds 폴더에서 랜덤 음원 파일 선택"""
        try:
            if not os.path.exists(self.sound_dir):
                logger.warning(f"⚠️ sounds 폴더가 존재하지 않습니다: {self.sound_dir}")
                return None
            
            # WAV 파일만 필터링
            sound_files = [f for f in os.listdir(self.sound_dir) if f.endswith('.wav')]
            
            if not sound_files:
                logger.warning(f"⚠️ sounds 폴더에 WAV 파일이 없습니다: {self.sound_dir}")
                return None
            
            # 랜덤 선택
            selected_file = random.choice(sound_files)
            logger.info(f"🎵 선택된 랜덤 음원: {selected_file}")
            return selected_file
            
        except Exception as e:
            logger.error(f"❌ 랜덤 음원 선택 오류: {str(e)}")
            return None
    
    def play_warning_sound(self, filename, noise_level, noise_type):
        """경고 음원 재생"""
        try:
            # 소음 레벨에 따른 음원 선택
            sound_file = self.get_sound_for_noise_level(noise_level, noise_type)
            if not sound_file:
                logger.warning("⚠️ 재생할 음원을 찾을 수 없습니다. 재생하지 않습니다.")
                return False
            
            # 먼저 기존 재생 정지
            stop_url = f"{self.app_server_url}/control/stop"
            logger.info(f"🛑 기존 재생 정지 요청")
            logger.info(f"   📡 URL: {stop_url}")
            
            try:
                stop_response = requests.get(stop_url, timeout=5)
                if stop_response.status_code == 200:
                    logger.info("✅ 기존 재생 정지 성공")
                else:
                    logger.warning(f"⚠️ 기존 재생 정지 실패 (상태코드: {stop_response.status_code})")
            except Exception as e:
                logger.warning(f"⚠️ 기존 재생 정지 중 오류: {str(e)}")
            
            # 잠시 대기 (정지 처리 시간)
            time.sleep(0.5)
            
            # 새로운 음원 재생
            play_url = f"{self.app_server_url}/control/play/ready/{sound_file}"
            
            logger.info(f"🔊 {noise_level} 레벨 음원 재생 시작: {sound_file}")
            logger.info(f"   📡 URL: {play_url}")
            
            response = requests.get(play_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ {noise_level} 레벨 음원 재생 성공: {sound_file}")
                return True
            else:
                logger.warning(f"❌ {noise_level} 레벨 음원 재생 실패: {sound_file} (상태코드: {response.status_code})")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ {noise_level} 레벨 음원 재생 타임아웃")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 app.py 서버 연결 실패")
            return False
        except Exception as e:
            logger.error(f"❌ {noise_level} 레벨 음원 재생 오류: {str(e)}")
            return False
    
    def send_file_to_api(self, file_path):
        """파일을 API로 전송하고 결과 반환"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "파일이 존재하지 않습니다"}
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {"success": False, "error": "파일 크기가 0입니다"}
            
            # 파일을 multipart/form-data로 전송
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'audio/wav')}
                
                logger.info(f"📤 API 전송 시작: {os.path.basename(file_path)} ({file_size:,} bytes)")
                
                response = requests.post(
                    self.api_url,
                    files=files,
                    timeout=30  # 30초 타임아웃
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"✅ API 응답 성공: {os.path.basename(file_path)}")
                        return {"success": True, "result": result, "status_code": response.status_code}
                    except ValueError:
                        # JSON이 아닌 경우 텍스트로 처리
                        logger.info(f"✅ API 응답 성공 (텍스트): {os.path.basename(file_path)}")
                        return {"success": True, "result": response.text, "status_code": response.status_code}
                else:
                    logger.warning(f"❌ API 응답 실패: {os.path.basename(file_path)} (상태코드: {response.status_code})")
                    return {"success": False, "error": f"HTTP {response.status_code}", "status_code": response.status_code}
                    
        except requests.exceptions.Timeout:
            logger.error(f"⏰ API 전송 타임아웃: {os.path.basename(file_path)}")
            return {"success": False, "error": "타임아웃"}
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 API 연결 실패: {os.path.basename(file_path)}")
            return {"success": False, "error": "연결 실패"}
        except Exception as e:
            logger.error(f"❌ API 전송 오류: {os.path.basename(file_path)} - {str(e)}")
            return {"success": False, "error": str(e)}
    
    def on_created(self, event):
        """새 파일 생성 감지"""
        if not event.is_directory and event.src_path.endswith('.wav'):
            file_path = event.src_path
            file_size = os.path.getsize(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            logger.info("=" * 60)
            logger.info(f"🆕 [새 파일 생성] {os.path.basename(file_path)}")
            logger.info(f"   📁 경로: {file_path}")
            logger.info(f"   📊 크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            logger.info(f"   ⏰ 생성 시간: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            # 파일 정보 추적에 추가
            self.file_sizes[file_path] = file_size
            self.file_timestamps[file_path] = file_time
            
            # API 전송 (새 파일 생성 시)
            if file_size > 0:
                api_result = self.send_file_to_api(file_path)
                self._log_api_result(api_result, os.path.basename(file_path))
    
    def on_modified(self, event):
        """파일 수정 감지"""
        if not event.is_directory and event.src_path.endswith('.wav'):
            file_path = event.src_path
            current_size = os.path.getsize(file_path)
            current_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # 이전 정보와 비교
            previous_size = self.file_sizes.get(file_path, 0)
            previous_time = self.file_timestamps.get(file_path)
            size_change = current_size - previous_size
            
            if size_change != 0:  # 크기가 실제로 변경된 경우만 처리
                # 변화 정보 저장
                change_info = {
                    'file_path': file_path,
                    'previous_size': previous_size,
                    'current_size': current_size,
                    'size_change': size_change,
                    'current_time': current_time,
                    'previous_time': previous_time,
                    'timestamp': time.time()
                }
                
                # 대기 중인 변화 업데이트
                self.pending_changes[file_path] = change_info
                
                # 디바운스 타이머 설정
                self._schedule_change_log(file_path)
                
                # 파일 정보 추적 업데이트
                self.file_sizes[file_path] = current_size
                self.file_timestamps[file_path] = current_time
    
    def _schedule_change_log(self, file_path):
        """변화 로그 출력을 스케줄링"""
        import threading
        
        def delayed_log():
            time.sleep(self.debounce_time)
            if file_path in self.pending_changes:
                change_info = self.pending_changes.pop(file_path)
                self._log_file_change(change_info)
        
        thread = threading.Timer(self.debounce_time, delayed_log)
        thread.daemon = True
        thread.start()
    
    def _log_file_change(self, change_info):
        """파일 변화 로그 출력"""
        file_path = change_info['file_path']
        previous_size = change_info['previous_size']
        current_size = change_info['current_size']
        size_change = change_info['size_change']
        current_time = change_info['current_time']
        previous_time = change_info['previous_time']
        
        # 변화 유형 판단
        if current_size == 0:
            change_type = "🔄 [파일 초기화]"
        elif previous_size == 0:
            change_type = "📝 [파일 작성 완료]"
        elif size_change > 0:
            change_type = "📈 [파일 확장]"
        else:
            change_type = "📉 [파일 축소]"
        
        logger.info("-" * 50)
        logger.info(f"{change_type} {os.path.basename(file_path)}")
        logger.info(f"   📁 경로: {file_path}")
        logger.info(f"   📊 크기 변화: {previous_size:,} → {current_size:,} bytes")
        logger.info(f"   📈 변화량: {size_change:+,} bytes ({size_change/1024:+.1f} KB)")
        logger.info(f"   ⏰ 수정 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if previous_time:
            time_diff = (current_time - previous_time).total_seconds()
            if time_diff > 0.1:  # 0.1초 이상 차이가 나는 경우만 표시
                logger.info(f"   ⏱️  마지막 수정 후: {time_diff:.1f}초")
        
        logger.info("-" * 50)
        
        # 파일이 완성되었을 때만 API 전송 (파일 작성 완료 또는 파일 확장으로 최종 크기에 도달)
        if (change_type == "📝 [파일 작성 완료]" or 
            (change_type == "📈 [파일 확장]")):  # 300KB 이상일 때
            api_result = self.send_file_to_api(file_path)
            self._log_api_result(api_result, os.path.basename(file_path))
    
    def _log_api_result(self, api_result, filename):
        """API 결과 로그 출력"""
        logger.info("🔍 API 분석 결과:")
        
        if api_result["success"]:
            result = api_result["result"]
            logger.info(f"   📄 파일: {filename}")
            logger.info(f"   ✅ 상태: 성공")
            
            # 결과 타입에 따라 다르게 출력
            if isinstance(result, dict):
                for key, value in result.items():
                    logger.info(f"   📊 {key}: {value}")
                
                # noise_level과 noise_type 모두 검토
                noise_level = result.get('noise_level')
                noise_type = result.get('noise_type')
                
                logger.info("🔍 소음 분석 결과 검토:")
                logger.info(f"   📊 소음 레벨: {noise_level}")
                logger.info(f"   📊 소음 유형: {noise_type}")
                
                # 소음 레벨과 유형에 따른 음원 재생 결정
                if noise_level and noise_type:
                    logger.info(f"🚨 소음 감지! 레벨: {noise_level}, 유형: {noise_type}")
                    
                    # 설정값이 있는지 확인
                    sound_settings = self._load_sound_settings()
                    if noise_level in sound_settings:
                        logger.info("🎵 단계별 음원 재생 시작...")
                        self.play_warning_sound(filename, noise_level, noise_type)
                    else:
                        logger.info(f"⚠️ {noise_level} 레벨에 대한 설정이 없습니다. 재생하지 않습니다.")
                        
                elif noise_level:
                    logger.info(f"🚨 소음 레벨 감지: {noise_level}")
                    logger.info(f" 소음 레벨만 감지되었습니다. 유형 설정이 필요합니다. 재생하지 않습니다.")
                    
                        
                elif noise_type:
                    logger.info(f"🚨 소음 유형 감지: {noise_type}")
                    logger.info("⚠️ 소음 유형만 감지되었습니다. 레벨 설정이 필요합니다. 재생하지 않습니다.")
                else:
                    logger.info("ℹ️ 소음 레벨 또는 유형이 감지되지 않았습니다")
            else:
                logger.info(f"   📊 결과: {result}")
        else:
            logger.info(f"   📄 파일: {filename}")
            logger.info(f"   ❌ 상태: 실패")
            logger.info(f"   🚫 오류: {api_result['error']}")
        
        logger.info("-" * 30)
    
    def on_deleted(self, event):
        """파일 삭제 감지"""
        if not event.is_directory and event.src_path.endswith('.wav'):
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            
            # 대기 중인 변화 제거
            if file_path in self.pending_changes:
                del self.pending_changes[file_path]
            
            logger.info("=" * 60)
            logger.info(f"🗑️ [파일 삭제] {file_name}")
            logger.info(f"   📁 경로: {file_path}")
            logger.info(f"   ⏰ 삭제 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            # 파일 정보 추적에서 제거
            if file_path in self.file_sizes:
                del self.file_sizes[file_path]
            if file_path in self.file_timestamps:
                del self.file_timestamps[file_path]
    
    def on_moved(self, event):
        """파일 이동/이름 변경 감지"""
        if not event.is_directory and (event.src_path.endswith('.wav') or event.dest_path.endswith('.wav')):
            old_name = os.path.basename(event.src_path)
            new_name = os.path.basename(event.dest_path)
            
            # 대기 중인 변화 업데이트
            if event.src_path in self.pending_changes:
                change_info = self.pending_changes.pop(event.src_path)
                change_info['file_path'] = event.dest_path
                self.pending_changes[event.dest_path] = change_info
            
            logger.info("=" * 60)
            logger.info(f"🔄 [파일 이동/이름 변경]")
            logger.info(f"   📁 이전 이름: {old_name}")
            logger.info(f"   📁 새 이름: {new_name}")
            logger.info(f"   📂 이전 경로: {event.src_path}")
            logger.info(f"   📂 새 경로: {event.dest_path}")
            logger.info(f"   ⏰ 변경 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            # 파일 정보 추적 업데이트
            if event.src_path in self.file_sizes:
                size = self.file_sizes.pop(event.src_path)
                self.file_sizes[event.dest_path] = size
            if event.src_path in self.file_timestamps:
                timestamp = self.file_timestamps.pop(event.src_path)
                self.file_timestamps[event.dest_path] = timestamp

def get_current_files(watch_path):
    """현재 폴더의 모든 WAV 파일 정보 출력"""
    logger.info("=" * 60)
    logger.info(f"📋 [현재 파일 목록] {watch_path} 폴더")
    logger.info("=" * 60)
    
    if not os.path.exists(watch_path):
        logger.warning(f"⚠️ 폴더가 존재하지 않습니다: {watch_path}")
        return {}
    
    files = {}
    file_count = 0
    
    for file_name in sorted(os.listdir(watch_path)):
        if file_name.endswith('.wav'):
            file_path = os.path.join(watch_path, file_name)
            file_size = os.path.getsize(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            logger.info(f"   📄 {file_name}")
            logger.info(f"      📊 크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            logger.info(f"      ⏰ 수정: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("")
            
            files[file_path] = file_size
            file_count += 1
    
    logger.info(f"📊 총 {file_count}개의 WAV 파일이 발견되었습니다.")
    logger.info("=" * 60)
    
    return files

def main():
    """메인 함수"""
    # 모니터링할 폴더 경로
    watch_path = "./record_sounds"
    
    print("🎵 record_sounds 폴더 파일 모니터링 시작")
    print("=" * 60)
    print("📡 변화 유형:")
    print("   🆕 새 파일 생성")
    print("   📝 파일 수정 (작성 완료)")
    print("   🔄 파일 초기화")
    print("   📈 파일 확장")
    print("   📉 파일 축소")
    print("   🗑️ 파일 삭제")
    print("   🔄 파일 이동/이름 변경")
    print("")
    print("💡 연속 변화는 0.5초 후 마지막 변화만 출력됩니다")
    print("🔍 파일 완성 시 API로 자동 전송 및 분석 결과 출력")
    print("🚨 noise_level이 '경고'일 경우 랜덤 음원 자동 재생")
    print("=" * 60)
    
    # 현재 파일 목록 출력
    current_files = get_current_files(watch_path)
    
    # 파일 시스템 이벤트 핸들러 생성
    event_handler = RecordFileHandler(watch_path)
    event_handler.file_sizes = current_files  # 현재 파일 크기 정보 설정
    
    # Observer 생성 및 시작
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()
    
    try:
        logger.info("🚀 파일 모니터링이 시작되었습니다. Ctrl+C로 종료하세요.")
        print("📡 실시간 파일 변화 감지 중...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 모니터링이 중단되었습니다.")
        print("\n🛑 모니터링 종료")
        
    finally:
        observer.stop()
        observer.join()
        logger.info("🏁 파일 모니터링이 종료되었습니다.")

if __name__ == "__main__":
    main() 