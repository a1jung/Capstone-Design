@app.post("/query")
async def query_ai(req: Request):
    try:
        data = await req.json()
        question = data.get("question", "").strip()
        if not question:
            return JSONResponse({"answer": "질문을 입력해주세요."})

        # 도메인 분류
        domains = classify_domain(question)
        retrieved = {
            domain: retrieve_relevant(KB.get(domain, {}), question)
            for domain in domains
        }

        # 로컬 KB 기반 응답 생성
        answer = local_synthesize_answer(question, retrieved)

        # OpenAI 옵션
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            system_prompt = (
                "당신은 Capstone Design 전문가 AI입니다. "
                "질문에 대해 최대한 정확하고 이해하기 쉽게 답하세요."
            )
            gpt_answer, err = openai_generate(
                system_prompt, answer, api_key, max_tokens=400
            )
            if gpt_answer:
                answer = gpt_answer

        return JSONResponse({"answer": answer})

    except Exception as e:
        # 모든 예외를 JSON으로 감싸서 script.js가 깨지지 않게 강제 보정
        return JSONResponse({"answer": f"서버 오류 발생: {str(e)}"})
