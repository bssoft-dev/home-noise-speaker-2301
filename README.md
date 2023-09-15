# 층간소음 스트레스 저감 스마트 스피커

## 통신
서버 - 스피커 - 앱
1. 스피커와 앱은 내부 네트워크를 통해서만 연결 
2. 스마트폰 앱을 통해 스피커 제어
3. 추후 녹음 음원을 분석한 서버 결과를 통해 자동 재생 추가 예정

## 특징 (Version 1.0)
1. 2ch 마이크 및 스피커
2. 자동실행 - 기기 부팅 후 메인 프로그램 자동 실행
3. 내부 웹서버 - 브라우저로 스피커 페이지 접속
4. 새벽에 주기적으로 서버를 통해 원격 강제 업데이트
5. 버튼클릭시 AP 모드 구동, 해당 wifi에 접속하여 wifi 접속설정 가능

## 환경
- python 3.9

## bssoft 시작프로그램 등록
등록예시
~~~bash
sudo mkdir /boot/bssoft
sudo cp ./scripts/entrypoints.sh /boot/bssoft/
sudo cp ./scripts/init.d-script /etc/init.d/bssoft
cd /etc/init.d
sudo update-rc.d bssoft defaults
~~~

## 참고  
초기 WIFI ssid/pw 연결  
[wifi-connect](https://github.com/balena-os/wifi-connect) 이용
