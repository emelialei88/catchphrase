/* ── State ───────────────────────────────────── */
let currentCard = null;
let serverHasKey = false;
const KEY_STORAGE = "catchphrase.gemini_key";

function getStoredKey() { return localStorage.getItem(KEY_STORAGE) || ""; }
function setStoredKey(k) {
  if (k) localStorage.setItem(KEY_STORAGE, k);
  else localStorage.removeItem(KEY_STORAGE);
}
function effectiveKey() { return getStoredKey() || (serverHasKey ? "server" : ""); }

/* ── DOM refs ────────────────────────────────── */
const phraseInput   = document.getElementById("phrase-input");
const enrichBtn     = document.getElementById("enrich-btn");
const cardSection   = document.getElementById("card-section");
const cardPhrase    = document.getElementById("card-phrase");
const cardDef       = document.getElementById("card-definition");
const cardExamples  = document.getElementById("card-examples");
const cardRegister  = document.getElementById("card-register");
const cardSimilar   = document.getElementById("card-similar");
const cardNotes     = document.getElementById("card-notes");
const deckSelect    = document.getElementById("deck-select");
const addBtn        = document.getElementById("add-btn");
const addStatus     = document.getElementById("add-status");
const statusDot     = document.getElementById("anki-status");

const settingsBtn   = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const settingsClose = document.getElementById("settings-close");
const settingsSave  = document.getElementById("settings-save");
const apiKeyInput   = document.getElementById("api-key-input");

const setupBanner   = document.getElementById("setup-banner");
const setupTitle    = document.getElementById("setup-title");
const setupBody     = document.getElementById("setup-body");
const setupActions  = document.getElementById("setup-actions");

/* ── AnkiConnect status ──────────────────────── */
async function checkAnki() {
  try {
    const res = await fetch("/api/anki-status");
    const data = await res.json();
    const wasDisconnected = statusDot.classList.contains("disconnected");
    statusDot.className = "status-dot " + (data.connected ? "connected" : "disconnected");
    statusDot.title = data.connected
      ? `AnkiConnect v${data.version} connected — click to refresh decks`
      : "Anki not running — click to launch";
    // Refresh decks once Anki comes back online
    if (data.connected && wasDisconnected) loadDecks();
  } catch {
    statusDot.className = "status-dot disconnected";
    statusDot.title = "AnkiConnect not reachable — click to launch Anki";
  }
}

statusDot.style.cursor = "pointer";
statusDot.addEventListener("click", async () => {
  if (statusDot.classList.contains("disconnected")) {
    await fetch("/api/launch-anki", { method: "POST" }).catch(() => {});
    statusDot.title = "Launching Anki…";
  }
  checkAnki();
});

async function loadDecks() {
  try {
    const res = await fetch("/api/decks");
    if (!res.ok) throw new Error();
    const { decks, default: preferred } = await res.json();
    deckSelect.innerHTML = decks
      .map(d => `<option value="${escHtml(d)}">${escHtml(d)}</option>`)
      .join("");
    if (preferred && decks.includes(preferred)) deckSelect.value = preferred;
  } catch {
    deckSelect.innerHTML = `<option value="">Anki not available</option>`;
  }
}

/* ── Enrich ──────────────────────────────────── */
enrichBtn.addEventListener("click", enrich);
phraseInput.addEventListener("keydown", e => { if (e.key === "Enter") enrich(); });

async function enrich() {
  const phrase = phraseInput.value.trim();
  if (!phrase) return;

  setLoading(enrichBtn, true);
  hideStatus();
  cardSection.classList.add("hidden");

  try {
    const headers = { "Content-Type": "application/json" };
    const userKey = getStoredKey();
    if (userKey) headers["X-Gemini-Key"] = userKey;

    const res = await fetch("/api/enrich", {
      method: "POST",
      headers,
      body: JSON.stringify({ phrase }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Enrichment failed");
    }

    currentCard = await res.json();
    renderCard(currentCard);
    cardSection.classList.remove("hidden");
    cardSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    showStatus(err.message, "err");
    cardSection.classList.remove("hidden");
  } finally {
    setLoading(enrichBtn, false);
  }
}

/* ── Render card ─────────────────────────────── */
function renderCard(data) {
  cardPhrase.textContent = data.phrase;
  cardDef.textContent = data.definition;
  cardNotes.textContent = data.notes;
  cardSimilar.textContent = (data.similar || []).join(", ");
  cardRegister.value = data.register || "neutral";

  cardExamples.innerHTML = "";
  (data.examples || []).forEach((ex, i) => {
    const row = document.createElement("div");
    row.className = "example-item";
    row.innerHTML = `<span class="example-num">${i + 1}</span>`;
    const ta = document.createElement("textarea");
    ta.className = "example-text";
    ta.value = ex;
    ta.rows = 1;
    ta.addEventListener("input", autoResize);
    autoResize.call(ta);
    row.appendChild(ta);
    cardExamples.appendChild(row);
  });
}

function autoResize() {
  this.style.height = "auto";
  this.style.height = this.scrollHeight + "px";
}

/* ── Add to Anki ─────────────────────────────── */
addBtn.addEventListener("click", addToAnki);

async function addToAnki() {
  const deck = deckSelect.value;
  if (!deck) { showStatus("Select a deck first", "err"); return; }

  const examples = [...cardExamples.querySelectorAll(".example-text")].map(t => t.value.trim()).filter(Boolean);
  const similar  = cardSimilar.textContent.split(",").map(s => s.trim()).filter(Boolean);

  const payload = {
    deck,
    phrase:     cardPhrase.textContent.trim(),
    definition: cardDef.textContent.trim(),
    examples,
    style:      cardRegister.value,
    notes:      cardNotes.textContent.trim(),
    similar,
  };

  setLoading(addBtn, true);
  hideStatus();

  try {
    const res = await fetch("/api/add-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to add card");
    }

    const { note_id, synced } = await res.json();
    const syncMsg = synced ? "synced to AnkiWeb" : "added locally (sync pending)";
    showStatus(`Card added to "${deck}" ✓ — ${syncMsg}`, "ok");

    // Reset for next phrase
    phraseInput.value = "";
    phraseInput.focus();
    setTimeout(() => {
      cardSection.classList.add("hidden");
      hideStatus();
      currentCard = null;
    }, 3000);
  } catch (err) {
    showStatus(err.message, "err");
  } finally {
    setLoading(addBtn, false);
  }
}

/* ── Helpers ─────────────────────────────────── */
function setLoading(btn, on) {
  btn.disabled = on;
  btn.querySelector(".btn-label").classList.toggle("hidden", on);
  btn.querySelector(".btn-spinner").classList.toggle("hidden", !on);
}

function showStatus(msg, type) {
  addStatus.textContent = msg;
  addStatus.className = `add-status ${type}`;
  addStatus.classList.remove("hidden");
}

function hideStatus() {
  addStatus.classList.add("hidden");
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* ── Settings modal ──────────────────────────── */
function openSettings() {
  apiKeyInput.value = getStoredKey();
  settingsModal.classList.remove("hidden");
  setTimeout(() => apiKeyInput.focus(), 50);
}
function closeSettings() { settingsModal.classList.add("hidden"); }

settingsBtn.addEventListener("click", openSettings);
settingsClose.addEventListener("click", closeSettings);
settingsModal.addEventListener("click", e => { if (e.target === settingsModal) closeSettings(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSettings(); });

settingsSave.addEventListener("click", () => {
  setStoredKey(apiKeyInput.value.trim());
  closeSettings();
  refreshBanner();
});

/* ── Onboarding banner ───────────────────────── */
function showBanner(title, body, actions) {
  setupTitle.textContent = title;
  setupBody.textContent = body;
  setupActions.innerHTML = "";
  for (const a of actions) {
    if (a.href) {
      const link = document.createElement("a");
      link.href = a.href; link.target = "_blank"; link.rel = "noopener";
      link.textContent = a.label;
      if (a.secondary) link.className = "secondary";
      setupActions.appendChild(link);
    } else {
      const btn = document.createElement("button");
      btn.textContent = a.label;
      if (a.secondary) btn.className = "secondary";
      btn.addEventListener("click", a.onClick);
      setupActions.appendChild(btn);
    }
  }
  setupBanner.classList.remove("hidden");
}
function hideBanner() { setupBanner.classList.add("hidden"); }

function refreshBanner() {
  const ankiOk = statusDot.classList.contains("connected");
  const keyOk = !!effectiveKey();

  if (!keyOk) {
    showBanner(
      "Add your Gemini API key to get started",
      "Catchphrase uses Google Gemini (free tier) to enrich phrases. Grab a free key, then paste it into Settings.",
      [
        { label: "Get free key", href: "https://aistudio.google.com/app/apikey" },
        { label: "Open settings", onClick: openSettings, secondary: true },
      ]
    );
  } else if (!ankiOk) {
    showBanner(
      "Anki not detected",
      "Open Anki (and install the AnkiConnect add-on, code 2055492159) so cards can be saved.",
      [
        { label: "Launch Anki", onClick: async () => {
            await fetch("/api/launch-anki", { method: "POST" }).catch(() => {});
            setTimeout(checkAnki, 800);
          }
        },
        { label: "How to install AnkiConnect", onClick: openSettings, secondary: true },
      ]
    );
  } else {
    hideBanner();
  }
}

/* ── Server config ──────────────────────────── */
async function loadServerConfig() {
  try {
    const r = await fetch("/api/config");
    const d = await r.json();
    serverHasKey = !!d.server_has_key;
  } catch { serverHasKey = false; }
  refreshBanner();
}

/* Re-evaluate banner each time AnkiConnect status flips */
const _origCheckAnki = checkAnki;
checkAnki = async function () {
  await _origCheckAnki();
  refreshBanner();
};

/* ── Init ────────────────────────────────────── */
loadServerConfig();
checkAnki();
loadDecks();
setInterval(checkAnki, 10_000);
phraseInput.focus();
