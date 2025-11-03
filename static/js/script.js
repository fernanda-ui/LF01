// ========================
// Utilidades de fecha
// ========================
function todayKey() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function friendlyDate(key) {
    const [y, m, d] = key.split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    const td = new Date();
    const same = dt.toDateString() === new Date(td.getFullYear(), td.getMonth(), td.getDate()).toDateString();
    if (same) return 'Hoy';
    const yesterday = new Date(td);
    yesterday.setDate(td.getDate() - 1);
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
  // 🔹 Ordenar por fecha descendente: más reciente primero
  const keys = Object.keys(state.sessions)
    .sort((a, b) => new Date(b) - new Date(a)); // 👈 esto invierte correctamente

  chatList.innerHTML = '';

  // 🔹 Insertar en orden correcto (no uses prepend aquí)
  keys.forEach(key => {
    const item = document.createElement('div');
    item.className = 'chat-item' + (key === state.activeKey ? ' active' : '');
    item.innerHTML = `
      <div style="
        width:28px;height:28px;
        border-radius:8px;
        background: radial-gradient(60% 60% at 40% 40%, var(--accent-500), var(--accent-700));
        display:grid; place-items:center;
        color:#fff; font-weight:800; font-size:13px;">
        ${friendlyDate(key).slice(0,1)}
      </div>
      <div>
        <div class="chat-title">${friendlyDate(key)}</div>
        <div class="chat-date">${key}</div>
      </div>
      <div style="font-size:11px; color: var(--muted);">
        ${state.sessions[key].length} msgs
      </div>
    `;

    // 🔹 Insertar en orden visual (arriba → abajo)
    chatList.appendChild(item);

    item.addEventListener('click', () => {
      state.activeKey = key;
      renderChatList();
      renderChatArea();
    });
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
  // Añadir mensajes en orden (antiguos -> nuevos)
  msgs.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + (m.tipo === 'usuario' ? 'user' : 'alira');
    const safeMessage = /<a\s+href=/.test(m.mensaje) ? m.mensaje : escapeHtml(m.mensaje);
    div.innerHTML = `<div>${safeMessage}</div>`;
    chatArea.appendChild(div);
  });
  // Forzar scroll al final para mostrar los mensajes más recientes
  try {
    chatArea.scrollTop = chatArea.scrollHeight;
  } catch (e) {
    scrollToBottom(chatArea);
  }
}

// ✅ Función confiable de scroll automático
function scrollToBottom(container) {
    const isNearBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight < 100;

    // Solo baja automáticamente si ya está al fondo
    if (isNearBottom) {
        requestAnimationFrame(() => {
            container.scroll({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
        });
    }
}


function escapeHtml(str) {
    return str.replace(/[&<>"']/g, s => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
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
                const k = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`;
                key = k;
            }
            if (!groups[key]) groups[key] = [];
            groups[key].push(m);
        });
    state.sessions = groups;
    // Seleccionar la sesión/día más reciente automáticamente
    const sortedKeys = Object.keys(groups).sort((a, b) => new Date(b) - new Date(a));
    if (!state.sessions[state.activeKey]) state.activeKey = sortedKeys[0] || todayKey();
        renderChatList();
        renderChatArea();
    } catch (e) {
        console.error('Error cargando historial', e);
    }
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
// Activar / Desactivar Iris con estado persistente
// ========================
const toast = document.getElementById('toast');
const activateBtn = document.getElementById('activateBtn');
const loader = document.getElementById('loader');
const fabImg = document.getElementById('fabImg');
let irisActiva = localStorage.getItem('irisActiva') === 'true'; // Cargar estado guardado

// Estado inicial
if (irisActiva) {
  activateBtn.classList.add('on');
} else {
  activateBtn.classList.add('off');
}


activateBtn.addEventListener('click', async () => {
  loader.classList.remove('hidden');
  fabImg.classList.add('hidden');
  activateBtn.disabled = true;

  if (!irisActiva) {
    // === ACTIVAR ===
    try {
      const res = await fetch('/activar');
      const j = await res.json();
      irisActiva = true;
      localStorage.setItem('irisActiva', 'true');
      activateBtn.classList.remove('off');
      activateBtn.classList.add('on');
      showToast(j.status || 'Iris activada');
      await loadHistory(); // Refresca historial y mensajes tras activar
    } catch (e) {
      showToast('No se pudo activar Iris');
    }
  } else {
    // === DESACTIVAR ===
    try {
      const res = await fetch('/desactivar');
      const j = await res.json();
      irisActiva = false;
      localStorage.setItem('irisActiva', 'false');
      activateBtn.classList.remove('on');
      activateBtn.classList.add('off');
      showToast(j.status || 'Iris desactivada');
      await loadHistory(); // Refresca historial y mensajes tras desactivar
    } catch (e) {
      showToast('Error al desactivar Iris');
    }
  }

  setTimeout(() => {
    loader.classList.add('hidden');
    fabImg.classList.remove('hidden');
    activateBtn.disabled = false;
  }, 1000);
});

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 1600);
}

// ========================
// Menú usuario
// ========================
const userMetaBtn = document.getElementById("userMetaBtn");
const profileMenu = document.getElementById("profileMenu");

userMetaBtn.addEventListener("click", () => {
    profileMenu.style.display = profileMenu.style.display === "none" ? "block" : "none";
});

document.addEventListener("click", (e) => {
    if (!userMetaBtn.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.style.display = "none";
    }
});
// ========================
// Chat Web
// ========================
const chatInputWeb = document.getElementById('chatInputWeb');
const sendBtnWeb = document.getElementById('sendBtnWeb');
const chatOutputWeb = document.getElementById('chatOutputWeb');

// Mensaje del usuario o texto simple
function agregarMensajeWeb(user, texto) {
  const div = document.createElement('div');
  div.className = user === 'user' ? 'mensaje-usuario' : 'mensaje-ia';
  div.textContent = texto;

  const isNearBottom =
    chatOutputWeb.scrollHeight - chatOutputWeb.scrollTop - chatOutputWeb.clientHeight < 100;

  chatOutputWeb.appendChild(div);

  if (isNearBottom) {
    chatOutputWeb.scrollTop = chatOutputWeb.scrollHeight;
  }
}

// ========================
// Mensajes de Iris con iconos
// ========================
function agregarMensajeWeb(user, texto) {
  const chatContainer = document.getElementById('chatOutputWeb');

  const div = document.createElement('div');
  div.className = user === 'user' ? 'mensaje-usuario' : 'mensaje-ia';

  const content = document.createElement('div');
  content.className = 'message-content';
  content.textContent = texto;
  div.appendChild(content);

  // Si es la IA, añadimos los íconos
  if (user === 'ia') {
    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'icon-btn';
    copyBtn.title = 'Copiar';
    copyBtn.innerHTML = '📋';
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(texto);
      showToast('Texto copiado');
    };

    const likeBtn = document.createElement('button');
    likeBtn.className = 'icon-btn';
    likeBtn.title = 'Me gusta';
    likeBtn.innerHTML = '👍';
    likeBtn.onclick = () => {
      likeBtn.classList.toggle('active');
      dislikeBtn.classList.remove('active');
      showToast('Gracias ❤️');
    };

    const dislikeBtn = document.createElement('button');
    dislikeBtn.className = 'icon-btn';
    dislikeBtn.title = 'No me gusta';
    dislikeBtn.innerHTML = '👎';
    dislikeBtn.onclick = () => {
      dislikeBtn.classList.toggle('active');
      likeBtn.classList.remove('active');
      showToast('Gracias 💬');
    };

    actions.append(copyBtn, likeBtn, dislikeBtn);
    div.appendChild(actions);
  }

  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}


// ========================
// Enviar mensaje
// ========================
async function enviarMensajeWeb() {
  const mensaje = chatInputWeb.value.trim();
  if (!mensaje) return;

  agregarMensajeWeb('user', mensaje);
  chatInputWeb.value = '';
  chatInputWeb.disabled = true;
  sendBtnWeb.disabled = true;

  try {
    const res = await fetch('/send_message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: mensaje }),
      credentials: 'include'
    });
    const data = await res.json();

    // Refresca historial y mensajes tras enviar
    await loadHistory();

    if (data.ok) {
      agregarMensajeIAConAcciones(data.ia_message);
    } else {
      agregarMensajeIAConAcciones("Error: " + (data.error || "No se pudo obtener respuesta"));
    }
  } catch (err) {
    agregarMensajeIAConAcciones("Error de conexión");
  } finally {
    chatInputWeb.disabled = false;
    sendBtnWeb.disabled = false;
    chatInputWeb.focus();
  }
}

sendBtnWeb.addEventListener('click', enviarMensajeWeb);
chatInputWeb.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') enviarMensajeWeb();
});


// ========================
// Inicialización
// ========================

// ========================
// startPolling (ahora usa loadHistory para refrescar historial y mensajes)
// ========================
function startPolling() {
  if (state.polling) clearInterval(state.polling);
  state.polling = setInterval(async () => {
    try {
      await loadHistory();
    } catch (err) {
      console.error('Error en startPolling:', err);
    }
  }, 3000);
}

// Carga inicial del historial y comienza el polling
loadHistory();
startPolling();


document.addEventListener('DOMContentLoaded', () => {
  // ========================
  // Ocultar / Mostrar sidebar (botón junto al theme)
  // ========================
  const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
  const sidebarEl = document.querySelector('.sidebar');
  const appEl = document.querySelector('.app');
  const arrowIcon = document.getElementById('arrowIcon');

  // Protección por si no existen (evita errores)
  if (toggleSidebarBtn && sidebarEl && appEl && arrowIcon) {
    // Restaurar estado (opcional)
    const savedCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (savedCollapsed) {
      sidebarEl.classList.add('collapsed');
      appEl.classList.add('sidebar-collapsed');
      arrowIcon.textContent = '▶';
    } else {
      arrowIcon.textContent = '◀';
    }

    toggleSidebarBtn.addEventListener('click', () => {
      const willCollapse = !sidebarEl.classList.contains('collapsed');

      // toggle classes
      sidebarEl.classList.toggle('collapsed', willCollapse);
      appEl.classList.toggle('sidebar-collapsed', willCollapse);

      // cambiar flecha (texto) y rotación visual
      arrowIcon.textContent = willCollapse ? '▶' : '◀';

      // persistir estado
      localStorage.setItem('sidebarCollapsed', willCollapse ? 'true' : 'false');
    });
  } else {
    // si falta algo, lo anotamos en consola (ayuda al debug)
    console.warn('toggleSidebarBtn o elementos relacionados no encontrados en DOM.');
  }
});


