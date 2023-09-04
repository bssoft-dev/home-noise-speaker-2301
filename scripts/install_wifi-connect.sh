#!/bin/bash
export CURL_PKG=`dpkg -s curl`
export AARCH_NUM=`uname -m | rev | cut -c 1-2 | rev`
if [ "" = "$CURL_PKG" ]
then
  echo "Please install curl first"
else
  if [ $AARCH_NUM = "64" ]
  then
    curl -L https://github.com/balena-io/wifi-connect/raw/master/scripts/raspbian-install.sh | sed 's/\*rpi/*aarch64/' | bash
  else
    bash <(curl -L https://github.com/balena-io/wifi-connect/raw/master/scripts/raspbian-install.sh)
  fi
fi