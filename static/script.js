// static/script.js
const messages = document.getElementById("messages");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // 사용자 메시지 표시
    addMessage(text, "user");
    input.value = "";

    // 로딩 메시지
    const loadingDiv = document.createElement("div");
    loadingDiv.classList.add("message", "ai");
    loadingDiv.textContent = "응답 생성 중...";
    messages.appendChild(loadingDiv);
    messages.scrollTop = messages.scrollHeight;

    try {
        const response = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text })
        });

        const data = await response.json();

        // 로딩 메시지 제거
        loadingDiv.remove();

        // 서버 응답 표시
        if (data.answer) {
            addMessage(data.answer, "ai");
        } else {
            addMessage("서버 오류: 응답을 받지 못했습니다.", "ai");
            console.error(data);
        }
    } catch (e) {
        loadingDiv.remove();
        addMessage("네트워크 오류: " + e.message, "ai");
        console.error(e);
    }
}

// 전송 버튼 클릭
sendBtn.addEventListener("click", sendMessage);

// Enter 키 전송
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// 환영 메시지
addMessage("안녕하세요! Capstone-Design 전문가 AI입니다. 질문을 입력해주세요.", "ai");
