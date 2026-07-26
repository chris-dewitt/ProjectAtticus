(() => {
  const logEl = document.getElementById("log");
  const sysEl = document.getElementById("sys");
  const citesEl = document.getElementById("cites");
  const approvalsEl = document.getElementById("approvals");
  const settingsEl = document.getElementById("settings");
  const traceEl = document.getElementById("trace");
  const promptEl = document.getElementById("prompt");
  const sendBtn = document.getElementById("send-btn");
  const newBtn = document.getElementById("new-btn");
  const citeBtn = document.getElementById("cite-btn");
  const approvalAuthBtn = document.getElementById("approval-auth-btn");
  const traceBtn = document.getElementById("trace-btn");
  const settingsBtn = document.getElementById("settings-btn");
  const demoBtn = document.getElementById("demo-btn");
  const installBtn = document.getElementById("install-btn");
  const linkEl = document.getElementById("link-status");
  const sessionEl = document.getElementById("session");

  const modalRoot = document.getElementById("modal-root");
  const modalTitle = document.getElementById("modal-title");
  const modalCopy = document.getElementById("modal-copy");
  const modalForm = document.getElementById("modal-form");
  const modalCancel = document.getElementById("modal-cancel");
  const modalOk = document.getElementById("modal-ok");

  const state = {
    conversationId: localStorage.getItem("atticus.conversationId") || null,
    lastRunId: localStorage.getItem("atticus.lastRunId") || null,
    approvalToken: null,
    busy: false,
    deferredInstall: null,
    modalResolver: null,
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
    const { headers = {}, ...rest } = options;
    const response = await fetch(path, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": crypto.randomUUID(),
        ...headers,
      },
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

  function closeModal(result) {
    if (!modalRoot) return;
    modalRoot.hidden = true;
    const resolver = state.modalResolver;
    state.modalResolver = null;
    if (resolver) resolver(result);
  }

  /**
   * In-page modal (works in desktop webview where window.prompt does not).
   * fields: [{ name, label, type?, value?, options?, required? }]
   */
  function openModal({ title, copy = "", fields = [], okLabel = "Save" }) {
    return new Promise((resolve) => {
      state.modalResolver = resolve;
      modalTitle.textContent = title;
      modalCopy.textContent = copy;
      modalOk.textContent = okLabel;
      modalForm.replaceChildren();

      for (const field of fields) {
        const label = document.createElement("label");
        label.textContent = field.label;
        let input;
        if (field.type === "select") {
          input = document.createElement("select");
          for (const option of field.options || []) {
            const opt = document.createElement("option");
            opt.value = option.value;
            opt.textContent = option.label;
            if (String(option.value) === String(field.value)) opt.selected = true;
            input.appendChild(opt);
          }
        } else {
          input = document.createElement("input");
          input.type = field.type || "text";
          input.value = field.value == null ? "" : String(field.value);
          if (field.placeholder) input.placeholder = field.placeholder;
        }
        input.name = field.name;
        input.autocomplete = "off";
        if (field.required !== false) input.required = true;
        label.appendChild(input);
        modalForm.appendChild(label);
      }

      modalRoot.hidden = false;
      const first = modalForm.querySelector("input, select");
      if (first) first.focus();
    });
  }

  modalCancel.addEventListener("click", () => closeModal(null));
  modalRoot.querySelectorAll("[data-modal-dismiss]").forEach((el) => {
    el.addEventListener("click", () => closeModal(null));
  });
  modalForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = {};
    const formData = new FormData(modalForm);
    for (const [key, value] of formData.entries()) {
      data[key] = String(value);
    }
    closeModal(data);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modalRoot.hidden) {
      event.preventDefault();
      closeModal(null);
    }
  });

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

  async function refreshSettings() {
    try {
      const data = await api("/v1/settings");
      settingsEl.textContent = [
        `address: ${data.assistant.user_address}`,
        `mode: ${data.assistant.default_mode}`,
        `provider: ${data.providers.default_provider}`,
        `memory: ${data.privacy.memory_enabled ? "on" : "off"}`,
        `spoken: ${data.voice.spoken_responses ? "on" : "off"}`,
        `sandbox: ${data.sandbox.enabled ? "on" : "off"}`,
        `otel: ${data.telemetry.otel_exporter}`,
        `rate/min: ${data.api.rate_limit_per_minute}`,
      ].join("\n");
    } catch (err) {
      settingsEl.textContent = `// settings unavailable\n${err.message || err}`;
    }
  }

  async function editSettings() {
    try {
      const current = await api("/v1/settings");
      const values = await openModal({
        title: "Settings",
        copy: "Adjust local operator toggles. Secrets stay in your environment — never here.",
        okLabel: "Save",
        fields: [
          {
            name: "default_provider",
            label: "Default provider",
            type: "select",
            value: current.providers.default_provider,
            options: [
              { value: "openai", label: "openai" },
              { value: "anthropic", label: "anthropic" },
              { value: "gemini", label: "gemini" },
              { value: "mock", label: "mock (local fixture)" },
            ],
          },
          {
            name: "spoken_responses",
            label: "Spoken responses",
            type: "select",
            value: String(current.voice.spoken_responses),
            options: [
              { value: "true", label: "true" },
              { value: "false", label: "false" },
            ],
          },
          {
            name: "default_mode",
            label: "Default mode",
            type: "text",
            value: current.assistant.default_mode || "default",
          },
        ],
      });
      if (!values) {
        line("system", "Settings closed without changes.", "system");
        return;
      }
      const patched = await api("/v1/settings", {
        method: "PATCH",
        body: JSON.stringify({
          default_provider: values.default_provider.trim(),
          spoken_responses: values.spoken_responses.trim().toLowerCase() === "true",
          default_mode: values.default_mode.trim(),
        }),
      });
      line("system", `Settings updated :: ${patched.changed.join(", ")}`, "system");
      refreshSettings();
    } catch (err) {
      line("system", String(err.message || err), "error");
    }
  }

  async function refreshCitations() {
    try {
      const data = await api("/v1/citations?limit=12");
      const items = data.items || [];
      if (!items.length) {
        citesEl.textContent = "// no citations yet\n// use Demo or CLI /browse";
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

  async function refreshTrace(runId) {
    const id = runId || state.lastRunId;
    if (!id) {
      traceEl.textContent = "// no run id yet";
      line("system", "No run to trace yet — send a message or run Demo.", "system");
      return;
    }
    try {
      const [trace, replay] = await Promise.all([
        api(`/v1/traces/${id}`),
        api(`/v1/runs/${id}/replay`),
      ]);
      const spanLines = (trace.spans || [])
        .map((s) => `${s.kind}:${s.name} [${s.status}]`)
        .join("\n");
      traceEl.textContent = [
        `run: ${id}`,
        `status: ${replay.status}`,
        `spans: ${trace.span_count}`,
        spanLines || "// no spans",
        `checkpoints: ${(replay.checkpoints || []).map((c) => c.name).join(" → ")}`,
      ].join("\n");
      line("system", `Trace loaded for ${id}.`, "system");
    } catch (err) {
      traceEl.textContent = `// trace unavailable\n${err.message || err}`;
      line("system", String(err.message || err), "error");
    }
  }

  async function refreshApprovals() {
    if (!state.approvalToken) {
      approvalsEl.textContent = "// queue locked\n// select Auth";
      return;
    }
    try {
      const [pending, approved] = await Promise.all([
        api("/v1/approvals?status=pending&limit=8", {
          headers: { "X-Atticus-Approval-Token": state.approvalToken },
        }),
        api("/v1/approvals?status=approved&limit=8", {
          headers: { "X-Atticus-Approval-Token": state.approvalToken },
        }),
      ]);
      const items = [...(pending.items || []), ...(approved.items || [])];
      approvalsEl.replaceChildren();
      if (!items.length) {
        approvalsEl.textContent = "// no pending/approved requests";
        return;
      }
      for (const approval of items) {
        const card = document.createElement("div");
        card.className = "approval-card";

        const summary = document.createElement("p");
        summary.textContent =
          `[${approval.risk}] ${approval.tool_name}\n${approval.action_summary}`;
        card.appendChild(summary);

        const digest = document.createElement("p");
        digest.className = "digest";
        digest.textContent = `digest: ${approval.action_digest.slice(0, 16)}…`;
        card.appendChild(digest);

        const approve = document.createElement("button");
        approve.type = "button";
        approve.textContent = "Approve";
        approve.addEventListener("click", () => decideApproval(approval, true));
        card.appendChild(approve);

        const deny = document.createElement("button");
        deny.type = "button";
        deny.className = "deny";
        deny.textContent = "Deny";
        deny.addEventListener("click", () => decideApproval(approval, false));
        card.appendChild(deny);

        if (approval.status === "approved") {
          const execBtn = document.createElement("button");
          execBtn.type = "button";
          execBtn.textContent = "Execute";
          execBtn.addEventListener("click", () => executeApproval(approval));
          card.appendChild(execBtn);
        }
        approvalsEl.appendChild(card);
      }
    } catch (err) {
      approvalsEl.textContent = `// approvals unavailable\n${err.message || err}`;
    }
  }

  async function decideApproval(approval, approve) {
    const verb = approve ? "APPROVE" : "DENY";
    const required = `${verb} ${approval.confirmation_hint}`;
    const values = await openModal({
      title: approve ? "Approve action" : "Deny action",
      copy: `Type this exact confirmation phrase:\n${required}`,
      okLabel: approve ? "Approve" : "Deny",
      fields: [
        {
          name: "confirmation",
          label: "Confirmation phrase",
          type: "text",
          value: "",
          placeholder: required,
        },
      ],
    });
    if (!values) {
      line("system", "Approval cancelled.", "system");
      return;
    }
    if (values.confirmation !== required) {
      line("system", "Approval cancelled: confirmation mismatch.", "error");
      return;
    }
    if (!state.approvalToken) {
      line("system", "Approval cancelled: token missing. Use Auth first.", "error");
      return;
    }
    try {
      const decided = await api(`/v1/approvals/${approval.id}/decision`, {
        method: "POST",
        headers: { "X-Atticus-Approval-Token": state.approvalToken },
        body: JSON.stringify({
          decision: approve ? "approve" : "deny",
          actor: "speaker",
          action_digest: approval.action_digest,
          confirmation: values.confirmation,
          rationale: "Decision from Atticus terminal UI.",
        }),
      });
      line("system", `Approval ${decided.id} :: ${decided.status}`, "system");
      refreshApprovals();
    } catch (err) {
      line("system", String(err.message || err), "error");
    }
  }

  async function executeApproval(approval) {
    if (!state.approvalToken) {
      line("system", "Execute cancelled: Auth first.", "error");
      return;
    }
    const values = await openModal({
      title: "Execute approved action",
      copy: "Provide an Idempotency-Key so repeated submits do not double-run.",
      okLabel: "Execute",
      fields: [
        {
          name: "idempotency_key",
          label: "Idempotency key",
          type: "text",
          value: crypto.randomUUID(),
        },
      ],
    });
    if (!values || !values.idempotency_key.trim()) {
      line("system", "Execute cancelled.", "system");
      return;
    }
    try {
      const result = await api(`/v1/approvals/${approval.id}/execute`, {
        method: "POST",
        headers: {
          "X-Atticus-Approval-Token": state.approvalToken,
          "Idempotency-Key": values.idempotency_key.trim(),
        },
        body: JSON.stringify({ actor: "atticus" }),
      });
      line(
        "system",
        `Dispatch ${result.approval_id} :: ${result.status}` +
          (result.replayed ? " (replay)" : ""),
        "system"
      );
      refreshApprovals();
    } catch (err) {
      line("system", String(err.message || err), "error");
    }
  }

  async function authenticateApprovals() {
    const values = await openModal({
      title: "Authorization",
      copy: "Enter ATTICUS_APPROVAL_TOKEN. Kept in page memory only — never written to disk.",
      okLabel: "Unlock",
      fields: [
        {
          name: "token",
          label: "Approval token",
          type: "password",
          value: "",
          placeholder: "token from your .env",
        },
      ],
    });
    if (!values || !values.token.trim()) {
      line("system", "Auth cancelled.", "system");
      return;
    }
    state.approvalToken = values.token.trim();
    line("system", "Approval queue unlocked for this session.", "system");
    refreshApprovals();
  }

  async function runSignatureDemo() {
    if (state.busy) return;
    state.busy = true;
    demoBtn.disabled = true;
    try {
      line("system", "Signature demo starting (synthetic fixtures)…", "system");
      const result = await api("/v1/demo/signature", {
        method: "POST",
        body: JSON.stringify({ artifacts_subdir: "signature_demo" }),
      });
      state.lastRunId = result.run_id;
      localStorage.setItem("atticus.lastRunId", result.run_id);
      line(
        "listener",
        `Demo complete. Approaches: ${result.comparison_table.map((r) => r.name).join(", ")}. ` +
          `Policy: ${result.policy_decision}. Approval: ${result.approval_id || "none"}. ` +
          `Quality ok=${result.quality_report.ok}. Stopped for approval before publish.`
      );
      refreshCitations();
      refreshApprovals();
      refreshTrace(result.run_id);
    } catch (err) {
      line("system", String(err.message || err), "error");
    } finally {
      state.busy = false;
      demoBtn.disabled = false;
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
    line("system", `Session opened :: ${created.id}`, "system");
    return created.id;
  }

  async function sendMessage() {
    const content = promptEl.value.trim();
    if (!content || state.busy) return;
    state.busy = true;
    sendBtn.disabled = true;
    try {
      const conversationId = await ensureConversation();
      line("speaker", content);
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
        line("system", "Message stored; no run executed.", "system");
        return;
      }
      state.lastRunId = run.id;
      localStorage.setItem("atticus.lastRunId", run.id);
      if (run.status === "succeeded") {
        line("listener", run.output_text || "(empty reply)");
      } else {
        line(
          "system",
          `run ${run.id} :: ${run.status}${run.error ? " :: " + run.error.message : ""}`,
          "error"
        );
      }
      refreshTrace(run.id);
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
    state.lastRunId = null;
    localStorage.removeItem("atticus.conversationId");
    localStorage.removeItem("atticus.lastRunId");
    sessionEl.textContent = "session: —";
    logEl.innerHTML = "";
    traceEl.textContent = "// send a message or run Demo";
    line("system", "New session ready when you are, Speaker.", "system");
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/ui/sw.js").catch(() => {});
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    state.deferredInstall = event;
    if (installBtn) installBtn.hidden = false;
  });

  async function installApp() {
    if (!state.deferredInstall) {
      await openModal({
        title: "Install Atticus",
        copy:
          "Use your browser menu: Add to Home Screen (phone) or Install app (desktop).\n\n" +
          "For a Windows .exe downloadable app, see docs/DOWNLOADABLE_APP.md and scripts/build_windows_app.ps1.",
        okLabel: "Understood",
        fields: [],
      });
      return;
    }
    state.deferredInstall.prompt();
    try {
      await state.deferredInstall.userChoice;
    } catch {
      /* dismissed */
    }
    state.deferredInstall = null;
    if (installBtn) installBtn.hidden = true;
  }

  sendBtn.addEventListener("click", sendMessage);
  newBtn.addEventListener("click", newSession);
  citeBtn.addEventListener("click", () => {
    refreshCitations();
    line("system", "Citations refreshed.", "system");
  });
  approvalAuthBtn.addEventListener("click", authenticateApprovals);
  traceBtn.addEventListener("click", () => refreshTrace());
  settingsBtn.addEventListener("click", editSettings);
  demoBtn.addEventListener("click", runSignatureDemo);
  if (installBtn) installBtn.addEventListener("click", installApp);
  promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  line("system", "The Listener is online.", "system");
  line(
    "system",
    "Speak when ready. Settings, Auth, Trace, Citations, and Demo use in-page panels (no browser prompts).",
    "system"
  );
  if (state.conversationId) {
    sessionEl.textContent = `session: ${state.conversationId}`;
    line("system", `Resumed session :: ${state.conversationId}`, "system");
  }
  registerServiceWorker();
  refreshSystem();
  refreshSettings();
  refreshCitations();
  refreshApprovals();
  refreshTrace();
  setInterval(refreshSystem, 15000);
  setInterval(refreshApprovals, 15000);
})();
