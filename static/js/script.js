// ========================
  // Utilidades de fecha
  // ========================
  function todayKey() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth()+1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function friendlyDate(key) {
    const [y,m,d] = key.split('-').map(Number);
    const dt = new Date(y, m-1, d);
    const td = new Date();
    const same = dt.toDateString() === new Date(td.getFullYear(), td.getMonth(), td.getDate()).toDateString();
    if (same) return 'Hoy';
    const yesterday = new Date(td); yesterday.setDate(td.getDate()-1);
    const ySame = dt.toDateString() === new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate()).toDateString();
    if (ySame) return 'Ayer';
    return dt.toLocaleDateString('es-ES', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
  }

  // ========================
  // Estado UI
  // ========================
  const state = {
    sessions: {},
    activeKey: todayKey(),
    polling: null
  };

  // ========================
  // Render: lista de chats (sidebar)
  // ========================
  const chatList = document.getElementById('chatList');
  function renderChatList() {
    const keys = Object.keys(state.sessions).sort().reverse();
    chatList.innerHTML = '';
    keys.forEach(key => {
      const item = document.createElement('div');
      item.className = 'chat-item' + (key === state.activeKey ? ' active' : '');
      item.innerHTML = `
        <div style="width:32px;height:32px;border-radius:10px;background: radial-gradient(60% 60% at 40% 40%, var(--accent-500), var(--accent-700)); display:grid; place-items:center; color:#fff; font-weight:800;">${friendlyDate(key).slice(0,1)}</div>
        <div>
          <div class="chat-title">${friendlyDate(key)}</div>
          <div class="chat-date">${key}</div>
        </div>
        <div style="font-size:12px; color: var(--muted);">${state.sessions[key].length} msgs</div>
      `;
      item.addEventListener('click', () => { state.activeKey = key; renderChatList(); renderChatArea(); });
      chatList.appendChild(item);
    });
  }

  // ========================
  // Render: panel de chat
  // ========================
  const chatArea = document.getElementById('chatArea');
  const chatTitle = document.getElementById('chatTitle');
  function renderChatArea() {
    const msgs = state.sessions[state.activeKey] || [];
    chatTitle.textContent = `Chat — ${friendlyDate(state.activeKey)}`;
    chatArea.innerHTML = '';
    msgs.forEach(m => {
      const div = document.createElement('div');
      div.className = 'msg ' + (m.tipo === 'usuario' ? 'user' : 'alira');
      
      // Si el mensaje contiene <a href> lo dejamos como HTML, si no, escapamos
      const safeMessage = /<a\s+href=/.test(m.mensaje) ? m.mensaje : escapeHtml(m.mensaje);
      div.innerHTML = `<div>${safeMessage}</div>`;
      chatArea.appendChild(div);
    });
    chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, s => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[s]));
  }

  // ========================
  // Carga del historial
  // ========================
  async function loadHistory() {
    try {
      const res = await fetch('/get_chat');
      const data = await res.json();
      const groups = {};
      data.forEach(m => {
        let key = todayKey();
        if (m.timestamp) {
          const t = new Date(m.timestamp);
          const k = `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`;
          key = k;
        }
        if (!groups[key]) groups[key] = [];
        groups[key].push(m);
      });
      state.sessions = groups;
      if (!state.sessions[state.activeKey]) state.activeKey = Object.keys(state.sessions)[0] || todayKey();
      renderChatList();
      renderChatArea();
    } catch (e) {
      console.error('Error cargando historial', e);
    }
  }

  // Auto-actualización cada 1.5s
  function startPolling() {
    if (state.polling) clearInterval(state.polling);
    state.polling = setInterval(loadHistory, 1500);
  }

  // ========================
  // Tema claro/oscuro
  // ========================
  const themeToggle = document.getElementById('themeToggle');
  const sunIcon = document.getElementById('sunIcon');
  const moonIcon = document.getElementById('moonIcon');
  const logoDark = document.getElementById("logoDark");
  const logoLight = document.getElementById("logoLight");

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    const dark = theme === 'dark';
    sunIcon.classList.toggle('hidden', dark);
    moonIcon.classList.toggle('hidden', !dark);
    logoDark.classList.toggle('hidden', dark);
    logoLight.classList.toggle('hidden', !dark);
  }

  const saved = localStorage.getItem('theme') ||
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light');
  applyTheme(saved);

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });

  // ========================
  // Activar Alira
  // ========================
  const toast = document.getElementById('toast');
  document.getElementById('activateBtn').addEventListener('click', async () => {
    try {
      const res = await fetch('/activar');
      const j = await res.json();
      showToast(j.status || 'Alira activada');
    } catch (e) {
      showToast('No se pudo activar');
    }
  });

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 1600);
  }

  // Refresh manual
  document.getElementById('refreshBtn').addEventListener('click', loadHistory);

  // Primera carga
  loadHistory();
  startPolling();