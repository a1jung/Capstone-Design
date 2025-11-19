# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json, re, textwrap
from typing import Dict, List
from pathlib import Path

# OpenAI optional
try:
    import openai
except Exception:
    openai = None

BASE = Path(__file__).parent.resolve()

app = FastAPI()

# static 서빙
static_dir = BASE / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# templates path
INDEX_PATH = BASE / "templates" / "index.html"

# ====== 지식베이스 로드 ======
KB: Dict[str, Dict[str, dict]] = {}

def safe_load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warn] JSON decode error: {path} -> {e}")
        return {}

# 도메인 폴더 목록(원하면 여기에 다른 도메인 추가)
for domain in ["yacht", "baseball", "gymnastics"]:
    folder = BASE / domain
    if folder.exists() and folder.is_dir():
        KB[domain] = {}
        # 지원: 폴더 내부에 바로 json 파일들 혹은 서브폴더(클래스) 구조
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".json":
                KB[domain][entry.name] = safe_load_json(entry)
            elif entry.is_dir():
                # 폴더 안의 모든 json을 합쳐서 <subdir>/<file.json>으로 저장
                KB[domain][entry.name] = {}
                for sub in entry.iterdir():
                    if sub.is_file() and sub.suffix.lower() == ".json":
                        KB[domain][entry.name][sub.name] = safe_load_json(sub)

# ====== 토크나이저 & 검색(심플키워드) ======
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
    return [ {"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0 ][:top_k]

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
        # 최신 OpenAI SDK may vary; this uses ChatCompletion for compatibility
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        # 안전하게 응답 얻기
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            # some SDKs: resp.choices[0].message.content
            choice = resp.choices[0]
            if hasattr(choice, "message") and isinstance(choice.message, dict):
                return choice.message.get("content", "").strip(), None
            # fallback
            return getattr(choice, "text", "").strip() or str(choice), None
        return None, "OpenAI 응답 형식이 예상과 다릅니다."
    except Exception as e:
        return None, str(e)

# ====== FastAPI 엔드포인트 ======
@app.get("/")
async def home():
    # templates/index.html 경로 존재 확인 후 반환
    if INDEX_PATH.exists():
        return FileResponse(str(INDEX_PATH))
    return JSONResponse({"error": "index.html not found on server"}, status_code=500)

@app.post("/query")
async def query_ai(req: Request):
    data = await req.json()
    question = data.get("question", "").strip()
    if not question:
        return JSONResponse({"answer": "질문을 입력해주세요."})
    
    # 로컬 KB 검색
    retrieved = {domain: retrieve_relevant(kb, question) for domain, kb in KB.items()}
    answer = local_synthesize_answer(question, retrieved)
    
    # OpenAI API 키가 있으면 보조 -> 배포 환경의 ENV VAR 사용 권장
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and openai is not None:
        system_prompt = "당신은 Capstone Design 전문가 AI입니다. 질문에 대해 최대한 정확하고 이해하기 쉽게 답하세요."
        gpt_answer, err = openai_generate(system_prompt, answer, api_key, max_tokens=400)
        if gpt_answer:
            answer = gpt_answer
        else:
            # 오류가 난 경우 로컬 answer와 함께 오류 메시지 포함
            answer = f"{answer}\n\n(참고: OpenAI 보조 호출 실패: {err})"
    
    return JSONResponse({"answer": answer})
