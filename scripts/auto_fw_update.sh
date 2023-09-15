#!/bin/bash

export NOW_VER=`cat ../../version | sed 's/\.//g'`
export RESPONSE=`curl https://home-therapy.bs-soft.co.kr/api/firmware/recent-ver | grep result`

if [ "$RESPONSE" != "" ]; then
    export TARGET_VER=`echo $RESPONSE | cut -d"\"" -f4 | sed 's/\.//g'`
    if [ "$NOW_VER" -lt "$TARGET_VER" ]; then
        echo "Update firmware"
        curl https://home-therapy.bs-soft.co.kr/api/firmware/update/$NOW_VER | bash 
    else
        echo "No update"
    fi
fi
