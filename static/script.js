// static/script.js
const chatEl = document.getElementById('chat');
const queryEl = document.getElementById('query');
const sendBtn = document.getElementById('send');
const useOpenaiEl = document.getElementById('use_openai');
const openaiKeyEl = document.getElementById('openai_key');

function appendMessage(text, cls){
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  chatEl.appendChild(d);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendQuery(){
  const q = queryEl.value.trim();
  if(!q) return;
  appendMessage(q, 'user');
  queryEl.value = '';

  appendMessage('잠시 처리중입니다...', 'assistant');
  const last = chatEl.lastChild;
  try {
    const payload = { query: q, use_openai: useOpenaiEl.checked };
    if(useOpenaiEl.checked){
      const k = openaiKeyEl.value.trim();
      if(k) payload.openai_key = k;
    }
    const resp = await fetch('/api/chat', {
      method:'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if(data.error){
      last.textContent = '오류: ' + data.error;
    } else {
      // replace the "처리중" message
      last.textContent = data.answer || JSON.stringify(data, null, 2);
      // (선택) show source info
      const meta = document.createElement('div');
      meta.style.fontSize='12px'; meta.style.opacity=0.7;
      meta.textContent = `출처: ${data.source || 'unknown'}`;
      last.appendChild(document.createElement('br'));
      last.appendChild(meta);
    }
  } catch(e){
    last.textContent = '요청 실패: ' + e.message;
  }
}

sendBtn.addEventListener('click', sendQuery);
queryEl.addEventListener('keydown', (e)=>{ if(e.key === 'Enter' && (e.ctrlKey||e.metaKey)) sendQuery(); });
