import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { apiFetch, getToken, setAuth } from "../lib/auth";
import { useToast } from "../components/ToastProvider";

export default function LoginPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (getToken()) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [router]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAuth(data.access_token, {
        email: data.email,
        full_name: data.full_name,
        role: data.role,
      });
      showToast({
        title: "SUCCESS",
        message: "Logged in successfully.",
        variant: "success",
      });
      setTimeout(() => {
        router.replace("/");
      }, 700);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="auth-page" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "#64748b" }}>Redirecting…</span>
      </div>
    );
  }

  return (
    <div className="auth-page login-shell">
      <aside className="login-brand">
        <div className="login-brand-glow-a" />
        <div className="login-brand-glow-b" />
        <div className="login-brand-inner">
          <h1>MeetScribe AI</h1>
          <p className="login-brand-desc">
            Live meeting transcription, speaker labels, and rolling summaries — powered by Whisper &amp; AI.
          </p>
          <ul className="login-features">
            <li>Real-time captions</li>
            <li>5-second admin summaries</li>
            <li>Secure JWT login</li>
          </ul>
        </div>
      </aside>

      <section className="login-form-side">
        <div className="login-form-bg" />
        <div className="login-card">
          <div className="login-card-head">
            <h2>Welcome back</h2>
            <p>Sign in to open your meeting workspace</p>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="login-label">EMAIL</label>
            <input
              className="login-field auth-input"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />

            <label className="login-label">PASSWORD</label>
            <input
              className="login-field auth-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />

            {error ? (
              <div
                style={{
                  background: "rgba(239, 68, 68, 0.12)",
                  color: "#fca5a5",
                  padding: "10px 12px",
                  borderRadius: 10,
                  fontSize: 13,
                  marginBottom: 16,
                  border: "none",
                }}
              >
                {error}
              </div>
            ) : null}

            <button type="submit" disabled={loading} className="login-submit auth-btn">
              {loading ? "Signing in…" : "Sign in →"}
            </button>
          </form>

          <p className="login-footer">
            New here? <Link href="/register">Create account</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
