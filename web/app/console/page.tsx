"use client";

import { useEffect, useState } from "react";

const apiBase =
  process.env.NEXT_PUBLIC_ATTICUS_API_BASE || "http://127.0.0.1:8000";

type Settings = {
  assistant?: { name?: string; default_mode?: string };
  providers?: { default_provider?: string; automatic?: boolean };
  sandbox?: { enabled?: boolean };
  telemetry?: { otel_exporter?: string };
};

export default function ConsolePage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demoSummary, setDemoSummary] = useState<string>("");

  useEffect(() => {
    fetch(`${apiBase}/v1/settings`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`settings HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((body) => setSettings(body))
      .catch((err) => setError(String(err.message || err)));
  }, []);

  async function runDemo() {
    setDemoSummary("Running…");
    try {
      const response = await fetch(`${apiBase}/v1/demo/signature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artifacts_subdir: "web_console" }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body?.error?.message || `HTTP ${response.status}`);
      }
      setDemoSummary(
        [
          `run=${body.run_id}`,
          `decision=${body.policy_decision}`,
          `approval=${body.approval_id}`,
          `quality_ok=${body.quality_report?.ok}`,
          "stopped_for_approval=true",
        ].join("\n")
      );
    } catch (err) {
      setDemoSummary(String(err));
    }
  }

  return (
    <main>
      <p className="muted">PLATFORM CONSOLE</p>
      <h1 className="brand">Atticus</h1>
      <p className="lede">
        Next.js operator surface for settings and the signature demo. The full
        phosphor terminal remains at the FastAPI <code>/ui</code> route.
      </p>
      <div className="actions">
        <button type="button" onClick={runDemo}>
          Run signature demo
        </button>
        <a className="button" href={`${apiBase}/ui/`}>
          Terminal UI
        </a>
        <a className="button" href="/">
          Home
        </a>
      </div>
      <div className="panel">
        {error
          ? `error: ${error}`
          : settings
            ? [
                `assistant: ${settings.assistant?.name}`,
                `mode: ${settings.assistant?.default_mode}`,
                `provider: ${settings.providers?.default_provider}`,
                `routing: ${settings.providers?.automatic ? "automatic" : "manual"}`,
                `sandbox: ${settings.sandbox?.enabled ? "on" : "off"}`,
                `otel: ${settings.telemetry?.otel_exporter}`,
              ].join("\n")
            : "loading settings…"}
      </div>
      {demoSummary ? <div className="panel">{demoSummary}</div> : null}
    </main>
  );
}
