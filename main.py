from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json, re, textwrap

# Optional OpenAI
try:
    import openai
except:
    openai = None

app = FastAPI()

# static 폴더 서빙
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== 유틸: JSON 안전 로드 =====
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

# ===== 지식베이스 로드 =====
KB = {}
for domain in ["yacht", "baseball", "gymnastics"]:
    if os.path.exists(domain):
        KB[domain] = {}
        for fname in os.listdir(domain):
            if fname.lower().endswith(".json"):
                KB[domain][fname] = load_json(os.path.join(domain, fname))

if os.path.exists("fitness_knowledge.json"):
    KB["misc"] = {"fitness_knowledge": load_json("fitness_knowledge.json")}

# ===== 토큰화 & 점수 =====
def tokenize(text):
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))
    return [t.lower() for t in tokens]

def score_doc_for_query(doc_text, query_tokens):
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

def retrieve_relevant(domain_kb, query, top_k=3):
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

# ===== 로컬 답변 생성 =====
def local_synthesize_answer(query, retrieved):
    parts = [f"질문: {query}\n"]
    for domain, hits in retrieved.items():
        if not hits: continue
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            snippet = json.dumps(h["doc"], ensure_ascii=False, indent=2) if isinstance(h["doc"], dict) else str(h["doc"])
            parts.append(f"[{h['key']}] (score {h['score']}):\n{snippet}\n")
    return textwrap.shorten("\n".join(parts), width=3500, placeholder="\n\n…(생략)")

# ===== OpenAI 통합 =====
def openai_generate(query):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not openai or not api_key:
        return None
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are a helpful assistant."},
                {"role":"user","content":query}
            ],
            temperature=0.5,
            max_tokens=512
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        return None

# ===== FastAPI 라우트 =====
@app.get("/")
async def root():
    if os.path.exists("templates/index.html"):
        return FileResponse("templates/index.html")
    return JSONResponse({"message":"Index not found"})

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    query = data.get("query", "")
    retrieved = {domain: retrieve_relevant(KB.get(domain, {}), query) for domain in KB}
    answer_local = local_synthesize_answer(query, retrieved)
    answer_ai = openai_generate(query)
    return JSONResponse({"local": answer_local, "ai": answer_ai})
