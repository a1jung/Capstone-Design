const chatBox = document.getElementById('chat-box');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

function appendMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.classList.add('message', sender);
  msgDiv.textContent = text;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = userInput.value.trim();
  if (!question) return;

  appendMessage(question, 'user');
  userInput.value = '';

  appendMessage('답변을 생성 중...', 'bot');

  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    const data = await response.json();
    const lastBotMessage = chatBox.querySelector('.message.bot:last-child');
    if (lastBotMessage) lastBotMessage.textContent = data.answer || '답변이 없습니다.';
  } catch (err) {
    const lastBotMessage = chatBox.querySelector('.message.bot:last-child');
    if (lastBotMessage) lastBotMessage.textContent = '서버 오류 발생';
    console.error(err);
  }
});
