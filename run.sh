#!/bin/bash
python3 -m uvicorn app:app --reload --host=0.0.0.0 --port=8080 &> log.txt &
