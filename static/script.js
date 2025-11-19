// static/script.js
const chat = document.getElementById("chat");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");

function appendMessage(text, who="bot"){
  const el = document.createElement("div");
  el.className = "msg " + (who === "user" ? "user" : "bot");
  // support simple preformatted blocks for readability
  if(text.includes("\n")){
    const pre = document.createElement("pre");
    pre.style.whiteSpace = "pre-wrap";
    pre.textContent = text;
    el.appendChild(pre);
  } else {
    el.textContent = text;
  }
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

async function sendQuestion(){
  const q = questionInput.value.trim();
  if(!q) return;
  appendMessage(q, "user");
  questionInput.value = "";
  appendMessage("응답 생성 중...", "bot"); // 임시 로딩 텍스트
  // 마지막 봇 메시지 교체
  const botMsgs = document.querySelectorAll(".msg.bot");
  const loadingEl = botMsgs[botMsgs.length-1];

  try {
    const resp = await fetch("/query", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({question: q})
    });
    const data = await resp.json();
    if(resp.ok && data.answer){
      loadingEl.remove();
      appendMessage(data.answer, "bot");
    } else {
      loadingEl.remove();
      appendMessage("서버 오류: 응답을 받지 못했습니다.", "bot");
      console.error(data);
    }
  } catch (e) {
    loadingEl.remove();
    appendMessage("네트워크 오류: " + e.message, "bot");
    console.error(e);
  }
}

// Enter 키로 전송 (Shift+Enter는 줄바꿈)
questionInput.addEventListener("keydown", (e) => {
  if(e.key === "Enter" && !e.shiftKey){
    e.preventDefault();
    sendQuestion();
  }
});

sendBtn.addEventListener("click", sendQuestion);

// 환영 메시지
appendMessage("안녕하세요! Capstone-Design 전문가 AI입니다. 질문을 입력해주세요.", "bot");
