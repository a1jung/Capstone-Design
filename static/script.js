const messages = document.getElementById("messages");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

// 메세지 추가
function addMessage(text, sender) {
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

// 질문 전송
async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user");
    input.value = "";

    addMessage("응답 생성 중...", "ai");
    const aiDiv = messages.lastElementChild;

    try {
        // ✅ 상대경로 fetch
        const resp = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text })
        });

        const data = await resp.json();
        aiDiv.textContent = data.answer || "죄송합니다, 답변을 받을 수 없습니다.";
    } catch (e) {
        aiDiv.textContent = "서버 오류가 발생했습니다.";
        console.error(e);
    }
}

// 버튼 및 엔터 이벤트
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});
