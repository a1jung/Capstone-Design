from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json, re, textwrap
from typing import Dict, List

# OpenAI optional
try:
    import openai
except Exception:
    openai = None

app = FastAPI()

# static 서빙
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ====== 지식베이스 로드 ======
KB: Dict[str, Dict[str, dict]] = {}

for domain in ["yacht", "baseball", "gymnastics"]:
    if os.path.exists(domain):
        KB[domain] = {}
        for fname in os.listdir(domain):
            if fname.lower().endswith(".json"):
                path = os.path.join(domain, fname)
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        KB[domain][fname] = json.load(f)
                except:
                    print(f"[Warn] JSON decode error: {path}")

# ====== 토크나이저 & 검색 ======
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

# ====== OpenAI 호출 (선택) ======
def openai_generate(system_prompt: str, user_prompt: str, api_key: str, max_tokens=512):
    if openai is None:
        return None, "OpenAI 패키지가 설치되어 있지 않습니다."
    if not api_key:
        return None, "OpenAI API Key가 제공되지 않았습니다."
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)

# ====== FastAPI 엔드포인트 ======
@app.get("/")
async def home():
    return FileResponse("index.html")

@app.post("/query")
async def query_ai(req: Request):
    data = await req.json()
    question = data.get("question", "").strip()
    if not question:
        return JSONResponse({"answer": "질문을 입력해주세요."})

    # 로컬 KB 검색
    retrieved = {domain: retrieve_relevant(kb, question) for domain, kb in KB.items()}
    answer = local_synthesize_answer(question, retrieved)

    # OpenAI 보조 답변
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        system_prompt = "너는 스포츠 전문가 AI다. 사용자의 질문과 로컬 지식베이스 내용을 참고해 정확한 답변을 제공해라."
        full_prompt = f"사용자 질문:\n{question}\n\n로컬 문서 기반 요약 정보:\n{answer}"
        ai_answer, err = openai_generate(system_prompt, full_prompt, api_key)
        if ai_answer:
            answer = ai_answer

    return JSONResponse({"answer": answer})

        system_prompt = "당신은 Capstone Design 전문가 AI입니다. 질문에 대해 최대한 정확하고 이해하기 쉽게 답하세요."
        openai_ans, err = openai_generate(system_prompt, question, api_key)
        if openai_ans:
            answer = openai_ans
    
    return JSONResponse({"answer": answer})
