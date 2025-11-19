#!/bin/bash

# 가상환경 활성화
source .venv/bin/activate

# PORT 환경변수 사용, 기본 8000
PORT=${PORT:-8000}

# uvicorn으로 FastAPI 실행
uvicorn main:app --host 0.0.0.0 --port $PORT --reload
