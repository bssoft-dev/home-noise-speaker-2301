#!/bin/bash
python3 app.py &> log.txt &
python3 file_monitor.py &> file_monitor.log &