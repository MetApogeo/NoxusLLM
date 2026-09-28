/* ============================================================
   Nexus Roleplay – App Logic
   ============================================================ */

// ── State ────────────────────────────────────────────────────
const state = {
  sessionId:   localStorage.getItem('nx_session')   || 'session_demo_1',
  characterId: localStorage.getItem('nx_character') || 'char_eldrin',
  userName:    localStorage.getItem('nx_username')  || 'Jugador',
  apiBase:     localStorage.getItem('nx_api')       || '',
  isSending:   false,
};

// ── DOM refs ─────────────────────────────────────────────────
const chatBox       = document.getElementById('chat-box');
const inputMsg      = document.getElementById('input-msg');
const sendBtn       = document.getElementById('send-btn');
const charCount     = document.getElementById('char-count');
const chatIntro     = document.getElementById('chat-intro');
const settingsBtn   = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-overlay');
const closeSettings = document.getElementById('close-settings-btn');
const saveSettings  = document.getElementById('save-settings-btn');
const clearChatBtn  = document.getElementById('clear-chat-btn');
const cfgSession    = document.getElementById('cfg-session');
const cfgCharacter  = document.getElementById('cfg-character');
const cfgUsername   = document.getElementById('cfg-username');
const cfgApi        = document.getElementById('cfg-api');

// ── Helpers ──────────────────────────────────────────────────

/** Construye la URL base del backend. */
function apiUrl(path) {
  const base = state.apiBase || `http://${window.location.hostname}:8000`;
  return `${base.replace(/\/$/, '')}${path}`;
}

/** Elimina el mensaje intro si aún existe. */
function removeIntro() {
  if (chatIntro && chatIntro.parentNode) {
    chatIntro.style.opacity = '0';
    chatIntro.style.transition = 'opacity 300ms';
    setTimeout(() => chatIntro.remove(), 300);
  }
}

/**
 * Inserta una burbuja de mensaje en el chat.
 * @param {string} sender  – nombre visible del remitente
 * @param {string} text    – contenido inicial (puede ser vacío para streaming)
 * @param {'user'|'bot'} type
 * @returns {HTMLElement}  – el elemento .msg-bubble para actualizar su contenido
 */
function appendMessage(sender, text, type) {
  removeIntro();

  const wrapper = document.createElement('div');
  wrapper.className = `msg-wrapper ${type}`;

  const senderEl = document.createElement('span');
  senderEl.className = 'msg-sender';
  senderEl.textContent = sender;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = renderContent(text);

  wrapper.appendChild(senderEl);
  wrapper.appendChild(bubble);
  chatBox.appendChild(wrapper);
  scrollToBottom();
  return bubble;
}

/** Convierte texto plano con *acciones* en HTML con <em>. */
function renderContent(text) {
  // Escapa HTML primero
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Convierte *texto* en <em>texto</em>
  return escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

/** Inserción de indicador de escritura animado. */
function appendTypingIndicator() {
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper bot';
  wrapper.id = 'typing-indicator';

  const senderEl = document.createElement('span');
  senderEl.className = 'msg-sender';
  senderEl.textContent = state.characterId;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';

  wrapper.appendChild(senderEl);
  wrapper.appendChild(bubble);
  chatBox.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function scrollToBottom() {
  chatBox.scrollTop = chatBox.scrollHeight;
}

function setSending(value) {
  state.isSending = value;
  sendBtn.disabled = value;
  inputMsg.disabled = value;
}

// ── Send message ─────────────────────────────────────────────

async function sendMessage() {
  const text = inputMsg.value.trim();
  if (!text || state.isSending) return;

  inputMsg.value = '';
  charCount.textContent = '0';
  autoResizeTextarea();
  setSending(true);

  // Renderizar mensaje del usuario
  appendMessage(state.userName, text, 'user');

  // Mostrar indicador de escritura
  const typingEl = appendTypingIndicator();

  try {
    const response = await fetch(apiUrl('/api/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:   state.sessionId,
        character_id: state.characterId,
        user_name:    state.userName,
        content:      text,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    // Remover typing e insertar burbuja del bot
    removeTypingIndicator();
    const botBubble = appendMessage(state.characterId, '', 'bot');
    let rawText = '';

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') break;

        try {
          const parsed = JSON.parse(payload);
          if (parsed.chunk) {
            rawText += parsed.chunk;
            botBubble.innerHTML = renderContent(rawText);
            scrollToBottom();
          }
        } catch {
          // Fragmento SSE incompleto – ignorar
        }
      }
    }

  } catch (err) {
    removeTypingIndicator();
    appendMessage('Sistema', `⚠ Error: ${err.message}`, 'bot');
  } finally {
    setSending(false);
    inputMsg.focus();
  }
}

// ── Auto-resize textarea ──────────────────────────────────────

function autoResizeTextarea() {
  inputMsg.style.height = 'auto';
  inputMsg.style.height = `${Math.min(inputMsg.scrollHeight, 120)}px`;
}

inputMsg.addEventListener('input', () => {
  autoResizeTextarea();
  charCount.textContent = inputMsg.value.length;
});

inputMsg.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

// ── Settings modal ────────────────────────────────────────────

function openSettings() {
  cfgSession.value   = state.sessionId;
  cfgCharacter.value = state.characterId;
  cfgUsername.value  = state.userName;
  cfgApi.value       = state.apiBase;
  settingsModal.classList.remove('hidden');
  cfgSession.focus();
}

function closeSettingsModal() {
  settingsModal.classList.add('hidden');
}

settingsBtn.addEventListener('click', openSettings);
closeSettings.addEventListener('click', closeSettingsModal);
settingsModal.addEventListener('click', (e) => {
  if (e.target === settingsModal) closeSettingsModal();
});

saveSettings.addEventListener('click', () => {
  state.sessionId   = cfgSession.value.trim()   || state.sessionId;
  state.characterId = cfgCharacter.value.trim() || state.characterId;
  state.userName    = cfgUsername.value.trim()  || state.userName;
  state.apiBase     = cfgApi.value.trim();

  localStorage.setItem('nx_session',   state.sessionId);
  localStorage.setItem('nx_character', state.characterId);
  localStorage.setItem('nx_username',  state.userName);
  localStorage.setItem('nx_api',       state.apiBase);

  // Actualiza el label de sesión en el header
  document.getElementById('session-name').textContent = state.sessionId;

  closeSettingsModal();
});

clearChatBtn.addEventListener('click', () => {
  if (!confirm('¿Limpiar el chat? Solo borra la vista local, no el historial del servidor.')) return;
  // Vaciar el chatBox y restaurar intro
  chatBox.innerHTML = '';
  const intro = document.createElement('div');
  intro.className = 'chat-intro';
  intro.id = 'chat-intro';
  intro.innerHTML = '<div class="intro-rune">⬡</div><p>La sesión ha comenzado.<br>Escribe tu primera acción o pregunta.</p>';
  chatBox.appendChild(intro);
  closeSettingsModal();
});

// ── Keyboard shortcut: Escape closes modal ────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeSettingsModal();
});

// ── Init ─────────────────────────────────────────────────────
document.getElementById('session-name').textContent = state.sessionId;
inputMsg.focus();
