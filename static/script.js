const messages = document.getElementById("messages");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

// 메시지 추가
function addMessage(text, sender) {
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

// 서버에 질문 보내기
async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user"); // 사용자 메시지 표시
    input.value = "";

    try {
        const response = await fetch("/query", { // /chat -> /query
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question: text }) // key는 question
        });

        const data = await response.json();

        if (data.answer) {
            addMessage(data.answer, "ai"); // 서버 응답 표시
        } else {
            addMessage("죄송합니다, 답변을 받을 수 없습니다.", "ai");
        }
    } catch (e) {
        addMessage("서버 오류가 발생했습니다.", "ai");
        console.error(e);
    }
}

// 이벤트
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// 환영 메시지
addMessage("안녕하세요! Capstone-Design 전문가 AI입니다. 질문을 입력해주세요.", "ai");
