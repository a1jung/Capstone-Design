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

    addMessage(text, "user");
    input.value = "";

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text }),
        });

        const data = await res.json();

        addMessage(data.answer || "죄송합니다, 관련 정보를 찾을 수 없습니다.", "ai");

    } catch (err) {
        addMessage("서버와 연결할 수 없습니다.", "ai");
    }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});
