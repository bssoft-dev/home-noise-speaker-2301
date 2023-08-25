# 층간소음 스트레스 저감 스마트 스피커

## 통신
랜선 혹은 WIFI 연결
1. 오디오 분석 <디바이스> -> <머신러닝 서버 분석> -> <결과 전달(디바이스)>
1. 연결상태 전송(주기), 이벤트 알림(비주기) <디바이스> -> <비상벨 대시보드 서버>

## 특징 (Version 0.1)
1. 자동실행 - 기기 부팅 후 메인 프로그램과 모니터링 프로그램 자동 실행
1. 사용자 설정 - /mount2/bssoft/ 폴더의 id.txt와 config.txt를 이용하여 기기 아이디와 각종 설정 변경 가능
(id.txt 파일이 있으면 해당 파일 내 텍스트를 deviceId로 인식하며, 파일이 없으면 unix time 기반으로 아이디를 만들고 id.txt를 생성함)
1. 내부 웹서버 - 브라우저로 스피커 페이지 접속
1. 6ch 마이크 및 고성능 스피커

## 환경
- python 3.7

## 실행(HW 접근을 위해 sudo 사용)
- sudo python3 app.py

## 참고  
초기 WIFI ssid/pw 연결  
[wifi-connect](https://github.com/balena-os/wifi-connect) 이용