# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, json, re, textwrap
from typing import Dict, List

# Optional OpenAI usage
try:
    import openai
except Exception:
    openai = None

app = FastAPI()

# static 서빙
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ====== 유틸: JSON 안전 로드 ======
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

# ====== 지식베이스 로드 (도메인별) ======
KB: Dict[str, Dict[str, dict]] = {}
# domains and expected folder names (case-sensitive on server)
domains = {
    "yacht": ["yacht", ["Laser", "470"]],
    "baseball": ["baseball", []],
    "gymnastics": ["gymnastics", []],
}

# load generic files: for yacht we load per-class files; for other domains load single JSONs in folder
if os.path.exists("yacht"):
    KB["yacht"] = {}
    # try Laser and 470 directories (case-sensitive)
    for cls in ["Laser", "470", "laser", "470"]:
        dir_path = os.path.join("yacht", cls)
        if os.path.isdir(dir_path):
            # load all json files in that folder and combine under one doc
            combined = {}
            for fname in os.listdir(dir_path):
                if fname.lower().endswith(".json"):
                    combined_name = fname
                    combined[combined_name] = load_json(os.path.join(dir_path, fname))
            if combined:
                KB["yacht"][cls.lower()] = combined

# baseball folder: load all json files and flatten
if os.path.exists("baseball"):
    KB["baseball"] = {}
    for fname in os.listdir("baseball"):
        if fname.lower().endswith(".json"):
            KB["baseball"][fname] = load_json(os.path.join("baseball", fname))

# gymnastics folder
if os.path.exists("gymnastics"):
    KB["gymnastics"] = {}
    for fname in os.listdir("gymnastics"):
        if fname.lower().endswith(".json"):
            KB["gymnastics"][fname] = load_json(os.path.join("gymnastics", fname))

# fallback: if a top-level JSON exists (fitness_knowledge.json etc.)
for top in ["fitness_knowledge.json", "fitness_knowledge"]:
    if os.path.exists(top):
        KB.setdefault("misc", {})["fitness_knowledge"] = load_json(top)

# ====== 간단한 키워드 기반 검색/랭킹 ======
def tokenize(text: str) -> List[str]:
    # 간단 토크나이저: 알파벳/한글 단어 분리, 소문자
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
        # partial match
        for dt in dtoks:
            if qt in dt:
                s += 1
    return s

def retrieve_relevant(domain_kb: dict, query: str, top_k=3):
    qtokens = tokenize(query)
    hits = []
    # domain_kb may be nested (like yacht: { 'laser': {file: obj}} or baseball: {file: obj})
    if not domain_kb:
        return []
    # flatten
    for key, val in domain_kb.items():
        # val might be dict of files or a doc
        if isinstance(val, dict):
            # stringify the contents for scoring
            text = json.dumps(val, ensure_ascii=False)
            score = score_doc_for_query(text, qtokens)
            hits.append((score, key, val))
        else:
            text = str(val)
            score = score_doc_for_query(text, qtokens)
            hits.append((score, key, val))
    hits = sorted(hits, key=lambda x: x[0], reverse=True)
    return [ {"score": h[0], "key": h[1], "doc": h[2]} for h in hits if h[0] > 0 ][:top_k]

# ====== 로컬 응답 생성기 (간단 요약/조합) ======
def local_synthesize_answer(query: str, retrieved: dict) -> str:
    # retrieved: {domain: [hits...], ...}
    parts = []
    parts.append(f"질문: {query}\n")
    for domain, hits in retrieved.items():
        if not hits:
            continue
        parts.append(f"--- {domain.upper()} 관련 정보 ---")
        for h in hits:
            # doc may be nested dict -> pretty print relevant fields
            snippet = ""
            if isinstance(h["doc"], dict):
                # try common fields
                if "description.json" in h["doc"]:
                    snippet = json.dumps(h["doc"]["description.json"], ensure_ascii=False, indent=2)
                else:
                    snippet = json.dumps(h["doc"], ensure_ascii=False, indent=2)
            else:
                snippet = str(h["doc"])
            parts.append(f"[{h['key']}] (score {h['score']}):\n{snippet}\n")
    # simple polish
    answer = "\n".join(parts)
    # shorten to reasonable length
    return textwrap.shorten(answer, width=3500, placeholder="\n\n…(생략)")

# ====== OpenAI 통합 보조 (선택적) ======
def openai_generate(system_prompt: str, user_prompt: str, api_key: str, max_tokens=512):
    if openai is None:
        return None, "OpenAI 패키지가 설치되어 있지 않습니다."
    if not api_key:
        return None, "OpenAI API Key가 제공되지 않았습니다."
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini" if hasattr(openai, "ChatCompletion") else "gpt-4o-mini",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt}
