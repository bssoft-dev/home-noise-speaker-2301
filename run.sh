#!/bin/bash
sudo python3 -m uvicorn app:app --host=0.0.0.0 --port=8080 &> log.txt &
