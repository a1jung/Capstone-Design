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

# 🔥 가장 핵심 변경: Render 기준으로 확실한 프로젝트 루트를 사용
BASE_DIR = os.getcwd()
print("🔥 BASE_DIR =", BASE_DIR)

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    print("⚠ static 폴더 없음:", STATIC_DIR)

# ----------------------------------------------------------
#                 KB(지식 파일) 로딩
# ----------------------------------------------------------
KB: Dict[str, Dict[str, dict]] = {}
knowledge_domains = ["yacht", "baseball", "gymnastics"]

for domain in knowledge_domains:
    domain_path = os.path.join(BASE_DIR, domain)

    if not os.path.exists(domain_path):
        print(f"❌ KB 폴더 없음: {domain_path}")
        continue

    print(f"📂 로딩 중: {domain_path}")
    KB[domain] = {}

    for root, dirs, files in os.walk(domain_path):
        for fname in files:
            if fname.lower().endswith(".json"):
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, domain_path)

                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        KB[domain][rel_path] = json.load(f)
                    print(f"   ✔ JSON 로드됨: {rel_path}")
                except Exception as e:
                    print(f"   ❌ JSON 오류: {rel_path} → {e}")

print("📌 KB 최종 로드 결과:")
for dom in KB:
    print("  -", dom, ":", list(KB[dom]].keys()))

# ----------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------
def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))] if text else []

def score_doc_for_query(doc_text: str, query_tokens: List[str]) -> int:
    if not doc_text: return 0
    dtoks = tokenize(doc_text)
    s = 0
    dtokset = set(dtoks)
    for qt in query_tokens:
        if qt in dtokset: s += 2
        for dt in dtoks:
            if qt in dt: s += 1
    return s

# ----------------------------------------------------------
# Domain Classification
# ----------------------------------------------------------
def classify_domain(question: str) -> List[str]:
    q = question.lower()
    if any(k in q for k in ["요트", "laser", "470", "yacht"]):
        return ["yacht"]
    elif any(k in q for k in ["야구", "투수", "포수", "내야", "외야", "baseball"]):
        return ["baseball"]
    elif any(k in q for k in ["체조", "평행봉", "마루", "도마", "링", "gymnastics"]):
        return ["gymnastics"]
    return ["yacht", "baseball", "gymnastics"]

# ----------------------------------------------------------
# Retrieve KB
# ----------------------------------------------------------
def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = tokenize(query)
    hits = []

    if not domain_kb:
        print("⚠ KB empty for domain")
        return []

    for key, val in domain_kb.items():

        def flatten_text(obj):
            if isinstance(obj, dict):
                return " ".join([flatten_text(v) for v in obj.values()])
            elif isinstance(obj, list):
                return " ".join([flatten_text(i) for i in obj])
            else:
                return str(obj)

        text = flatten_text(val)
        score = score_doc_for_query(text, qtokens)
        hits.append((score, key, val))

    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [{"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0][:top_k]

# ----------------------------------------------------------
# Summarize
# ----------------------------------------------------------
def summarize_doc(doc: dict) -> str:
    if not isinstance(doc, dict):
        return str(doc)
    parts = []

    if "overview" in doc: parts.append(f"- {doc['overview']}")
    if "function" in doc: parts.append(f"- 기능: {doc['function']}")
    if "wind_ranges" in doc:
        parts.append("- 바람 범위: " + ", ".join([f"{k}={v}" for k, v in doc["wind_ranges"].items()]))
    if "cunningham" in doc and isinstance(doc["cunningham"], dict):
        parts.append("- 커닝햄: " + ", ".join([f"{k}={v}" for k, v in doc["cunningham"].items()]))

    if "equipment" in doc:
        for k, v in doc["equipment"].items():
            desc = v.get("description", "") if isinstance(v, dict) else str(v)
            if desc: parts.append(f"- {k}: {desc}")

    return "\n".join(parts)

# ----------------------------------------------------------
# Answer composer
# ----------------------------------------------------------
def local_synthesize_answer(query: str, retrieved: dict) -> str:
    parts = []
    found = False

    for domain, hits in retrieved.items():
        if not hits:
            continue
        found = True
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            snippet = summarize_doc(h["doc"])
            parts.append(snippet)

    if not found:
        return "죄송합니다, 관련 정보를 찾을 수 없습니다."

    parts.append("\n추가 설명이 필요하면 말씀해주세요!")
    return textwrap.shorten("\n".join(parts), width=3500, placeholder="\n\n…(생략)")

# ----------------------------------------------------------
# OpenAI (optional)
# ----------------------------------------------------------
def openai_generate(system_prompt: str, user_prompt: str, api_key: str, max_tokens=512):
    if not openai: return None, "OpenAI 미설치"
    if not api_key: return None, "키 없음"
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)

# ----------------------------------------------------------
# API Routes
# ----------------------------------------------------------
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

    if not question:
        return JSONResponse({"answer": "질문을 입력해주세요."})

    domains = classify_domain(question)
    retrieved = {domain: retrieve_relevant(KB.get(domain, {}), question) for domain in domains}
    answer = local_synthesize_answer(question, retrieved)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        system_prompt = "당신은 Capstone Design 전문가 AI입니다."
        gpt_answer, err = openai_generate(system_prompt, answer, api_key, max_tokens=400)
        if gpt_answer:
            answer = gpt_answer

    return JSONResponse({"answer": answer})
