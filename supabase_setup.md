# Supabase 설정 가이드

## 1. Supabase 프로젝트 설정

### 1.1 환경변수 설정
```bash
export SUPABASE_URL="https://supastudio.bs-soft.co.kr"
export SUPABASE_KEY="const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogImFub24iLAogICJpc3MiOiAic3VwYWJhc2UiLAogICJpYXQiOiAxNzAxMzU2NDAwLAogICJleHAiOiAxODU5MjA5MjAwCn0.qCMiad61me4LQAJgm-n4jUsvXHhgVN0TtkWDw1ht0UA"
```

### 1.2 테이블 구조

#### noise_level_settings 테이블
```sql
CREATE TABLE noise_level_settings (
    id SERIAL PRIMARY KEY,
    noise_level VARCHAR(20) NOT NULL,  -- '주의', '경고', '위험' 등
    sound_type VARCHAR(50) NOT NULL,   -- '자연음', '노이즈', '음악' 등
    sound_files TEXT[] NOT NULL,       -- 음원 파일명 배열
    enabled BOOLEAN DEFAULT true,      -- 활성화 여부
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.3 샘플 데이터
```sql
-- 주의 레벨: 새소리, 비소리 등 자연음
INSERT INTO noise_level_settings (noise_level, sound_type, sound_files) VALUES 
('주의', '자연음', ARRAY['새소리1.wav', '새소리2.wav', '새소리3.wav', '비소리1.wav', '비소리2.wav']);

-- 경고 레벨: 폭포소리, 계곡물소리 등 강한 자연음
INSERT INTO noise_level_settings (noise_level, sound_type, sound_files) VALUES 
('경고', '강한자연음', ARRAY['폭포소리1.wav', '폭포소리2.wav', '계곡물소리1.wav', '계곡물소리2.wav']);

-- 위험 레벨: 화이트 노이즈, 핑크 노이즈 등 노이즈
INSERT INTO noise_level_settings (noise_level, sound_type, sound_files) VALUES 
('위험', '노이즈', ARRAY['화이트 노이즈.wav', '핑크 노이즈.wav', '브라운 노이즈.wav']);
```

## 2. 시스템 동작 방식

### 2.1 음원 선택 로직
1. **Supabase 설정 확인**: noise_level_settings 테이블에서 해당 레벨의 설정 조회
2. **음원 선택**: 설정된 음원 파일 중에서 랜덤 선택
3. **파일 존재 확인**: 선택된 음원이 실제로 sounds 폴더에 존재하는지 확인
4. **폴백 처리**: 설정이 없거나 파일이 없으면 기본 랜덤 선택

### 2.2 캐시 시스템
- **캐시 시간**: 5분 (300초)
- **자동 새로고침**: 설정 변경 시 자동으로 반영
- **성능 최적화**: 불필요한 DB 조회 방지

### 2.3 로그 출력 예시
```
📋 Supabase에서 음원 설정 로드 중...
   📊 주의: 자연음 (5개 파일)
   📊 경고: 강한자연음 (4개 파일)
   📊 위험: 노이즈 (3개 파일)
✅ 음원 설정 로드 완료 (3개 레벨)

🎵 경고 레벨 음원 선택: 폭포소리1.wav (강한자연음)
🔊 경고 레벨 음원 재생 시작: 폭포소리1.wav
```

## 3. 관리 방법

### 3.1 설정 추가
```sql
INSERT INTO noise_level_settings (noise_level, sound_type, sound_files) VALUES 
('새로운레벨', '새로운타입', ARRAY['음원1.wav', '음원2.wav']);
```

### 3.2 설정 수정
```sql
UPDATE noise_level_settings 
SET sound_files = ARRAY['새음원1.wav', '새음원2.wav']
WHERE noise_level = '경고';
```

### 3.3 설정 비활성화
```sql
UPDATE noise_level_settings 
SET enabled = false
WHERE noise_level = '위험';
```

## 4. 파일 구조
```
sounds/
├── 새소리1.wav
├── 새소리2.wav
├── 새소리3.wav
├── 비소리1.wav
├── 비소리2.wav
├── 폭포소리1.wav
├── 폭포소리2.wav
├── 계곡물소리1.wav
├── 계곡물소리2.wav
├── 화이트 노이즈.wav
├── 핑크 노이즈.wav
└── 브라운 노이즈.wav
```

## 5. 오류 처리

### 5.1 Supabase 연결 실패
- 기본 랜덤 선택으로 폴백
- 로그에 오류 메시지 출력

### 5.2 설정 없음
- 해당 레벨에 설정이 없으면 기본 랜덤 선택
- 경고 메시지 출력

### 5.3 파일 없음
- 설정된 음원 파일이 실제로 없으면 기본 랜덤 선택
- 경고 메시지 출력 