async function send() {
  const prompt = document.getElementById('prompt').value.trim();
  const out = document.getElementById('out');
  const sendBtn = document.getElementById('send');
  const overlay = document.getElementById('loading');
  if (!prompt) { out.textContent = 'Please enter a message.'; return; }
  out.textContent = '';
  sendBtn.disabled = true;
  if (overlay) overlay.classList.add('show');
  try {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    if (!res.ok) {
      const err = await res.text();
      out.textContent = `Error ${res.status}: ${err}`;
      return;
    }
    if (!res.body) {
      out.textContent = 'Streaming not supported by the browser/connection.';
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      out.textContent += decoder.decode(value, { stream: true });
      out.scrollTop = out.scrollHeight;
    }
    // Flush any remaining partial multi-byte characters
    out.textContent += decoder.decode();
    out.scrollTop = out.scrollHeight;
  } catch (e) {
    out.textContent = 'Network error: ' + (e?.message || e);
  } finally {
    sendBtn.disabled = false;
    if (overlay) overlay.classList.remove('show');
  }
}

document.getElementById('send').addEventListener('click', send);

document.getElementById('prompt').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send();
});
