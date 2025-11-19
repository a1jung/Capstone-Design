#!/bin/bash
export $(cat .env | xargs)  # .env 읽기
uvicorn main:app --host 0.0.0.0 --port $PORT
