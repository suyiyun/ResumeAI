"""
Chatbox snippet injected into every generated HTML page.
Call inject_chatbox(html, backend_url) to add it.
"""

CHATBOX_TEMPLATE = """
<!-- ResumeAI Chatbox -->
<style>
  #resumeai-chat { position: fixed; bottom: 24px; right: 24px; z-index: 9999; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
  #rai-btn {
    width: 52px; height: 52px; border-radius: 50%; background: #7c6aff;
    border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 20px rgba(124,106,255,0.5); transition: transform 0.2s;
  }
  #rai-btn:hover { transform: scale(1.08); }
  #rai-btn svg { width: 24px; height: 24px; fill: white; }
  #rai-panel {
    display: none; position: absolute; bottom: 64px; right: 0;
    width: 320px; background: #12121a; border: 1px solid #2a2a3d;
    border-radius: 16px; overflow: hidden;
    box-shadow: 0 12px 48px rgba(0,0,0,0.6);
  }
  #rai-panel.open { display: flex; flex-direction: column; }
  #rai-header {
    padding: 14px 16px; background: #1a1a28; border-bottom: 1px solid #2a2a3d;
    display: flex; align-items: center; justify-content: space-between;
  }
  #rai-header span { font-size: 13px; font-weight: 600; color: #e8e8f0; }
  #rai-header small { font-size: 11px; color: #6b7280; }
  #rai-close { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 18px; line-height:1; }
  #rai-messages {
    height: 240px; overflow-y: auto; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
  }
  #rai-messages::-webkit-scrollbar { width: 4px; }
  #rai-messages::-webkit-scrollbar-thumb { background: #2a2a3d; border-radius: 2px; }
  .rai-msg { max-width: 85%; padding: 9px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5; }
  .rai-msg.bot { background: #1a1a28; color: #e8e8f0; align-self: flex-start; border-bottom-left-radius: 3px; }
  .rai-msg.user { background: #7c6aff; color: #fff; align-self: flex-end; border-bottom-right-radius: 3px; }
  .rai-msg.loading { color: #6b7280; font-style: italic; }
  #rai-input-row {
    display: flex; gap: 8px; padding: 12px;
    border-top: 1px solid #2a2a3d; background: #1a1a28;
  }
  #rai-input {
    flex: 1; background: #12121a; border: 1px solid #2a2a3d; border-radius: 8px;
    color: #e8e8f0; font-size: 13px; padding: 8px 12px; outline: none;
    font-family: inherit;
  }
  #rai-input:focus { border-color: #7c6aff; }
  #rai-input::placeholder { color: #4b5563; }
  #rai-send {
    background: #7c6aff; border: none; border-radius: 8px;
    color: #fff; padding: 8px 14px; font-size: 13px; font-weight: 600;
    cursor: pointer; white-space: nowrap; transition: background 0.2s;
  }
  #rai-send:hover { background: #6c5aef; }
  #rai-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>

<div id="resumeai-chat">
  <div id="rai-panel">
    <div id="rai-header">
      <div>
        <span>✦ AI 定制助手</span><br>
        <small>告诉我你想改什么</small>
      </div>
      <button id="rai-close" onclick="raiToggle()">×</button>
    </div>
    <div id="rai-messages">
      <div class="rai-msg bot">你好！你可以告诉我任何修改，比如：<br>「把背景改成深蓝色」<br>「加一个 Projects 项目区域」<br>「把字体改大一点」</div>
    </div>
    <div id="rai-input-row">
      <input id="rai-input" placeholder="描述你想要的修改..." onkeydown="if(event.key==='Enter')raiSend()">
      <button id="rai-send" onclick="raiSend()">发送</button>
    </div>
  </div>
  <button id="rai-btn" onclick="raiToggle()" title="AI 定制">
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Sparkle/AI stars icon -->
      <path d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z" fill="white"/>
      <path d="M19 2L19.75 4.25L22 5L19.75 5.75L19 8L18.25 5.75L16 5L18.25 4.25L19 2Z" fill="white" opacity="0.8"/>
      <path d="M5 16L5.5 17.5L7 18L5.5 18.5L5 20L4.5 18.5L3 18L4.5 17.5L5 16Z" fill="white" opacity="0.7"/>
    </svg>
  </button>
</div>

<script>
(function() {
  const BACKEND = "BACKEND_URL_PLACEHOLDER";
  let history = [];
  let currentHTML = document.documentElement.outerHTML;

  function raiToggle() {
    const panel = document.getElementById('rai-panel');
    panel.classList.toggle('open');
  }
  window.raiToggle = raiToggle;

  function addMsg(text, role) {
    const el = document.createElement('div');
    el.className = 'rai-msg ' + role;
    el.innerHTML = text.replace(/\\n/g, '<br>');
    const msgs = document.getElementById('rai-messages');
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  async function raiSend() {
    const input = document.getElementById('rai-input');
    const send  = document.getElementById('rai-send');
    const msg   = input.value.trim();
    if (!msg) return;

    input.value = '';
    send.disabled = true;
    addMsg(msg, 'user');
    history.push({ role: 'user', content: msg });

    const loading = addMsg('正在修改页面...', 'bot loading');

    try {
      const res = await fetch(BACKEND + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: currentHTML, message: msg, history })
      });
      const data = await res.json();

      loading.remove();
      addMsg(data.reply, 'bot');
      history.push({ role: 'assistant', content: data.reply });

      // Apply updated HTML — preserve the chat panel state
      const panelOpen = document.getElementById('rai-panel').classList.contains('open');
      document.open();
      document.write(data.html);
      document.close();
      currentHTML = data.html;
      if (panelOpen) {
        setTimeout(() => {
          const p = document.getElementById('rai-panel');
          if (p) p.classList.add('open');
        }, 100);
      }
    } catch(e) {
      loading.textContent = '出错了，请重试 :(';
      loading.classList.remove('loading');
    }
    send.disabled = false;
  }
  window.raiSend = raiSend;
})();
</script>
<!-- /ResumeAI Chatbox -->
"""


def inject_chatbox(html: str, backend_url: str) -> str:
    """Inject the chatbox snippet into the HTML before </body>."""
    snippet = CHATBOX_TEMPLATE.replace("BACKEND_URL_PLACEHOLDER", backend_url.rstrip("/"))
    if "</body>" in html:
        return html.replace("</body>", snippet + "\n</body>", 1)
    return html + snippet
