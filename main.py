import os, json, re, textwrap
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

try:
    import openai
except:
    openai = None

app = FastAPI()

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Knowledge Base
KB: Dict[str, Dict[str, dict]] = {}

for domain in ["yacht", "baseball", "gymnastics"]:
    domain_path = os.path.join(BASE_DIR, domain)
    KB[domain] = {}

    for root, _, files in os.walk(domain_path):
        for fname in files:
            if fname.lower().endswith(".json"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        key = os.path.relpath(fpath, domain_path)
                        KB[domain][key] = json.load(f)
                except:
                    print(f"[Warn] JSON decode error: {fpath}")

# Tokenizer
def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))] if text else []

# 한글 → 영어 확장 사전
synonyms = {
    "요트": ["yacht", "boat", "sailing", "laser", "470"],
    "기계체조": ["gymnastics"],
    "체조": ["gymnastics"],
    "야구": ["baseball"],
    "투수": ["pitcher"],
    "포수": ["catcher"],
    "내야수": ["infielder"],
    "외야수": ["outfielder"]
}

def expand_query_tokens(qtokens):
    expanded = set(qtokens)
    for qt in qtokens:
        if qt in synonyms:
            for syn in synonyms[qt]:
                expanded.add(syn.lower())
    return list(expanded)

def score_doc_for_query(doc_text: str, query_tokens: List[str]) -> int:
    dtoks = tokenize(doc_text)
    dtokset = set(dtoks)
    s = 0
    for qt in query_tokens:
        if qt in dtokset: s += 2
        for dt in dtoks:
            if qt in dt: s += 1
    return s

def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = expand_query_tokens(tokenize(query))  # 변경 부분!
    hits = []
    for key, val in domain_kb.items():
        text = json.dumps(val, ensure_ascii=False)
        score = score_doc_for_query(text, qtokens)
        hits.append((score, key, val))
    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [{"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0][:top_k]

def local_synthesize_answer(query: str, retrieved: dict) -> str:
    parts = [f"질문: {query}\n"]
    found = False
    for domain, hits in retrieved.items():
        if not hits: continue
        found = True
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            snippet = json.dumps(h["doc"], ensure_ascii=False, indent=2)
            parts.append(f"[{h['key']}] (score {h['score']}):\n{snippet}\n")
    if not found:
        return "죄송합니다, 관련 정보를 찾을 수 없습니다."
    return textwrap.shorten("\n".join(parts), width=3000, placeholder="\n\n…(생략)")

@app.get("/")
async def home():
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "index.html not found"}

@app.post("/query")
async def query_ai(req: Request):
    data = await req.json()
    question = data.get("question", "")
    if not question:
        return JSONResponse({"answer": "질문을 입력해주세요."})

    retrieved = {domain: retrieve_relevant(kb, question) for domain, kb in KB.items()}
    answer = local_synthesize_answer(question, retrieved)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        system_prompt = "Capstone 전문가 AI 답변"
        ai, err = openai_generate(system_prompt, answer, api_key, 450)
        if ai: answer = ai

    return JSONResponse({"answer": answer})
