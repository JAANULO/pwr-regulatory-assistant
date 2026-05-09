# Instrukcje redesignu UI — Asystent Regulaminowy PWr
> Autor oryginalny: JAANULO | Repo: https://github.com/JAANULO/model | Deploy: https://model-wp08.onrender.com

---

## 1. Kontekst projektu

Projekt to webowy asystent czatowy oparty na **Flasku** (Python), który odpowiada na pytania o regulamin studiów PWr. Backend używa wyszukiwarki BM25/TF-IDF + Mini-GPT (własna implementacja Transformer). Aplikacja hostowana na Render.com.

**Obecna struktura plików (zakładana na podstawie typowego projektu Flask):**
```
v2/
├── main.py              ← serwer Flask, trasy HTTP
├── transformer.py
├── tokenizer.py
├── wyszukiwarka.py
├── parser.py
├── dane.json
├── regulamin.pdf
├── baza_wiedzy.json
├── templates/
│   └── index.html       ← główny szablon HTML (TUTAJ GŁÓWNE ZMIANY)
└── static/
    ├── logo.png
    ├── style.css         ← główny arkusz CSS (TUTAJ GŁÓWNE ZMIANY)
    └── script.js         ← logika frontendu (TUTAJ DROBNE ZMIANY)
```

> **Jeśli `templates/` lub `static/` nie istnieją** — stwórz je. Flask wymaga tej struktury.

---

## 2. Cel redesignu

Zastąpić obecny prosty interfejs **profesjonalnym, dwupanelowym layoutem czatu** z:
- lewym panelem (sidebar) z historią rozmów
- prawym panelem (główny czat) z wiadomościami, sugestiami i polem input
- ciemno-niebieską paletą kolorów nawiązującą do PWr
- animowanym wskaźnikiem "pisania" (typing indicator)
- badge'ami z nazwą paragrafu źródłowego przy każdej odpowiedzi bota

---

## 3. Paleta kolorów i zmienne CSS

Wstaw na początku pliku `static/style.css`:

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f3;
  --bg-tertiary: #ebebea;
  --bg-sidebar: #0a0a0a;
  --text-primary: #1a1a1a;
  --text-secondary: #6b6b6b;
  --text-tertiary: #a0a0a0;
  --text-on-dark: #e8e8e8;
  --text-muted-dark: #8a8a8a;
  --accent: #042C53;
  --accent-hover: #0C447C;
  --accent-light: #E6F1FB;
  --accent-text: #185FA5;
  --border: rgba(0,0,0,0.08);
  --border-medium: rgba(0,0,0,0.12);
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 18px;
  --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  height: 100vh;
  overflow: hidden;
}
```

---

## 4. Layout główny — `templates/index.html`

Zastąp całą zawartość `<body>` poniższą strukturą HTML. Zachowaj istniejące `<script>` tagi na dole jeśli masz własną logikę JS.

```html
<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Asystent Regulaminowy – PWr</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
</head>
<body>

<div class="app-shell">

  <!-- ═══════════════════════════════════════
       SIDEBAR (lewy panel)
  ═══════════════════════════════════════ -->
  <aside class="sidebar">

    <div class="sidebar-header">
      <div class="logo-row">
        <div class="logo-badge">PWr</div>
        <div class="logo-info">
          <span class="logo-title">Asystent</span>
          <span class="logo-sub">Regulaminowy</span>
        </div>
      </div>
      <button class="btn-new-chat" id="btnNewChat">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        nowy czat
      </button>
    </div>

    <div class="sidebar-section-label">Historia</div>

    <div class="history-list" id="historyList">
      <!-- Dynamicznie generowane przez JS -->
      <!-- Przykładowy item (możesz usunąć):
      <div class="hist-item active">Egzaminy i urlopy</div>
      -->
    </div>

    <div class="sidebar-footer">
      <button class="footer-btn" id="btnSavePdf">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Zapisz rozmowę
      </button>
      <button class="footer-btn" id="btnToggleTheme">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        </svg>
        Zmień motyw
      </button>
      <div class="footer-version">v2.0 · BM25 + Mini-GPT · JAANULO</div>
    </div>

  </aside>

  <!-- ═══════════════════════════════════════
       GŁÓWNY PANEL (prawy)
  ═══════════════════════════════════════ -->
  <main class="main-panel">

    <!-- Topbar -->
    <header class="topbar">
      <div class="topbar-info">
        <span class="topbar-title">Asystent Regulaminowy PWr</span>
        <span class="topbar-sub">Politechnika Wrocławska · Regulamin studiów</span>
      </div>
      <div class="topbar-actions">
        <button class="icon-btn" id="btnClearChat" title="Wyczyść czat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Obszar wiadomości -->
    <div class="messages-area" id="messagesArea">

      <!-- Ekran powitalny — widoczny gdy brak wiadomości -->
      <div class="welcome-screen" id="welcomeScreen">
        <div class="welcome-icon">📋</div>
        <h2 class="welcome-title">Asystent Regulaminowy</h2>
        <p class="welcome-sub">Zadaj pytanie o regulamin studiów Politechniki Wrocławskiej.</p>
        <div class="suggestions-grid" id="suggestionsGrid">
          <button class="sug-chip" onclick="fillInput('ile razy można podejść do egzaminu?')">ile razy można podejść do egzaminu?</button>
          <button class="sug-chip" onclick="fillInput('kiedy można wziąć urlop dziekański?')">kiedy można wziąć urlop dziekański?</button>
          <button class="sug-chip" onclick="fillInput('co grozi za nieobecności?')">co grozi za nieobecności?</button>
          <button class="sug-chip" onclick="fillInput('jak wznowić studia po skreśleniu?')">jak wznowić studia po skreśleniu?</button>
          <button class="sug-chip" onclick="fillInput('jak oblicza się średnią ocen?')">jak oblicza się średnią ocen?</button>
          <button class="sug-chip" onclick="fillInput('jakie są warunki zaliczenia semestru?')">jakie są warunki zaliczenia semestru?</button>
        </div>
      </div>

      <!-- Kontener na wiadomości — JS wstawia tu elementy -->
      <div class="messages-container" id="messagesContainer"></div>

    </div>

    <!-- Pole input -->
    <div class="input-section">
      <div class="input-wrapper">
        <textarea
          id="userInput"
          class="input-field"
          placeholder="Zapytaj o regulamin studiów…"
          rows="1"
          autocomplete="off"
          spellcheck="false"
        ></textarea>
        <button class="send-btn" id="sendBtn" aria-label="Wyślij">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p class="input-hint">Enter – wyślij · Shift+Enter – nowa linia</p>
    </div>

  </main>
</div>

<script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
```

---

## 5. Style CSS — `static/style.css`

Dodaj (lub zastąp) poniższe style po sekcji `:root` z punktu 3:

```css
/* ── Layout powłoki ── */
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 230px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255,255,255,0.06);
}

.sidebar-header {
  padding: 16px 14px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.logo-badge {
  width: 32px;
  height: 32px;
  background: var(--accent);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #B5D4F4;
  letter-spacing: 0.03em;
}

.logo-info {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-on-dark);
  line-height: 1.2;
}

.logo-sub {
  font-size: 10px;
  color: var(--text-muted-dark);
}

.btn-new-chat {
  width: 100%;
  padding: 7px 10px;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--text-muted-dark);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font);
  transition: background 0.15s, color 0.15s;
}

.btn-new-chat:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-on-dark);
}

.sidebar-section-label {
  padding: 12px 14px 5px;
  font-size: 10px;
  font-weight: 500;
  color: rgba(255,255,255,0.25);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}

.history-list::-webkit-scrollbar { width: 3px; }
.history-list::-webkit-scrollbar-track { background: transparent; }
.history-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.hist-item {
  padding: 7px 9px;
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--text-muted-dark);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 1px;
  transition: background 0.12s, color 0.12s;
}

.hist-item:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-on-dark);
}

.hist-item.active {
  background: rgba(255,255,255,0.08);
  color: var(--text-on-dark);
  font-weight: 500;
}

.sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.footer-btn {
  background: transparent;
  border: none;
  padding: 6px 4px;
  font-size: 11px;
  color: var(--text-muted-dark);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font);
  border-radius: var(--radius-sm);
  transition: color 0.12s, background 0.12s;
  text-align: left;
}

.footer-btn:hover {
  color: var(--text-on-dark);
  background: rgba(255,255,255,0.05);
}

.footer-version {
  font-size: 10px;
  color: rgba(255,255,255,0.15);
  margin-top: 6px;
  padding: 0 4px;
}

/* ── Główny panel ── */
.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-primary);
}

/* ── Topbar ── */
.topbar {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.topbar-info {
  display: flex;
  flex-direction: column;
}

.topbar-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.topbar-sub {
  font-size: 11px;
  color: var(--text-tertiary);
}

.topbar-actions {
  display: flex;
  gap: 6px;
}

.icon-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: background 0.12s, color 0.12s;
}

.icon-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

/* ── Obszar wiadomości ── */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.messages-area::-webkit-scrollbar { width: 4px; }
.messages-area::-webkit-scrollbar-track { background: transparent; }
.messages-area::-webkit-scrollbar-thumb { background: var(--border-medium); border-radius: 2px; }

/* ── Ekran powitalny ── */
.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 20px;
  text-align: center;
}

.welcome-icon {
  font-size: 36px;
  margin-bottom: 14px;
  line-height: 1;
}

.welcome-title {
  font-size: 20px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.welcome-sub {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 400px;
  line-height: 1.6;
  margin-bottom: 28px;
}

.suggestions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 560px;
}

.sug-chip {
  padding: 7px 14px;
  border: 1px solid var(--border-medium);
  border-radius: 20px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  background: var(--bg-primary);
  font-family: var(--font);
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}

.sug-chip:hover {
  border-color: var(--accent-text);
  color: var(--accent-text);
  background: var(--accent-light);
}

/* ── Kontener wiadomości ── */
.messages-container {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── Wiadomości ── */
.msg {
  display: flex;
  flex-direction: column;
  max-width: 72%;
  animation: msgIn 0.2s ease-out;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg.user {
  align-self: flex-end;
}

.msg.bot {
  align-self: flex-start;
}

.msg-bubble {
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
}

.msg.bot .msg-bubble {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px 14px 14px 14px;
}

.msg.user .msg-bubble {
  background: var(--accent);
  color: #B5D4F4;
  border-radius: 14px 4px 14px 14px;
}

/* Badge źródła paragrafu */
.source-badge {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--accent-light);
  border: 1px solid rgba(24, 95, 165, 0.2);
  border-radius: var(--radius-md);
  padding: 4px 10px;
  font-size: 11px;
  color: var(--accent-text);
  font-weight: 500;
  align-self: flex-start;
  cursor: default;
}

.source-badge svg {
  flex-shrink: 0;
}

.msg-time {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 4px;
  padding: 0 4px;
}

.msg.user .msg-time {
  text-align: right;
}

/* ── Typing indicator (animowane kropki) ── */
.typing-indicator {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px 14px 14px 14px;
  animation: msgIn 0.2s ease-out;
}

.typing-dot {
  width: 5px;
  height: 5px;
  background: var(--text-tertiary);
  border-radius: 50%;
  animation: typingBounce 1.2s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.18s; }
.typing-dot:nth-child(3) { animation-delay: 0.36s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-5px); }
}

/* Separator daty */
.date-separator {
  text-align: center;
  margin: 6px 0;
}

.date-separator span {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  padding: 3px 12px;
  border-radius: 12px;
  border: 1px solid var(--border);
}

/* ── Input section ── */
.input-section {
  padding: 12px 18px 14px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg-primary);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-lg);
  padding: 8px 10px;
  transition: border-color 0.15s;
}

.input-wrapper:focus-within {
  border-color: var(--accent-text);
}

.input-field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  font-family: var(--font);
  color: var(--text-primary);
  resize: none;
  line-height: 1.5;
  min-height: 38px;
  max-height: 120px;
  overflow-y: auto;
}

.input-field::placeholder {
  color: var(--text-tertiary);
}

.send-btn {
  width: 32px;
  height: 32px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #B5D4F4;
  transition: background 0.15s, transform 0.1s;
}

.send-btn:hover { background: var(--accent-hover); }
.send-btn:active { transform: scale(0.95); }
.send-btn:disabled { background: var(--border-medium); cursor: not-allowed; color: var(--text-tertiary); }

.input-hint {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 6px;
  padding: 0 3px;
}

/* ── Responsywność (mobile) ── */
@media (max-width: 640px) {
  .sidebar { display: none; }
  .topbar-sub { display: none; }
}
```

---

## 6. JavaScript — `static/script.js`

**Zachowaj całą istniejącą logikę wysyłania zapytań do backendu.** Dopisz lub zastąp funkcje UI:

```javascript
// ─── Stałe DOM ───────────────────────────────────────────
const messagesContainer = document.getElementById('messagesContainer');
const messagesArea      = document.getElementById('messagesArea');
const welcomeScreen     = document.getElementById('welcomeScreen');
const userInput         = document.getElementById('userInput');
const sendBtn           = document.getElementById('sendBtn');
const historyList       = document.getElementById('historyList');
const btnNewChat        = document.getElementById('btnNewChat');
const btnClearChat      = document.getElementById('btnClearChat');

let conversationHistory = [];  // lokalna historia rozmowy

// ─── Pomocnicze ──────────────────────────────────────────

function getTime() {
  return new Date().toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
}

function hideWelcome() {
  if (welcomeScreen) welcomeScreen.style.display = 'none';
}

function scrollBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

// ─── Wypełnij input sugestią ──────────────────────────────
function fillInput(text) {
  userInput.value = text;
  userInput.focus();
  autoResize();
}

// ─── Auto-resize textarea ────────────────────────────────
function autoResize() {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
}

userInput.addEventListener('input', autoResize);

// ─── Dodaj wiadomość użytkownika do DOM ──────────────────
function addUserMessage(text) {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'msg user';
  div.innerHTML = `
    <div class="msg-bubble">${escapeHtml(text)}</div>
    <div class="msg-time">${getTime()}</div>
  `;
  messagesContainer.appendChild(div);
  scrollBottom();
}

// ─── Dodaj wiadomość bota do DOM ─────────────────────────
// source — opcjonalny string np. "§ 18. Egzaminy"
function addBotMessage(text, source) {
  const sourceHtml = source ? `
    <div class="source-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      ${escapeHtml(source)}
    </div>` : '';

  const div = document.createElement('div');
  div.className = 'msg bot';
  div.innerHTML = `
    <div class="msg-bubble">${escapeHtml(text)}</div>
    ${sourceHtml}
    <div class="msg-time">${getTime()}</div>
  `;
  messagesContainer.appendChild(div);
  scrollBottom();
}

// ─── Typing indicator ────────────────────────────────────
function showTyping() {
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = 'typingIndicator';
  el.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;
  messagesContainer.appendChild(el);
  scrollBottom();
}

function hideTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ─── Escape HTML (bezpieczeństwo XSS) ───────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ─── Główna funkcja wysyłania ─────────────────────────────
// WAŻNE: dostosuj endpoint i parsowanie odpowiedzi do swojego backendu!
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = '';
  autoResize();
  sendBtn.disabled = true;

  addUserMessage(text);
  showTyping();

  // Dodaj do historii sidebar
  addToHistory(text);

  try {
    // ─── DOSTOSUJ TEN FRAGMENT DO SWOJEGO BACKENDU ───────
    // Zmień '/ask' na właściwą trasę Flask
    // Zmień parsowanie odpowiedzi do struktury którą zwraca twój backend
    const response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text })
    });

    const data = await response.json();

    hideTyping();

    // Zakładamy że backend zwraca:
    // { "answer": "...", "source": "§ 18. Egzaminy" }
    // Dostosuj nazwy kluczy do swojego API!
    const answer = data.answer || data.response || data.text || 'Brak odpowiedzi.';
    const source = data.source || data.paragraph || null;

    addBotMessage(answer, source);

  } catch (error) {
    hideTyping();
    addBotMessage('Wystąpił błąd połączenia z serwerem.', null);
    console.error('Błąd fetch:', error);
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

// ─── Historia rozmów w sidebarze ─────────────────────────
function addToHistory(text) {
  const short = text.length > 35 ? text.slice(0, 35) + '…' : text;
  const item = document.createElement('div');
  item.className = 'hist-item active';
  item.textContent = short;
  item.title = text;
  // Usuń klasę active z poprzednich
  document.querySelectorAll('.hist-item').forEach(el => el.classList.remove('active'));
  historyList.insertBefore(item, historyList.firstChild);
}

// ─── Nowy czat ────────────────────────────────────────────
function clearChat() {
  messagesContainer.innerHTML = '';
  if (welcomeScreen) welcomeScreen.style.display = 'flex';
  conversationHistory = [];
}

// ─── Eventy ───────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

if (btnNewChat)   btnNewChat.addEventListener('click', clearChat);
if (btnClearChat) btnClearChat.addEventListener('click', clearChat);
```

---

## 7. Backend Flask — `main.py` (minimalne zmiany)

Sprawdź, że Twój endpoint Flask zwraca dane w formacie oczekiwanym przez JS.  
JS zakłada odpowiedź JSON: `{ "answer": "...", "source": "§ X. Nazwa" }`.

Jeśli twój backend zwraca inny format, **zmień parsowanie w `script.js`** (linia oznaczona komentarzem `DOSTOSUJ`) zamiast modyfikować backend.

Przykładowa trasa Flask (dostosuj do swojego istniejącego kodu):

```python
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')

    # Tutaj Twoja istniejąca logika wyszukiwania + generacji
    answer, source = twoja_funkcja_odpowiedzi(question)

    return jsonify({
        'answer': answer,
        'source': source  # np. "§ 18. Egzaminy" — może być None
    })
```

---

## 8. Checklist wdrożenia

Wykonaj po kolei:

- [ ] Wstaw zmienne CSS (sekcja 3) do `static/style.css`
- [ ] Zastąp `<body>` w `templates/index.html` kodem z sekcji 4
- [ ] Zastąp / uzupełnij `static/style.css` kodem z sekcji 5
- [ ] Zastąp / uzupełnij `static/script.js` kodem z sekcji 6
- [ ] Sprawdź nazwę endpointu (domyślnie `/ask`) — dostosuj jeśli inny
- [ ] Sprawdź klucze JSON w odpowiedzi backendu (`answer`, `source`) — dostosuj jeśli inne
- [ ] Przetestuj lokalnie: `python main.py`
- [ ] Zrób `git push` → Render automatycznie przebuduje

---

## 9. Uwagi końcowe

- **Motyw ciemny/jasny**: Plik zawiera tylko motyw jasny. Jeśli chcesz dark mode, dodaj klasę `.dark` do `<body>` i nadpisz zmienne `--bg-*` i `--text-*` w `.dark { ... }`.
- **Logo PWr**: Obraz `static/logo.png` można umieścić w `.logo-badge` zamiast tekstu "PWr" — zamień div na `<img src="{{ url_for('static', filename='logo.png') }}" />`.
- **Fonts offline**: Jeśli Render blokuje Google Fonts, pobierz plik `Inter` lokalnie i wstaw do `static/fonts/`.
- **Bezpieczeństwo**: Funkcja `escapeHtml()` w JS chroni przed XSS — nie usuwaj jej.
