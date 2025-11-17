#!/bin/bash
export OPENAI_API_KEY="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"
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
