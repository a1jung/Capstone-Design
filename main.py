from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json

app = FastAPI()

# ====== Static 폴더 서빙 ======
app.mount("/static", StaticFiles(directory="static"), name="static")

# ====== JSON 로드 함수 ======
def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"[Warning] File not found: {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8-sig") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[Warning] JSON decode error: {file_path}")
            return {}

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
    yacht_class_lower = yacht_class.lower()
    if yacht_class_lower not in yacht_data:
        return JSONResponse({"error": "Yacht class not found"}, status_code=404)
    return JSONResponse(yacht_data[yacht_class_lower])

# ====== index.html 서빙 ======
@app.get("/")
async def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found"}, status_code=404)
