#!/bin/bash
sudo apt-get install -y git python3-pip libportaudio2 libasound2 libasound2-dev python3-pyaudio

# sound card driver setup
git clone https://github.com/waveshare/WM8960-Audio-HAT
cd WM8960-Audio-HAT
sudo ./install.sh 
echo "Reboot after 10 seconds"
for ((i=10;i>=0;i--))
do
  echo $i...
  sleep 1
done
sudo reboot now