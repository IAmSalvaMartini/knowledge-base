/**
 * KB Ask Widget — embed in Wiki.js via Administration → Theme → Custom HTML (body end).
 *
 * Usage:
 *   <script src="https://<kb-host>/static/widget/ask-widget.js"
 *           data-api-url="https://<kb-host>/api/ask"></script>
 *
 * Or set window.KB_API_URL before the script loads.
 */
(function () {
  "use strict";

  const API_URL =
    (document.currentScript && document.currentScript.getAttribute("data-api-url")) ||
    window.KB_API_URL ||
    "/api/ask";

  /* ── Styles ─────────────────────────────────────────────────────────── */
  const css = `
    #kb-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 52px; height: 52px; border-radius: 50%;
      background: #2563eb; color: #fff; border: none; cursor: pointer;
      font-size: 22px; box-shadow: 0 2px 8px rgba(0,0,0,.25);
      display: flex; align-items: center; justify-content: center;
    }
    #kb-btn:hover { background: #1d4ed8; }
    #kb-panel {
      position: fixed; bottom: 88px; right: 24px; z-index: 9998;
      width: 360px; max-height: 520px;
      background: #fff; border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,.18);
      display: flex; flex-direction: column;
      font-family: system-ui, sans-serif; font-size: 14px;
    }
    #kb-panel.kb-hidden { display: none; }
    #kb-header {
      padding: 12px 16px; background: #2563eb; color: #fff;
      border-radius: 10px 10px 0 0;
      display: flex; justify-content: space-between; align-items: center;
      font-weight: 600;
    }
    #kb-close { background: none; border: none; color: #fff; cursor: pointer; font-size: 18px; line-height: 1; }
    #kb-messages {
      flex: 1; overflow-y: auto; padding: 12px 16px;
      display: flex; flex-direction: column; gap: 10px;
    }
    .kb-msg { padding: 8px 12px; border-radius: 6px; line-height: 1.5; max-width: 95%; }
    .kb-msg-user { background: #eff6ff; align-self: flex-end; color: #1e3a8a; }
    .kb-msg-bot  { background: #f3f4f6; align-self: flex-start; color: #111; }
    .kb-msg-bot a { color: #2563eb; }
    .kb-citations { margin-top: 6px; font-size: 12px; color: #555; }
    .kb-citations span { display: block; }
    #kb-footer { padding: 10px 12px; border-top: 1px solid #e5e7eb; display: flex; gap: 8px; }
    #kb-input {
      flex: 1; border: 1px solid #d1d5db; border-radius: 6px;
      padding: 7px 10px; font-size: 14px; outline: none;
    }
    #kb-input:focus { border-color: #2563eb; }
    #kb-send {
      background: #2563eb; color: #fff; border: none; border-radius: 6px;
      padding: 7px 14px; cursor: pointer; font-size: 14px;
    }
    #kb-send:hover { background: #1d4ed8; }
    #kb-send:disabled { background: #93c5fd; cursor: not-allowed; }
  `;

  /* ── DOM ─────────────────────────────────────────────────────────────── */
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  const btn = document.createElement("button");
  btn.id = "kb-btn";
  btn.title = "Ask the Knowledge Base";
  btn.innerHTML = "💬";

  const panel = document.createElement("div");
  panel.id = "kb-panel";
  panel.className = "kb-hidden";
  panel.innerHTML = `
    <div id="kb-header">
      <span>Knowledge Base</span>
      <button id="kb-close" title="Close">✕</button>
    </div>
    <div id="kb-messages"></div>
    <div id="kb-footer">
      <input id="kb-input" type="text" placeholder="Ask a question…" autocomplete="off">
      <button id="kb-send">Ask</button>
    </div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  /* ── Logic ───────────────────────────────────────────────────────────── */
  const messages = document.getElementById("kb-messages");
  const input    = document.getElementById("kb-input");
  const send     = document.getElementById("kb-send");

  btn.addEventListener("click", () => panel.classList.toggle("kb-hidden"));
  document.getElementById("kb-close").addEventListener("click", () => panel.classList.add("kb-hidden"));

  function addMessage(html, cls) {
    const el = document.createElement("div");
    el.className = `kb-msg ${cls}`;
    el.innerHTML = html;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function markdownToHtml(text) {
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  async function ask() {
    const q = input.value.trim();
    if (!q) return;

    input.value = "";
    send.disabled = true;
    addMessage(escapeHtml(q), "kb-msg-user");
    const thinking = addMessage("…", "kb-msg-bot");

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question: q }),
      });

      if (res.status === 401) {
        thinking.innerHTML = 'Not signed in. <a href="/auth/login">Sign in</a> to use the knowledge base.';
        return;
      }

      const data = await res.json();
      let html = markdownToHtml(escapeHtml(data.answer || data.error || "No response."));

      if (data.citations && data.citations.length) {
        const links = data.citations
          .map(c => `<span>📄 ${escapeHtml(c)}</span>`)
          .join("");
        html += `<div class="kb-citations">${links}</div>`;
      }

      thinking.innerHTML = html;
    } catch (err) {
      thinking.innerHTML = "Request failed. Is the knowledge base server running?";
    } finally {
      send.disabled = false;
      input.focus();
    }
  }

  send.addEventListener("click", ask);
  input.addEventListener("keydown", e => { if (e.key === "Enter") ask(); });
})();
