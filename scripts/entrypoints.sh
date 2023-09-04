#!/bin/bash

if [ $1 = "start" ]
then
  cd /home/bssoft/home-noise-speaker-2301
  ./run.sh
else
  pkill python3