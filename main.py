import os, json, re, textwrap
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# OpenAI optional
try:
    import openai
except:
    openai = None

app = FastAPI()

# ====== 경로 설정 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# static 서빙
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ====== KB 로드 ======
KB: Dict[str, Dict[str, dict]] = {}
for domain in ["yacht", "baseball", "gymnastics"]:
    domain_path = os.path.join(BASE_DIR, domain)
    if os.path.exists(domain_path):
        KB[domain] = {}
        for fname in os.listdir(domain_path):
            if fname.lower().endswith(".json"):
                fpath = os.path.join(domain_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        KB[domain][fname] = json.load(f)
                except:
                    print(f"[Warn] JSON decode error: {fpath}")

# ====== 토크나이저 & 검색 ======
def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))] if text else []

def score_doc_for_query(doc_text: str, query_tokens: List[str]) -> int:
    dtoks = tokenize(doc_text)
    s = 0
    dtokset = set(dtoks)
    for qt in query_tokens:
        if qt in dtokset: s += 2
        for dt in dtoks:
            if qt in dt: s += 1
    return s

def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = tokenize(query)
    hits = []
    for key, val in domain_kb.items():
        text = json.dumps(val, ensure_ascii=False) if isinstance(val, dict) else str(val)
        score = score_doc_for_query(text, qtokens)
        hits.append((score, key, val))
    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [{"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0][:top_k]

def local_synthesize_answer(query: str, retrieved: dict) -> str:
    parts = [f"질문: {query}\n"]
    for domain, hits in retrieved.items():
        if not hits: continue
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            snippet = json.dumps(h["doc"], ensure_ascii=False, indent=2) if isinstance(h["doc"], dict) else str(h["doc"])
            parts.append(f"[{h['key']}] (score {h['score']}):\n{snippet}\n")
    return textwrap.shorten("\n".join(parts), width=3500, placeholder="\n\n…(생략)")

# ====== OpenAI 호출 (선택) ======
def openai_generate(system_prompt: str, user_prompt: str, api_key: str, max_tokens=512):
    if not openai or not api_key: return None, "OpenAI 미사용"
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)

# ====== FastAPI 엔드포인트 ======
@app.get("/")
async def home():
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "index.html not found"}

@app.post("/query")
async def query_ai(req: Request):
    data = await req.json()
    question = data.get("question", "").strip()
    if not question: return JSONResponse({"answer": "질문을 입력해주세요."})

    retrieved = {domain: retrieve_relevant(kb, question) for domain, kb in KB.items()}
    answer = local_synthesize_answer(question, retrieved)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        system_prompt = "당신은 Capstone-Design 전문가 AI입니다. 질문에 대해 최대한 정확하고 이해하기 쉽게 답하세요."
        gpt_answer, err = openai_generate(system_prompt, answer, api_key, max_tokens=400)
        if gpt_answer: answer = gpt_answer

    return JSONResponse({"answer": answer})
