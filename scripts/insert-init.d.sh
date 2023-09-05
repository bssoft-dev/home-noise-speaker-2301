#!/bin/bash
# Register init.d-script as a service named bssoft

# Check sudo permission
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

cp init.d-script /etc/init.d/bssoft
cd /etc/init.d
chmod +x bssoft
update-rc.d bssoft defaults
