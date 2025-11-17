from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
import os, json

app = FastAPI()

# ====== JSON 로드 함수 ======
def load_json(file_path):
    """파일 없거나 비어있으면 빈 dict 반환, 에러 로그 출력"""
    if not os.path.exists(file_path):
        print(f"[Warning] File not found: {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8-sig") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[Warning] JSON decode error: {file_path}")
            return {}

# ====== JSON 경로 생성 함수 ======
def get_json_path(*args):
    return os.path.join(*args)

# ====== 요트 데이터 로드 ======
yacht_data = {
    "laser": load_json(get_json_path("yacht", "Laser", "description.json")),
    "470": load_json(get_json_path("yacht", "470", "description.json"))
}

# ====== API 엔드포인트 ======
@app.get("/api/yacht/{yacht_class}")
async def get_yacht(yacht_class: str):
    yacht_class = yacht_class.lower()
    if yacht_class not in yacht_data:
        return JSONResponse({"error": "Yacht class not found"}, status_code=404)
    return JSONResponse(yacht_data[yacht_class])

# ====== static 파일 서빙 ======
@app.get("/")
async def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found"}, status_code=404)
