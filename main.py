import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
app = FastAPI()

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# static / templates 연결
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

###############################
#   지식베이스 자동 로드       #
###############################
KB = {}

def load_all_knowledge():
    base_dir = "knowledge"
    result = {}

    if not os.path.exists(base_dir):
        return {}

    for domain in os.listdir(base_dir):
        domain_path = os.path.join(base_dir, domain)
        if not os.path.isdir(domain_path):
            continue

        result[domain] = {}

        for file in os.listdir(domain_path):
            if file.endswith(".json"):
                with open(os.path.join(domain_path, file), "r", encoding="utf-8") as f:
                    result[domain][file] = json.load(f)

    return result

KB = load_all_knowledge()

###############################
#     요청 모델                #
###############################
class ChatRequest(BaseModel):
    message: str

###############################
#   AI에게 넘길 시스템 프롬프트 #
###############################
SYSTEM_PROMPT = """
너는 요트, 야구, 기계체조 전문 지식을 가진 AI 전문가 시스템이다.
질문을 분석해서 어떤 분야인지 자동으로 판단하고,
아래 제공된 JSON 지식을 참고해 정확하고 자세하게 설명해라.

- 요트: sailing / laser / 470 / mast / sail trim 등
- 야구: pitching, batting, rules 등
- 기계체조: floor, vault, pommel, rings 등

만약 지식베이스에 있는 내용이면 반드시 기반해서 답변하고,
없는 내용이면 일반적인 상식으로 설명한다.
"""

###############################
#   ChatGPT 응답 생성 함수     #
###############################
def generate_answer(user_message: str):
    knowledge_text = json.dumps(KB, ensure_ascii=False)

    prompt = f"""
[사용자 질문]
{user_message}

[지식베이스 JSON]
{knowledge_text}

위 JSON에서 관련 있는 내용을 골라서 사람이 이해하기 쉽게 정리해서 설명해줘.
필요하면 여러 영역을 조합해도 된다.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )

    return response.choices[0].message.content

###############################
#   라우팅                    #
###############################
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        answer = generate_answer(req.message)
        return {"answer": answer}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
