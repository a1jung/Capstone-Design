// 메시지 출력 함수
function addMessage(text, sender) {
    const messages = document.getElementById("messages");
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

// 전송 버튼 이벤트
document.getElementById("sendBtn").addEventListener("click", sendMsg);
document.getElementById("userInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMsg();
});

async function sendMsg() {
    const input = document.getElementById("userInput");
    const text = input.value.trim();
    if (!text) return;

    // 사용자 메시지 오른쪽
    addMessage(text, "user");

    input.value = "";

    try {
        // 실제 AI 서버로 요청 보내는 부분 (너의 API URL로 수정)
        const res = await fetch("http://localhost:8000/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ question: text })
        });

        const data = await res.json();

        // AI 응답 왼쪽
        addMessage(data.answer, "ai");

    } catch (error) {
        addMessage("오류가 발생했습니다. 다시 시도해주세요.", "ai");
    }
}
