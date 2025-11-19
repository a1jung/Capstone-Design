const messagesDiv = document.getElementById("messages");
const questionInput = document.getElementById("question");

function appendMessage(text, who="bot"){
  const el = document.createElement("div");
  el.className = "msg " + (who === "user" ? "user" : "bot");
  if(text.includes("\n")){
    const pre = document.createElement("pre");
    pre.style.whiteSpace = "pre-wrap";
    pre.textContent = text;
    el.appendChild(pre);
  } else {
    el.textContent = text;
  }
  messagesDiv.appendChild(el);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendQuestion(){
  const q = questionInput.value.trim();
  if(!q) return;
  appendMessage(q, "user");
  questionInput.value = "";
  appendMessage("응답 생성 중...", "bot");
  const botMsgs = document.querySelectorAll(".msg.bot");
  const loadingEl = botMsgs[botMsgs.length-1];

  try{
    const resp = await fetch("/query", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({question:q})
    });
    const data = await resp.json();
    loadingEl.remove();
    appendMessage(data.answer || "서버 오류: 응답 없음", "bot");
  }catch(e){
    loadingEl.remove();
    appendMessage("네트워크 오류: "+e.message, "bot");
  }
}

questionInput.addEventListener("keydown",(e)=>{
  if(e.key==="Enter" && !e.shiftKey){
    e.preventDefault();
    sendQuestion();
  }
});

// 초기 환영 메시지
appendMessage("안녕하세요! Capstone-Design 전문가 AI입니다. 질문을 입력해주세요.", "bot");
