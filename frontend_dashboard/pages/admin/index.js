import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { apiFetch, clearAuth, getAuthUser, getToken } from "../../lib/auth";

const layout = {
  minHeight: "100vh",
  background: "#0a0e17",
  color: "#e2e8f0",
  fontFamily: "system-ui, sans-serif",
};

export default function AdminDashboard() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState("");
  const [selectedSession, setSelectedSession] = useState("all");

  const loadDashboard = useCallback(async () => {
    try {
      let analytics;
      try {
        analytics = await apiFetch("/api/admin/analytics?limit=60");
      } catch (err) {
        if (!String(err.message).toLowerCase().includes("not found")) throw err;
        const [dash, sessions] = await Promise.all([
          apiFetch("/api/admin/dashboard?limit=60"),
          apiFetch("/api/admin/sessions"),
        ]);
        const bySession = {};
        for (const s of sessions) {
          bySession[s.session_key] = {
            id: s.id,
            session_key: s.session_key,
            title: s.title,
            is_active: s.is_active,
            started_at: s.started_at,
            summary_count: s.summary_count,
            latest_summary: "",
            latest_at: null,
          };
        }
        for (const sum of dash.latest_summaries || []) {
          const row = bySession[sum.session_key];
          if (row && !row.latest_at) {
            row.latest_summary = (sum.text || "").slice(0, 500);
            row.latest_at = sum.created_at;
          }
        }
        const sessionList = Object.values(bySession);
        analytics = {
          active_sessions: dash.active_sessions,
          total_sessions: sessionList.length,
          total_summaries: dash.total_summaries,
          sessions: sessionList,
          chart_by_session: sessionList
            .map((s) => ({
              label: s.session_key.length > 12 ? s.session_key.slice(-12) : s.session_key,
              value: s.summary_count,
            }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 12),
          latest_summaries: dash.latest_summaries,
        };
      }
      setData(analytics);
      setError("");
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err.message || "Failed to load dashboard");
      if (String(err.message).includes("401") || String(err.message).includes("403")) {
        clearAuth();
        router.replace("/login");
      }
    }
  }, [router]);

  useEffect(() => {
    const token = getToken();
    const u = getAuthUser();
    if (!token || !u) {
      router.replace("/login");
      return;
    }
    if (u.role !== "admin") {
      router.replace("/");
      return;
    }
    setUser(u);
    loadDashboard();
    const id = setInterval(loadDashboard, 5000);
    return () => clearInterval(id);
  }, [router, loadDashboard]);

  function logout() {
    clearAuth();
    router.push("/login");
  }

  if (!user) {
    return (
      <div style={{ ...layout, display: "flex", alignItems: "center", justifyContent: "center" }}>
        Loading admin panel…
      </div>
    );
  }

  const maxBar = Math.max(1, ...(data?.chart_by_session?.map((b) => b.value) || [1]));
  const filteredSummaries =
    selectedSession === "all"
      ? data?.latest_summaries || []
      : (data?.latest_summaries || []).filter((s) => s.session_key === selectedSession);

  return (
    <div style={layout}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 28px",
          borderBottom: "1px solid #1e293b",
          background: "linear-gradient(90deg, #0f172a, #1e1b4b)",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>Admin Dashboard</h1>
        
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, color: "#a5b4fc" }}>{user.email}</span>
          <Link
            href="/"
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              background: "#1e293b",
              color: "#60a5fa",
              fontSize: 13,
              textDecoration: "none",
              border: "1px solid #334155",
            }}
          >
            Meeting Home
          </Link>
          <button type="button" onClick={logout} style={ghostBtn}>
            Logout
          </button>
        </div>
      </header>

      <main style={{ padding: "24px 28px", maxWidth: 1280, margin: "0 auto" }}>
        {error ? (
          <div style={{ background: "#7f1d1d", padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>
        ) : null}

        {data ? (
          <>
            <div style={{ display: "flex", gap: 14, marginBottom: 24, flexWrap: "wrap" }}>
              <StatCard label="Active sessions" value={data.active_sessions} accent="#22c55e" />
              <StatCard label="Total meeting IDs" value={data.total_sessions} accent="#60a5fa" />
              <StatCard label="Total summaries" value={data.total_summaries} accent="#a78bfa" />
              <StatCard label="Last refresh" value={lastRefresh || "—"} accent="#94a3b8" small />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
              <Panel title="Summaries per meeting ID (chart)">
                {data.chart_by_session.length === 0 ? (
                  <p style={{ color: "#64748b", fontSize: 14 }}>Loading.</p>
                ) : (
                  <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 180, paddingTop: 12 }}>
                    {data.chart_by_session.map((bar) => (
                      <div key={bar.label} style={{ flex: 1, textAlign: "center", minWidth: 36 }}>
                        <div
                          style={{
                            height: `${Math.max(8, (bar.value / maxBar) * 140)}px`,
                            background: "linear-gradient(180deg, #818cf8, #4f46e5)",
                            borderRadius: "6px 6px 2px 2px",
                            margin: "0 auto",
                            width: "100%",
                            maxWidth: 48,
                          }}
                          title={`${bar.label}: ${bar.value}`}
                        />
                        <div style={{ fontSize: 10, color: "#64748b", marginTop: 8 }}>{bar.label}</div>
                        <div style={{ fontSize: 11, fontWeight: 600, color: "#c7d2fe" }}>{bar.value}</div>
                      </div>
                    ))}
                  </div>
                )}
              </Panel>

              <Panel title="Activity overview">
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <MetricRow label="Sessions with summaries" value={data.sessions.filter((s) => s.summary_count > 0).length} />
                  <MetricRow label="Empty sessions" value={data.sessions.filter((s) => s.summary_count === 0).length} />
                  <MetricRow label="Avg summaries / session" value={data.total_sessions ? Math.round(data.total_summaries / data.total_sessions) : 0} />
                  <div style={{ marginTop: 8, padding: 12, background: "#0f172a", borderRadius: 10, fontSize: 13, color: "#94a3b8" }}>
                    Live meeting  <strong style={{ color: "#e2e8f0" }}>5 sec</strong> 
                  </div>
                </div>
              </Panel>
            </div>

            <Panel title="All meeting IDs — summary data">
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "#94a3b8", textAlign: "left", borderBottom: "1px solid #334155" }}>
                      <th style={th}>Session ID</th>
                      <th style={th}>Title</th>
                      <th style={th}>Summaries</th>
                      <th style={th}>Status</th>
                      <th style={th}>Latest summary</th>
                      <th style={th}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.sessions.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={{ padding: 16, color: "#64748b" }}>
                          No sessions yet
                        </td>
                      </tr>
                    ) : (
                      data.sessions.map((s) => (
                        <tr key={s.id} style={{ borderBottom: "1px solid #1e293b" }}>
                          <td style={td}>
                            <code style={{ color: "#60a5fa", fontSize: 12 }}>{s.session_key}</code>
                          </td>
                          <td style={td}>{s.title}</td>
                          <td style={td}>
                            <span style={{ fontWeight: 700, color: "#a78bfa" }}>{s.summary_count}</span>
                          </td>
                          <td style={td}>
                            <span style={{ color: s.is_active ? "#22c55e" : "#64748b" }}>
                              {s.is_active ? "● Live" : "Ended"}
                            </span>
                          </td>
                          <td style={{ ...td, maxWidth: 280 }}>
                            <span style={{ color: "#cbd5e1", lineHeight: 1.4 }}>
                              {s.latest_summary
                                ? s.latest_summary.length > 120
                                  ? `${s.latest_summary.slice(0, 120)}…`
                                  : s.latest_summary
                                : "—"}
                            </span>
                          </td>
                          <td style={td}>
                            <button
                              type="button"
                              onClick={() => setSelectedSession(s.session_key)}
                              style={{
                                ...ghostBtn,
                                padding: "6px 10px",
                                fontSize: 12,
                                background: selectedSession === s.session_key ? "#4f46e5" : "#1e293b",
                              }}
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Panel>

            <div style={{ marginTop: 24 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h2 style={{ margin: 0, fontSize: 18 }}>
                  Live summaries {selectedSession !== "all" ? `· ${selectedSession}` : ""}
                </h2>
                {selectedSession !== "all" ? (
                  <button type="button" onClick={() => setSelectedSession("all")} style={ghostBtn}>
                    Show all IDs
                  </button>
                ) : null}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {filteredSummaries.length === 0 ? (
                  <p style={{ color: "#94a3b8" }}>No summaries for this filter.</p>
                ) : (
                  filteredSummaries.map((s) => (
                    <div
                      key={s.id}
                      style={{
                        background: "#111827",
                        border: "1px solid #1e293b",
                        borderLeft: "4px solid #6366f1",
                        borderRadius: 10,
                        padding: 14,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                        <code style={{ fontSize: 11, color: "#60a5fa" }}>{s.session_key}</code>
                        <span style={{ fontSize: 11, color: "#64748b" }}>
                          {s.timestamp_label} · {new Date(s.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p style={{ margin: 0, lineHeight: 1.55, fontSize: 14 }}>{s.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        ) : (
          <p style={{ color: "#94a3b8" }}>Loading dashboard…</p>
        )}
      </main>
    </div>
  );
}

const th = { padding: "10px 12px", fontWeight: 600 };
const td = { padding: "12px", verticalAlign: "top" };
const ghostBtn = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid #475569",
  background: "transparent",
  color: "#e2e8f0",
  cursor: "pointer",
  fontSize: 13,
};

function StatCard({ label, value, accent = "#fff", small }) {
  return (
    <div
      style={{
        flex: "1 1 160px",
        background: "#111827",
        border: "1px solid #1e293b",
        borderRadius: 12,
        padding: 16,
        borderTop: `3px solid ${accent}`,
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: small ? 16 : 28, fontWeight: 700, color: "#f1f5f9" }}>{value}</div>
    </div>
  );
}

function Panel({ title, children }) {
  return (
    <div
      style={{
        background: "#111827",
        border: "1px solid #1e293b",
        borderRadius: 14,
        padding: 20,
      }}
    >
      <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600, color: "#cbd5e1" }}>{title}</h3>
      {children}
    </div>
  );
}

function MetricRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ color: "#94a3b8", fontSize: 14 }}>{label}</span>
      <span style={{ fontWeight: 700, fontSize: 18, color: "#e2e8f0" }}>{value}</span>
    </div>
  );
}
