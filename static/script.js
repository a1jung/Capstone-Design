const chatbox = document.getElementById("chatbox");
const input = document.getElementById("query");
const btn = document.getElementById("send");

btn.onclick = async () => {
    const q = input.value.trim();
    if(!q) return;
    appendMessage(q, "user");
    input.value = "";
    const resp = await fetch("/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query: q})
    });
    const data = await resp.json();
    if(data.local) appendMessage(data.local, "local");
    if(data.ai) appendMessage(data.ai, "ai");
}

function appendMessage(msg, cls){
    const div = document.createElement("div");
    div.className = "message " + cls;
    div.textContent = msg;
    chatbox.appendChild(div);
    chatbox.scrollTop = chatbox.scrollHeight;
}
