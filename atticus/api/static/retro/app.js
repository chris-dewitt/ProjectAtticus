(() => {
  const logEl = document.getElementById("log");
  const sysEl = document.getElementById("sys");
  const citesEl = document.getElementById("cites");
  const promptEl = document.getElementById("prompt");
  const sendBtn = document.getElementById("send-btn");
  const newBtn = document.getElementById("new-btn");
  const citeBtn = document.getElementById("cite-btn");
  const linkEl = document.getElementById("link-status");
  const sessionEl = document.getElementById("session");

  const state = {
    conversationId: localStorage.getItem("atticus.conversationId") || null,
    busy: false,
  };

  function line(who, text, cls = "") {
    const div = document.createElement("div");
    div.className = `line ${cls}`.trim();
    const stamp = new Date().toISOString().slice(11, 19);
    div.innerHTML = `<span class="who">[${stamp}] ${who}</span>\n${escapeHtml(text)}`;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": crypto.randomUUID(),
        ...(options.headers || {}),
      },
      ...options,
    });
    const text = await response.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { raw: text };
    }
    if (!response.ok) {
      const message =
        (body && body.error && body.error.message) ||
        `HTTP ${response.status}`;
      throw new Error(message);
    }
    return body;
  }

  async function refreshSystem() {
    try {
      const live = await api("/health/live");
      const ready = await api("/health/ready");
      linkEl.textContent = ready.status === "ready" ? "LINK OK" : "LINK DEGRADED";
      linkEl.className = `status ${ready.status === "ready" ? "ok" : "bad"}`;
      sysEl.textContent = [
        `service: ${live.service}`,
        `version: ${live.version}`,
        `ready:   ${ready.status}`,
        ...((ready.checks || []).map((c) => ` - ${c.name}: ${c.ok ? "ok" : "FAIL"}`)),
      ].join("\n");
    } catch (err) {
      linkEl.textContent = "LINK DOWN";
      linkEl.className = "status bad";
      sysEl.textContent = String(err.message || err);
    }
  }

  async function refreshCitations() {
    try {
      const data = await api("/v1/citations?limit=12");
      const items = data.items || [];
      if (!items.length) {
        citesEl.textContent = "// no citations yet\n// use CLI /browse /file read /code-search";
        return;
      }
      citesEl.textContent = items
        .map(
          (c) =>
            `${c.id}\n[${c.kind}] ${c.title}\n${c.source_uri}\nsha:${(c.content_sha256 || "").slice(0, 12)}…\n`
        )
        .join("\n");
    } catch (err) {
      citesEl.textContent = `// citations unavailable\n${err.message || err}`;
    }
  }

  async function ensureConversation() {
    if (state.conversationId) {
      sessionEl.textContent = `session: ${state.conversationId}`;
      return state.conversationId;
    }
    const created = await api("/v1/conversations", {
      method: "POST",
      body: JSON.stringify({ title: "terminal" }),
    });
    state.conversationId = created.id;
    localStorage.setItem("atticus.conversationId", created.id);
    sessionEl.textContent = `session: ${created.id}`;
    line("system", `session opened :: ${created.id}`, "system");
    return created.id;
  }

  async function sendMessage() {
    const content = promptEl.value.trim();
    if (!content || state.busy) return;
    state.busy = true;
    sendBtn.disabled = true;
    try {
      const conversationId = await ensureConversation();
      line("boss", content);
      promptEl.value = "";
      const payload = await api(`/v1/conversations/${conversationId}/messages`, {
        method: "POST",
        body: JSON.stringify({
          content,
          execute: true,
        }),
      });
      const run = payload.run;
      if (!run) {
        line("system", "message stored; no run executed", "system");
        return;
      }
      if (run.status === "succeeded") {
        line("atticus", run.output_text || "(empty reply)");
      } else {
        line(
          "system",
          `run ${run.id} :: ${run.status}${run.error ? " :: " + run.error.message : ""}`,
          "error"
        );
      }
    } catch (err) {
      line("system", String(err.message || err), "error");
    } finally {
      state.busy = false;
      sendBtn.disabled = false;
      promptEl.focus();
    }
  }

  function newSession() {
    state.conversationId = null;
    localStorage.removeItem("atticus.conversationId");
    sessionEl.textContent = "session: —";
    logEl.innerHTML = "";
    line("system", "new session armed. transmit when ready.", "system");
  }

  sendBtn.addEventListener("click", sendMessage);
  newBtn.addEventListener("click", newSession);
  citeBtn.addEventListener("click", refreshCitations);
  promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  line("system", "ATTICUS terminal boot sequence complete.", "system");
  line("system", "Local API only. Phone access needs atticus-api --host 0.0.0.0 on trusted LAN.", "system");
  if (state.conversationId) {
    sessionEl.textContent = `session: ${state.conversationId}`;
    line("system", `resumed session :: ${state.conversationId}`, "system");
  }
  refreshSystem();
  refreshCitations();
  setInterval(refreshSystem, 15000);
})();
