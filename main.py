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

# =============================
# 📌 한국어 → 영어 검색 확장 사전
# =============================
KOR_TO_ENG = {
    "요트": ["yacht", "laser", "470"],
    "세일링": ["yacht"],
    "레이저": ["laser"],
    "야구": ["baseball", "pitcher", "catcher", "infielder", "outfielder"],
    "투수": ["pitcher"],
    "포수": ["catcher"],
    "타자": ["batter"],
    "내야": ["infielder"],
    "외야": ["outfielder"],
    "체조": ["gymnastics"],
    "기계체조": ["gymnastics"],
    "평행봉": ["parallel bars"],
    "마루": ["floor"],
    "도마": ["vault"],
    "링": ["rings"],
}

def expand_korean_query(q: str) -> str:
    """한국어 질문을 영어 키워드까지 확장"""
    result = [q]
    for kor, eng_list in KOR_TO_ENG.items():
        if kor in q:
            result.extend(eng_list)
    return " ".join(result)


# =============================
# 경로 설정
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# =============================
# KB 로드 (JSON 재귀 탐색)
# =============================
KB: Dict[str, Dict[str, dict]] = {}
for domain in ["yacht", "baseball", "gymnastics"]:
    domain_path = os.path.join(BASE_DIR, domain)
    if os.path.exists(domain_path):
        KB[domain] = {}
        for root, dirs, files in os.walk(domain_path):
            for fname in files:
                if fname.lower().endswith(".json"):
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, domain_path)
                    try:
                        with open(fpath, "r", encoding="utf-8-sig") as f:
                            KB[domain][rel_path] = json.load(f)
                    except:
                        print(f"[Warn] JSON decode error: {fpath}")

# =============================
# 검색 토크나이즈
# =============================
def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z\uAC00-\uD7AF0-9]+", str(text))] if text else []


def score_doc_for_query(doc_text: str, query_tokens: List[str]) -> int:
    if not doc_text:
        return 0
    dtoks = tokenize(doc_text)
    dtokset = set(dtoks)
    score = 0
    for qt in query_tokens:
        if qt in dtokset:
            score += 2
        for dt in dtoks:
            if qt in dt:
                score += 1
    return score


# =============================
# 도메인 자동 분류
# =============================
def classify_domain(question: str) -> List[str]:
    q = question.lower()
    if any(k in q for k in ["요트", "laser", "470", "yacht"]):
        return ["yacht"]
    elif any(k in q for k in ["야구", "투수", "포수", "baseball"]):
        return ["baseball"]
    elif any(k in q for k in ["체조", "마루", "평행봉", "gymnastics"]):
        return ["gymnastics"]
    else:
        return ["yacht", "baseball", "gymnastics"]


# =============================
# KB 검색
# =============================
def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = tokenize(query)
    hits = []

    for key, val in domain_kb.items():
        # JSON 전체 flatten
        def flatten(obj):
            if isinstance(obj, dict):
                return " ".join([flatten(v) for v in obj.values()])
            elif isinstance(obj, list):
                return " ".join([flatten(i) for i in obj])
            else:
                return str(obj)

        flat = flatten(val)
        score = score_doc_for_query(flat, qtokens)
        hits.append((score, key, val))

    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [{"score": s, "key": k, "doc": d} for s, k, d in hits if s > 0][:top_k]


# =============================
# 요약 생성
# =============================
def summarize_doc(doc: dict) -> str:
    parts = []

    if "overview" in doc:
        parts.append(f"- {doc['overview']}")
    if "function" in doc:
        parts.append(f"- 기능: {doc['function']}")
    if "wind_ranges" in doc:
        parts.append("- 바람 범위: " + ", ".join([f"{k}={v}" for k, v in doc["wind_ranges"].items()]))
    if "cunningham" in doc and isinstance(doc["cunningham"], dict):
        parts.append(
            "- 커닝햄 가이드: "
            + ", ".join([f"{k}={v}" for k, v in doc["cunningham"].items()])
        )
    if "equipment" in doc:
        for k, v in doc["equipment"].items():
            desc = v.get("description", "") if isinstance(v, dict) else str(v)
            if desc:
                parts.append(f"- {k}: {desc}")

    return "\n".join(parts)


# =============================
# 최종 답변 합성
# =============================
def local_synthesize_answer(query: str, retrieved: dict) -> str:
    found = False
    parts = []

    for domain, hits in retrieved.items():
        if not hits:
            continue
        found = True
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            parts.append(summarize_doc(h["doc"]))

    if not found:
        return "죄송합니다, 관련 정보를 찾을 수 없습니다."

    parts.append("\n추가 설명이나 세부 정보가 필요하면 언제든지 알려주세요!")
    return textwrap.shorten("\n".join(parts), width=3500, placeholder="\n\n…(생략)")


# =============================
# OpenAI 연결 (옵션)
# =============================
def openai_generate(system_prompt: str, user_prompt: str, api_key: str, max_tokens=512):
    if not openai:
        return None, "OpenAI 패키지가 없음"
    if not api_key:
        return None, "API Key 없음"

    try:
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content, None
    except Exception as e:
        return None, str(e)


# =============================
# API 엔드포인트
# =============================
@app.get("/")
async def home():
    html = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html):
        return FileResponse(html)
    return {"error": "index.html not found"}


@app.post("/query")
async def query_ai(req: Request):
    data = await req.json()
    question = data.get("question", "").strip()

    if not question:
        return JSONResponse({"answer": "질문을 입력해주세요."})

    # 한국어 질문 확장
    expanded = expand_korean_query(question)

    # 도메인 분류 후 검색
    domains = classify_domain(question)
    retrieved = {
        domain: retrieve_relevant(KB.get(domain, {}), expanded)
        for domain in domains
    }

    # 합성
    answer = local_synthesize_answer(question, retrieved)

    # OpenAI 사용 시 가독성 향상
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        sys = "당신은 Capstone Design 전문가 AI입니다. 검색 결과를 바탕으로 자연스럽게 설명하세요."
        resp, err = openai_generate(sys, answer, api_key, max_tokens=400)
        if resp:
            answer = resp

    return JSONResponse({"answer": answer})
