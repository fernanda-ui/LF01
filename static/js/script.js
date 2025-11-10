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
  // Preferir contenedor específico si existe
  const container = document.getElementById('chatOutputWeb') || chatArea;
  // Guardar estado de scroll para decidir autoscroll y preservar posición si el usuario está arriba
  const wasNearBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) < 120;
  const prevScrollTop = container.scrollTop;
  // Asegurar track interno centrado
  let track = container.querySelector('.chat-track');
  if (!track) {
    container.innerHTML = '';
    track = document.createElement('div');
    track.className = 'chat-track';
    container.appendChild(track);
  } else {
    track.innerHTML = '';
  }
  // Añadir mensajes en orden (antiguos -> nuevos)
  msgs.forEach(m => {
    const div = document.createElement('div');
    // Usar clases de estilo existentes
    const isUser = m.tipo === 'usuario';
    div.className = isUser ? 'mensaje-usuario' : 'mensaje-ia';
    const safeMessage = /<a\s+href=/.test(m.mensaje) ? m.mensaje : escapeHtml(m.mensaje);
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = safeMessage;
    div.appendChild(content);

    if (!isUser) {
      const actions = document.createElement('div');
      actions.className = 'message-actions';
      const copyBtn = document.createElement('button');
      copyBtn.className = 'icon-btn';
      copyBtn.title = 'Copiar';
      copyBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="12" height="12" rx="2" ry="2"></rect>
          <path d="M5 15V5a2 2 0 0 1 2-2h10" />
        </svg>`;
      copyBtn.onclick = () => { navigator.clipboard.writeText(content.textContent || ''); showToast('Copiado'); };
      const likeBtn = document.createElement('button');
      likeBtn.className = 'icon-btn';
      likeBtn.title = 'Me gusta';
      likeBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-1 6H5.5A2.5 2.5 0 0 0 3 10.5v1.8c0 .4.06.79.17 1.17l1.26 4.41A3 3 0 0 0 7.32 20H14a4 4 0 0 0 4-4v-5a2 2 0 0 0-2-2h-2z" />
        </svg>`;
      const dislikeBtn = document.createElement('button');
      dislikeBtn.className = 'icon-btn';
      dislikeBtn.title = 'No me gusta';
      dislikeBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(180deg);">
          <path d="M14 9V5a3 3 0 0 0-3-3l-1 6H5.5A2.5 2.5 0 0 0 3 10.5v1.8c0 .4.06.79.17 1.17l1.26 4.41A3 3 0 0 0 7.32 20H14a4 4 0 0 0 4-4v-5a2 2 0 0 0-2-2h-2z" />
        </svg>`;
      likeBtn.onclick = () => { likeBtn.classList.toggle('active'); dislikeBtn.classList.remove('active'); showToast('Gracias ❤️'); };
      dislikeBtn.onclick = () => { dislikeBtn.classList.toggle('active'); likeBtn.classList.remove('active'); showToast('Gracias 💬'); };
      actions.append(copyBtn, likeBtn, dislikeBtn);
      div.appendChild(actions);
    }

    track.appendChild(div);
  });
  // Autoscroll sólo si ya estabas cerca del final; si no, intenta preservar la posición
  if (wasNearBottom) {
    container.scrollTop = container.scrollHeight;
  } else {
    container.scrollTop = prevScrollTop;
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
  // Asegurar que exista grupo del día actual aunque no haya mensajes
  if (!groups[todayKey()]) groups[todayKey()] = [];
  state.sessions = groups;
  // Seleccionar el día actual por defecto si no hay selección válida
  const sortedKeys = Object.keys(groups).sort((a, b) => new Date(b) - new Date(a));
  if (!state.sessions[state.activeKey]) state.activeKey = todayKey();
        renderChatList();
        renderChatArea();
    } catch (e) {
        console.error('Error cargando historial', e);
    }
}


// ========================
// Tema claro/oscuro
// ========================
const logoDark = document.getElementById("logoDark");
const logoLight = document.getElementById("logoLight");

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  const dark = theme === 'dark';
  // Solo alterna logos; el botón sol/luna fue eliminado
  logoDark.classList.toggle('hidden', dark);
  logoLight.classList.toggle('hidden', !dark);
}

const saved = localStorage.getItem('theme') ||
  (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light');
applyTheme(saved);
// ========================
// Activar / Desactivar Iris con estado persistente
// ========================
const toast = document.getElementById('toast');
const activateBtn = document.getElementById('activateBtn');
const loader = document.getElementById('loader');
const fabImg = document.getElementById('fabImg');

// Usamos sessionStorage para que cada sesión de login empiece en OFF por defecto.
// Si en esta sesión ya se activó manualmente, respetamos ese estado.
const IRIS_SESSION_FLAG = 'irisSessionActivated';
let irisActiva = localStorage.getItem('irisActiva') === 'true';
if (!sessionStorage.getItem(IRIS_SESSION_FLAG)) {
  // Nueva sesión: forzar OFF visual y lógico
  irisActiva = false;
  localStorage.setItem('irisActiva', 'false');
}

// Estado inicial del botón según irisActiva (limpiando clase opuesta para evitar verde inesperado)
if (irisActiva) {
  activateBtn.classList.remove('off');
  activateBtn.classList.add('on');
} else {
  activateBtn.classList.remove('on');
  activateBtn.classList.add('off');
}

// Actualiza el tooltip/aria-label según el estado (verde=Desactivar, rojo=Activar)
function updateIrisTooltip() {
  if (irisActiva) {
    activateBtn.title = 'Desactivar Iris';
    activateBtn.setAttribute('aria-label', 'Desactivar Iris');
  } else {
    activateBtn.title = 'Activar Iris';
    activateBtn.setAttribute('aria-label', 'Activar Iris');
  }
}

// Ajuste inicial del tooltip
updateIrisTooltip();


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
  sessionStorage.setItem(IRIS_SESSION_FLAG, 'true');
      activateBtn.classList.remove('off');
      activateBtn.classList.add('on');
  updateIrisTooltip();
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
  sessionStorage.removeItem(IRIS_SESSION_FLAG);
      activateBtn.classList.remove('on');
      activateBtn.classList.add('off');
  updateIrisTooltip();
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
const voiceStopBtn = document.getElementById('voiceStopBtn');
const chatOutputWeb = document.getElementById('chatOutputWeb');
// ===== Notificaciones y Recordatorios =====
const notifBell = document.getElementById('notifBell');
const reminderModal = document.getElementById('reminderModal');
const closeReminderModal = document.getElementById('closeReminderModal');
const reminderForm = document.getElementById('reminderForm');
const reminderListPending = document.getElementById('reminderListPending');
const reminderListNotified = document.getElementById('reminderListNotified');
const notificationsModal = document.getElementById('notificationsModal');
const closeNotificationsModal = document.getElementById('closeNotificationsModal');
const notificationsList = document.getElementById('notificationsList');
const markAllReadBtn = document.getElementById('markAllRead');
const dueBadge = document.getElementById('dueBadge');
const openReminderPanelBtn = document.getElementById('openReminderPanel');

let remindersCache = [];
let notificationsCache = [];

function toggleReminderModal(show=true){
  reminderModal.classList.toggle('hidden', !show);
  if(show){
    // Enfocar campo mensaje
    document.getElementById('reminderText')?.focus();
    document.body.classList.add('modal-open');
  }
  else {
    document.body.classList.remove('modal-open');
  }
}
// La campana ahora abre Notificaciones (no recordatorios) y refresca lista al abrir
notifBell?.addEventListener('click', async ()=>{ await fetchNotifications(); toggleNotificationsModal(true); });
closeReminderModal?.addEventListener('click',()=> toggleReminderModal(false));
// Abrir modal desde el botón Panel (sidebar)
openReminderPanelBtn?.addEventListener('click',()=> toggleReminderModal(true));

async function fetchReminders(){
  try { const r = await fetch('/reminders'); if(!r.ok) return; const j = await r.json(); remindersCache = j || []; renderReminders(); } catch(e){ console.error('Error fetchReminders', e);} }

function renderReminders(){
  if(!reminderListPending || !reminderListNotified) return;
  reminderListPending.innerHTML='';
  reminderListNotified.innerHTML='';
  remindersCache.forEach(r=>{
    const li = document.createElement('li');
    li.className='reminder-item';
    li.innerHTML = `<div><strong>${escapeHtml(r.message)}</strong><div class=\"meta\">${r.due_at} · ${r.status}</div></div><button class=\"del\" data-id=\"${r.id}\">✕</button>`;
    if(r.status === 'pendiente'){
      reminderListPending.appendChild(li);
    } else {
      reminderListNotified.appendChild(li);
    }
  });
  [...document.querySelectorAll('.reminder-item .del')].forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const id = btn.getAttribute('data-id');
      try { await fetch(`/reminders/${id}`, {method:'DELETE'}); await fetchReminders(); } catch(e){ console.error('Error delete', e);} }
    );
  });
  // Auto-scroll hacia el inicio (pendientes arriba) si hay overflow
  const scrollArea = document.getElementById('remindersScrollArea');
  if(scrollArea){ scrollArea.scrollTop = 0; }
}

reminderForm?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const time = document.getElementById('reminderTime').value;
  const text = document.getElementById('reminderText').value.trim();
  if(!time){ showToast('Selecciona una hora'); document.getElementById('reminderTime').focus(); return; }
  if(!text){ showToast('Escribe el mensaje'); document.getElementById('reminderText').focus(); return; }
  try {
    const res = await fetch('/reminders', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({time, message:text})});
    if(res.ok){
      const j = await res.json();
      showToast('Recordatorio creado');
      document.getElementById('reminderText').value='';
      await fetchReminders();
      toggleReminderModal(false);
    } else {
      const msg = await res.text();
      showToast('Error creando recordatorio');
      console.error('POST /reminders error:', msg);
    }
  } catch(e){ console.error('Error new reminder', e);} 
});

// Poll periódicamente para refrescar (cada 35s)
setInterval(fetchReminders, 35000);
fetchReminders();

// (removido) panel inferior: ahora todo va por modal
// Cerrar modal al hacer click fuera del contenido
reminderModal?.addEventListener('click', (e)=>{
  if(e.target === reminderModal) toggleReminderModal(false);
});

// Cerrar modal con tecla ESC
document.addEventListener('keydown', (e)=>{
  if(e.key === 'Escape' && !reminderModal.classList.contains('hidden')){
    toggleReminderModal(false);
  }
  if(e.key === 'Escape' && notificationsModal && !notificationsModal.classList.contains('hidden')){
    toggleNotificationsModal(false);
  }
});

// ========================
// Notificaciones
// ========================
function toggleNotificationsModal(show=true){
  notificationsModal.classList.toggle('hidden', !show);
  if(show){ document.body.classList.add('modal-open'); }
  else { document.body.classList.remove('modal-open'); }
}

closeNotificationsModal?.addEventListener('click', ()=> toggleNotificationsModal(false));
notificationsModal?.addEventListener('click', (e)=>{ if(e.target === notificationsModal) toggleNotificationsModal(false); });

async function fetchNotifications(){
  try { const r = await fetch('/notifications'); if(!r.ok) return; const j = await r.json(); notificationsCache = j || []; renderNotifications(); } catch(e){ console.error('Error fetchNotifications', e);} }

function renderNotifications(){
  notificationsList.innerHTML='';
  let unread = 0;
  notificationsCache.forEach(n=>{
    const li = document.createElement('li');
    li.className = 'reminder-item';
    if(!n.is_read) unread++;
    const title = n.title || 'Recordatorio';
    li.innerHTML = `<div${n.is_read? '':' style=\"font-weight:600;\"'}><strong>${title}</strong><div class=\"meta\">${n.created_at}</div><div>${n.body}</div></div>`;
    notificationsList.appendChild(li);
  });
  if(unread>0){ dueBadge.textContent = unread; dueBadge.classList.remove('hidden'); } else { dueBadge.classList.add('hidden'); }
}

markAllReadBtn?.addEventListener('click', async ()=>{
  try { const r = await fetch('/notifications/mark_all_read', {method:'POST'}); if(r.ok){ await fetchNotifications(); } } catch(e){ console.error('markAllRead error', e);} 
});

// Poll de notificaciones
setInterval(fetchNotifications, 30000);
fetchNotifications();

// ========================
// Mensajes (usuario/IA) con acciones para la IA
// ========================
function getFirstName() {
  try {
    const userData = JSON.parse(document.getElementById('userData').textContent);
    return (userData.first_name || '').split(' ')[0] || 'Usuario';
  } catch {
    return 'Usuario';
  }
}

function renderTitlesAndClean(text) {
  // Convierte líneas que empiezan con * o ** en títulos en mayúsculas, elimina los asteriscos
  return text.split(/\n/).map(line => {
    const titleMatch = line.match(/^\s*\*{1,2}([^*]+)\*{1,2}\s*$/);
    if (titleMatch) {
      return `<div style='margin:10px 0 4px 0;font-weight:700;'>${titleMatch[1].trim().toUpperCase()}</div>`;
    }
    // Elimina asteriscos sueltos
    return line.replace(/\*{1,2}/g, '');
  }).join('<br>');
}

function agregarMensajeWeb(user, texto) {
  const chatContainer = document.getElementById('chatOutputWeb');
  const nearBottom = (chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight) < 120;
  let track = chatContainer.querySelector('.chat-track');
  if (!track) {
    track = document.createElement('div');
    track.className = 'chat-track';
    chatContainer.appendChild(track);
  }
  const div = document.createElement('div');
  div.className = user === 'user' ? 'mensaje-usuario' : 'mensaje-ia';
  const content = document.createElement('div');
  content.className = 'message-content';
  if (user === 'ia') {
    // Saludo personalizado y renderizado de títulos
    const nombre = getFirstName();
    content.innerHTML = `<span style='color:var(--accent-500);font-weight:600;'>${nombre},</span> ` + renderTitlesAndClean(texto);
  } else {
    content.textContent = texto;
  }
  div.appendChild(content);
  // ...acciones IA...
  if (user === 'ia') {
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    const copyBtn = document.createElement('button');
    copyBtn.className = 'icon-btn';
    copyBtn.title = 'Copiar';
    copyBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="12" height="12" rx="2" ry="2"></rect>
        <path d="M5 15V5a2 2 0 0 1 2-2h10" />
      </svg>`;
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(content.textContent || '');
      showToast('Copiado');
    };

    const likeBtn = document.createElement('button');
    likeBtn.className = 'icon-btn';
    likeBtn.title = 'Me gusta';
    likeBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 9V5a3 3 0 0 0-3-3l-1 6H5.5A2.5 2.5 0 0 0 3 10.5v1.8c0 .4.06.79.17 1.17l1.26 4.41A3 3 0 0 0 7.32 20H14a4 4 0 0 0 4-4v-5a2 2 0 0 0-2-2h-2z" />
      </svg>`;
    likeBtn.onclick = () => {
      likeBtn.classList.toggle('active');
      dislikeBtn.classList.remove('active');
      showToast('Gracias ❤️');
    };

    const dislikeBtn = document.createElement('button');
    dislikeBtn.className = 'icon-btn';
    dislikeBtn.title = 'No me gusta';
    dislikeBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(180deg);">
        <path d="M14 9V5a3 3 0 0 0-3-3l-1 6H5.5A2.5 2.5 0 0 0 3 10.5v1.8c0 .4.06.79.17 1.17l1.26 4.41A3 3 0 0 0 7.32 20H14a4 4 0 0 0 4-4v-5a2 2 0 0 0-2-2h-2z" />
      </svg>`;
    dislikeBtn.onclick = () => {
      dislikeBtn.classList.toggle('active');
      likeBtn.classList.remove('active');
      showToast('Gracias 💬');
    };

    actions.append(copyBtn, likeBtn, dislikeBtn);
    div.appendChild(actions);
  }
  track.appendChild(div);
  // Sólo baja si el usuario ya estaba al fondo o si es un mensaje propio
  if (nearBottom || user === 'user') {
    scrollToBottom(chatContainer);
  }
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

    if (data.ok) {
      agregarMensajeWeb('ia', data.ia_message);
      // Guardar el mensaje en el historial local para que no desaparezca
      if (!state.sessions[state.activeKey]) state.sessions[state.activeKey] = [];
      state.sessions[state.activeKey].push({ tipo: 'usuario', mensaje });
      state.sessions[state.activeKey].push({ tipo: 'ia', mensaje: data.ia_message });
      renderChatArea();

      // Mostrar botón de detener voz si está hablando
      if (data.speaking && voiceStopBtn) {
        voiceStopBtn.classList.remove('hidden');
        voiceStopBtn.classList.remove('stop');
      }
    } else {
      agregarMensajeWeb('ia', "Error: " + (data.error || "No se pudo obtener respuesta"));
    }
  } catch (err) {
    agregarMensajeWeb('ia', "Error de conexión");
  } finally {
    chatInputWeb.disabled = false;
    sendBtnWeb.disabled = false;
    chatInputWeb.focus();
  }
}

sendBtnWeb.addEventListener('click', enviarMensajeWeb);
chatInputWeb.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); enviarMensajeWeb(); }
});

// ========================
// Control de voz (botón detener)
// ========================
async function pollTtsStatusOnce() {
  try {
    const r = await fetch('/tts_status', { credentials: 'include' });
    const j = await r.json();
    if (j.speaking) {
      voiceStopBtn.classList.remove('hidden');
    } else {
      voiceStopBtn.classList.add('hidden');
      voiceStopBtn.classList.remove('stop');
    }
  } catch {}
}

// Consultar estado al cargar y cada 700 ms mientras esté visible
let ttsPoll = null;
function startTtsPolling() {
  if (ttsPoll) return;
  ttsPoll = setInterval(pollTtsStatusOnce, 700);
}
function stopTtsPolling() {
  if (!ttsPoll) return;
  clearInterval(ttsPoll);
  ttsPoll = null;
}

// Iniciar una consulta al inicio
pollTtsStatusOnce();
startTtsPolling();

if (voiceStopBtn) {
  voiceStopBtn.addEventListener('click', async () => {
    try {
      voiceStopBtn.classList.add('stop');
      const r = await fetch('/stop_tts', { method: 'POST', credentials: 'include' });
      const j = await r.json();
      if (j.stopped || j.speaking === false) {
        voiceStopBtn.classList.add('hidden');
        voiceStopBtn.classList.remove('stop');
      }
    } catch (e) {
      // En caso de error, intentamos ocultar igualmente tras un momento
      setTimeout(()=>{
        voiceStopBtn.classList.add('hidden');
        voiceStopBtn.classList.remove('stop');
      }, 800);
    }
  });
}


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

  // ========================
  // Modal Configuración
  // ========================
  const openSettingsLink = document.getElementById('openSettings');
  const settingsModal = document.getElementById('settingsModal');
  const settingsBackdrop = document.getElementById('settingsBackdrop');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const themeSelect = document.getElementById('themeSelect');
  const autoStartToggle = document.getElementById('autoStartToggle');
  const accentGrid = document.getElementById('accentGrid');
  const decreaseTextBtn = document.getElementById('decreaseTextBtn');
  const increaseTextBtn = document.getElementById('increaseTextBtn');
  const resetTextBtn = document.getElementById('resetTextBtn');
  const textSizeDisplay = document.getElementById('textSizeDisplay');

  let baseFontPercent = parseInt(localStorage.getItem('appTextSize')||'100');
  // Para control de foco accesible en modal
  let previouslyFocused = null;
  updateTextSizeDisplay();
  applyStoredAccent();
  applyStoredThemeSelection();
  autoStartToggle.checked = localStorage.getItem('autoStart') === 'true';

  function openSettings() {
    settingsBackdrop.hidden = false;
    settingsModal.hidden = false;
    document.body.classList.add('modal-open');
    previouslyFocused = document.activeElement;
    requestAnimationFrame(()=>{
      settingsBackdrop.classList.add('active');
      settingsModal.classList.add('active');
      // Foco al primer elemento interactivo
      const first = settingsModal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (first) first.focus();
    });
    document.addEventListener('keydown', trapFocusHandler);
  }
  function closeSettings() {
    settingsBackdrop.classList.remove('active');
    settingsModal.classList.remove('active');
    document.body.classList.remove('modal-open');
    document.removeEventListener('keydown', trapFocusHandler);
    setTimeout(()=>{
      settingsBackdrop.hidden = true;
      settingsModal.hidden = true;
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus();
      }
    },180);
  }

  function trapFocusHandler(e){
    if (settingsModal.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); closeSettings(); return; }
    if (e.key !== 'Tab') return;
    const focusable = Array.from(settingsModal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
      .filter(el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));
    if (!focusable.length) return;
    const firstEl = focusable[0];
    const lastEl = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === firstEl) {
      e.preventDefault();
      lastEl.focus();
    } else if (!e.shiftKey && document.activeElement === lastEl) {
      e.preventDefault();
      firstEl.focus();
    }
  }

  if (openSettingsLink) openSettingsLink.addEventListener('click', e => { e.preventDefault(); openSettings(); });
  if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', closeSettings);
  if (settingsBackdrop) settingsBackdrop.addEventListener('click', closeSettings);
  // Escape y Tab gestionados en trapFocusHandler

  // Navegación entre secciones
  settingsModal.addEventListener('click', e => {
    if (e.target.classList.contains('settings-tab')) {
      settingsModal.querySelectorAll('.settings-tab').forEach(btn=>btn.classList.remove('active'));
      e.target.classList.add('active');
      const section = e.target.dataset.section;
      settingsModal.querySelectorAll('.settings-section').forEach(sec=>{
        sec.classList.toggle('active', sec.dataset.section===section);
      });
    }
  });

  // Tema
  themeSelect.addEventListener('change', ()=>{
    const val = themeSelect.value;
    localStorage.setItem('themePref', val);
    if (val === 'system') {
      const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      applyTheme(sysDark? 'dark':'light');
    } else {
      applyTheme(val);
    }
  });
  function applyStoredThemeSelection(){
    const pref = localStorage.getItem('themePref');
    if (!pref) return; themeSelect.value = pref;
    if (pref === 'system') {
      const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      applyTheme(sysDark? 'dark':'light');
    } else applyTheme(pref);
  }

  // AutoStart
  autoStartToggle.addEventListener('change', ()=>{
    localStorage.setItem('autoStart', autoStartToggle.checked ? 'true':'false');
  });

  // Acento
  function getUserPrefKey(base){
    try {
      const u = JSON.parse(document.getElementById('userData').textContent)||{};
      const idk = u.id || u.username || u.email || 'default';
      return `${base}:${idk}`;
    } catch { return `${base}:default`; }
  }
  accentGrid.addEventListener('click', e => {
    const btn = e.target.closest('.accent-option');
    if (!btn) return;
    accentGrid.querySelectorAll('.accent-option').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const color = btn.dataset.accent;
    applyAccent(color, true);
  });
  function applyAccent(color, persist){
    const root = document.documentElement;
    root.style.setProperty('--accent-500', color);
    root.style.setProperty('--accent-600', color);
    root.style.setProperty('--accent-700', color);
    if (persist){ localStorage.setItem(getUserPrefKey('accentColor'), color); }
  }
  function applyStoredAccent(){
    const key = getUserPrefKey('accentColor');
    const c = localStorage.getItem(key);
    if (!c){
      // default rojo (#ef4444) ya está en CSS, marcar botón rojo
      const def = accentGrid.querySelector('[data-accent="#ef4444"]');
      if (def){ accentGrid.querySelectorAll('.accent-option').forEach(b=>b.classList.remove('active')); def.classList.add('active'); }
      return;
    }
    applyAccent(c, false);
    const match = accentGrid.querySelector(`[data-accent="${c}"]`);
    if (match) { accentGrid.querySelectorAll('.accent-option').forEach(b=>b.classList.remove('active')); match.classList.add('active'); }
  }

  // Tamaño de texto
  decreaseTextBtn.addEventListener('click', ()=>{ changeTextSize(-10); });
  increaseTextBtn.addEventListener('click', ()=>{ changeTextSize(10); });
  resetTextBtn.addEventListener('click', ()=>{ baseFontPercent = 100; applyTextSize(); });
  function changeTextSize(delta){
    baseFontPercent = Math.min(140, Math.max(70, baseFontPercent + delta));
    applyTextSize();
  }
  function applyTextSize(){
    document.documentElement.style.fontSize = (baseFontPercent/100 * 14) + 'px';
    localStorage.setItem('appTextSize', String(baseFontPercent));
    updateTextSizeDisplay();
  }
  function updateTextSizeDisplay(){ textSizeDisplay.textContent = baseFontPercent + '%'; }
  applyTextSize();

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


