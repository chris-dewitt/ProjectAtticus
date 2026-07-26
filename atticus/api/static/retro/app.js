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
  const linkEl = document.getElementById("link-status");
  const sessionEl = document.getElementById("session");

  const state = {
    conversationId: localStorage.getItem("atticus.conversationId") || null,
    lastRunId: localStorage.getItem("atticus.lastRunId") || null,
    approvalToken: null,
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
      const provider = window.prompt(
        "Default provider (openai|anthropic|gemini|mock):",
        current.providers.default_provider
      );
      if (provider == null) return;
      const spokenRaw = window.prompt(
        "Spoken responses? (true/false):",
        String(current.voice.spoken_responses)
      );
      if (spokenRaw == null) return;
      const patched = await api("/v1/settings", {
        method: "PATCH",
        body: JSON.stringify({
          default_provider: provider.trim(),
          spoken_responses: spokenRaw.trim().toLowerCase() === "true",
        }),
      });
      line("system", `settings updated :: ${patched.changed.join(", ")}`, "system");
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
        citesEl.textContent = "// no citations yet\n// use SIG DEMO or CLI /browse";
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
    } catch (err) {
      traceEl.textContent = `// trace unavailable\n${err.message || err}`;
    }
  }

  async function refreshApprovals() {
    if (!state.approvalToken) {
      approvalsEl.textContent = "// queue locked\n// select AUTH APPROVALS";
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
        approve.textContent = "APPROVE";
        approve.addEventListener("click", () => decideApproval(approval, true));
        card.appendChild(approve);

        const deny = document.createElement("button");
        deny.type = "button";
        deny.className = "deny";
        deny.textContent = "DENY";
        deny.addEventListener("click", () => decideApproval(approval, false));
        card.appendChild(deny);

        if (approval.status === "approved") {
          const execBtn = document.createElement("button");
          execBtn.type = "button";
          execBtn.textContent = "EXECUTE";
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
    const confirmation = window.prompt(
      `Exact action digest confirmation required:\n${required}`,
      ""
    );
    if (confirmation !== required) {
      line("system", "approval cancelled: confirmation mismatch", "error");
      return;
    }
    const token = state.approvalToken;
    if (!token) {
      line("system", "approval cancelled: token missing", "error");
      return;
    }
    try {
      const decided = await api(`/v1/approvals/${approval.id}/decision`, {
        method: "POST",
        headers: { "X-Atticus-Approval-Token": token },
        body: JSON.stringify({
          decision: approve ? "approve" : "deny",
          actor: "boss",
          action_digest: approval.action_digest,
          confirmation,
          rationale: "Decision from retro terminal UI.",
        }),
      });
      line("system", `approval ${decided.id} :: ${decided.status}`, "system");
      refreshApprovals();
    } catch (err) {
      line("system", String(err.message || err), "error");
    }
  }

  async function executeApproval(approval) {
    if (!state.approvalToken) {
      line("system", "execute cancelled: auth approvals first", "error");
      return;
    }
    const key =
      window.prompt("Idempotency-Key for this execution:", crypto.randomUUID()) ||
      "";
    if (!key.trim()) {
      line("system", "execute cancelled: idempotency key required", "error");
      return;
    }
    try {
      const result = await api(`/v1/approvals/${approval.id}/execute`, {
        method: "POST",
        headers: {
          "X-Atticus-Approval-Token": state.approvalToken,
          "Idempotency-Key": key.trim(),
        },
        body: JSON.stringify({ actor: "atticus" }),
      });
      line(
        "system",
        `dispatch ${result.approval_id} :: ${result.status}` +
          (result.replayed ? " (replay)" : ""),
        "system"
      );
      refreshApprovals();
    } catch (err) {
      line("system", String(err.message || err), "error");
    }
  }

  function authenticateApprovals() {
    const token = window.prompt(
      "Enter ATTICUS_APPROVAL_TOKEN (kept in page memory only):",
      ""
    );
    if (!token) return;
    state.approvalToken = token;
    refreshApprovals();
  }

  async function runSignatureDemo() {
    if (state.busy) return;
    state.busy = true;
    demoBtn.disabled = true;
    try {
      line("system", "signature demo starting (synthetic fixtures)…", "system");
      const result = await api("/v1/demo/signature", {
        method: "POST",
        body: JSON.stringify({ artifacts_subdir: "signature_demo" }),
      });
      state.lastRunId = result.run_id;
      localStorage.setItem("atticus.lastRunId", result.run_id);
      line(
        "atticus",
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
      state.lastRunId = run.id;
      localStorage.setItem("atticus.lastRunId", run.id);
      if (run.status === "succeeded") {
        line("atticus", run.output_text || "(empty reply)");
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
    traceEl.textContent = "// run a message or SIG DEMO";
    line("system", "new session armed. transmit when ready.", "system");
  }

  sendBtn.addEventListener("click", sendMessage);
  newBtn.addEventListener("click", newSession);
  citeBtn.addEventListener("click", refreshCitations);
  approvalAuthBtn.addEventListener("click", authenticateApprovals);
  traceBtn.addEventListener("click", () => refreshTrace());
  settingsBtn.addEventListener("click", editSettings);
  demoBtn.addEventListener("click", runSignatureDemo);
  promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  line("system", "ATTICUS terminal boot sequence complete.", "system");
  line(
    "system",
    "Chat · approvals · settings · traces · signature demo. Phone: atticus-api --lan on trusted LAN only.",
    "system"
  );
  if (state.conversationId) {
    sessionEl.textContent = `session: ${state.conversationId}`;
    line("system", `resumed session :: ${state.conversationId}`, "system");
  }
  refreshSystem();
  refreshSettings();
  refreshCitations();
  refreshApprovals();
  refreshTrace();
  setInterval(refreshSystem, 15000);
  setInterval(refreshApprovals, 15000);
})();
