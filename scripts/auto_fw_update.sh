#!/bin/bash

export SCRIPT_DIR="/home/bssoft/home-noise-speaker-2301/scripts"
cd $SCRIPT_DIR
export NOW_VER=`cat ../../version`
export RESPONSE=`curl https://home-therapy.bs-soft.co.kr/api/firmware/recent-ver | grep result`

if [ "$RESPONSE" != "" ]; then
    export TARGET_VER=`echo $RESPONSE | cut -d"\"" -f4 | sed 's/\.//g'`
    if [ "$NOW_VER" -lt "$TARGET_VER" ]; then
        echo "Update firmware"
        curl https://home-therapy.bs-soft.co.kr/api/firmware/update/$NOW_VER | bash &> log.txt
        cd $SCRIPT_DIR
        export RESULT=`tail -1 log.txt`
        if [ "$RESULT" = "ok" ]; then
            cat  <<EOF > ../../version 
$TARGET_VER
EOF
        fi
    else
        echo "No update"
    fi
fi
