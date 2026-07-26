const apiBase =
  process.env.NEXT_PUBLIC_ATTICUS_API_BASE || "http://127.0.0.1:8000";

async function fetchReady(): Promise<string> {
  try {
    const response = await fetch(`${apiBase}/health/ready`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return `ready HTTP ${response.status}`;
    }
    const body = (await response.json()) as { status?: string };
    return `API ${body.status || "unknown"} @ ${apiBase}`;
  } catch (error) {
    return `API unreachable @ ${apiBase} (${String(error)})`;
  }
}

export default async function HomePage() {
  const status = await fetchReady();
  return (
    <main>
      <p className="muted">PROJECTATTICUS</p>
      <h1 className="brand">Atticus</h1>
      <p className="lede">
        Local-first agent console. Chat, approvals, traces, and the signature
        research demo stay under Boss control — nothing consequential publishes
        without an explicit allow.
      </p>
      <div className="actions">
        <a className="button" href={`${apiBase}/ui/`}>
          Open terminal UI
        </a>
        <a className="button" href="/console">
          Platform console
        </a>
      </div>
      <div className="panel">{status}</div>
    </main>
  );
}
