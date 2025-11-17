const chatBox = document.getElementById("chat-box");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");

function appendMessage(content, sender) {
  const msg = document.createElement("div");
  msg.classList.add("message", sender);
  msg.textContent = content;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendQuery(query) {
  appendMessage(query, "user");

  // FastAPI backend 요청
  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: query })
    });
    const data = await response.json();
    appendMessage(data.answer || "답변이 없습니다.", "bot");
  } catch (err) {
    appendMessage("서버 오류가 발생했습니다.", "bot");
    console.error(err);
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const query = userInput.value.trim();
  if (!query) return;
  sendQuery(query);
  userInput.value = "";
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event("submit"));
  }
});
