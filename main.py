# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json, re, textwrap
from typing import Dict, List

# OpenAI 패키지 로드
try:
    import openai
except Exception:
    openai = None

# .env에서 키 읽기
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# static 서빙
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ====== JSON 안전 로드 ======
def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"[Warn] File not found: {file_path}")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[Warn] JSON decode error: {file_path}")
        return {}

# ====== 지식베이스 초기화 (기본 구조만) ======
KB: Dict[str, Dict[str, dict]] = {
    "yacht": {},       # 나중에 Laser, 470 JSON 추가 가능
    "baseball": {},    # 나중에 JSON 추가
    "gymnastics": {},  # 나중에 JSON 추가
    "misc": {}         # 기타
}

# ====== 간단 토크나이저 & 검색 ======
def tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))
    return [t.lower() for t in tokens]

def score_doc_for_query(doc_text: str, query_tokens: List[str]) -> int:
    if not doc_text:
        return 0
    dtoks = tokenize(doc_text)
    s = 0
    dtokset = set(dtoks)
    for qt in query_tokens:
        if qt in dtokset:
            s += 2
        for dt in dtoks:
            if qt in dt:
                s += 1
    return s

def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = tokenize(query)
    hits = []
    if not domain_kb:
        return []
    for key, val in domain_kb.items():
        text = json.dumps(val, ensure_ascii=False) if isinstance(val, dict) else str(val)
        score = score_doc_for_query(text, qtokens)
        hits.append((score, key, val))
    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [{"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0][:top_k]

# ====== 로컬 답변 생성 ======
def local_synthesize_answer(query: str, retrieved: dict) -> str:
    parts = [f"질문: {query}\n"]
    for domain, hits in retrieved.items():
        if not hits:
            continue
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            snippet = json.dumps(h["doc"], ensure_ascii=False, indent=2) if isinstance(h["doc"], dict) else str(h["doc"])
            parts.append(f"[{h['key']}] (score {h['score']}):\n{snippet}\n")
    answer = "\n".join(parts)
    return textwrap.shorten(answer, width=3500, placeholder="\n\n…(생략)")

# ====== OpenAI 연동 답변 (선택) ======
def openai_generate(system_prompt: str, user_prompt: str):
    if openai is None:
        return "OpenAI 패키지가 설치되어 있지 않습니다."
    if not OPENAI_API_KEY:
        return "OpenAI API Key가 제공되지 않았습니다."
    openai.api_key = OPENAI_API_KEY
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"OpenAI 호출 오류: {str(e)}"

# ====== API 엔드포인트 ======
@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    query = data.get("query", "")
    use_openai = data.get("use_openai", False)

    # 로컬 검색
    retrieved = {domain: retrieve_relevant(KB.get(domain, {}), query) for domain in KB.keys()}
    local_answer = local_synthesize_answer(query, retrieved)

    if use_openai:
        system_prompt = "당신은 운동 전문가 AI입니다. 요트, 야구, 기계체조 지식을 활용하여 답변합니다."
        openai_answer = openai_generate(system_prompt, query)
        return JSONResponse({"answer": local_answer, "openai_answer": openai_answer})
    else:
        return JSONResponse({"answer": local_answer})

# ====== 기본 페이지 ======
@app.get("/")
async def index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Hello! 웹페이지 파일(index.html)이 없습니다."})
