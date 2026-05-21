import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { apiFetch, getToken, setAuth } from "../lib/auth";
import { useToast } from "../components/ToastProvider";

export default function RegisterPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [fullName, setFullName] = useState("");
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
      const data = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      setAuth(data.access_token, {
        email: data.email,
        full_name: data.full_name,
        role: data.role,
      });
      showToast({
        title: "SUCCESS",
        message: "Account created successfully.",
        variant: "success",
      });
      setTimeout(() => {
        router.replace("/");
      }, 700);
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="auth-page" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "#64748b" }}>Loading…</span>
      </div>
    );
  }

  return (
    <div className="auth-page login-shell">
      <aside className="login-brand">
        <div className="login-brand-glow-a" />
        <div className="login-brand-glow-b" />
        <div className="login-brand-inner">
          <h1>Join MeetScribe AI</h1>
          <p className="login-brand-desc">
            Create your account and start live meeting transcription with secure JWT access.
          </p>
          <ul className="login-features">
            <li>First user becomes admin</li>
            <li>Live meeting workspace</li>
            <li>PostgreSQL-backed auth</li>
          </ul>
        </div>
      </aside>

      <section className="login-form-side">
        <div className="login-form-bg" />
        <div className="login-card">
          <div className="login-card-head">
            <h2>Create account</h2>
            <p>Register to access the meeting dashboard</p>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="login-label">FULL NAME</label>
            <input
              className="login-field auth-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
            />

            <label className="login-label">EMAIL</label>
            <input
              className="login-field auth-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label className="login-label">PASSWORD</label>
            <input
              className="login-field auth-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              placeholder="Min 6 characters"
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
                }}
              >
                {error}
              </div>
            ) : null}

            <button type="submit" disabled={loading} className="login-submit auth-btn">
              {loading ? "Creating…" : "Create account →"}
            </button>
          </form>

          <p className="login-footer">
            Already have an account? <Link href="/login">Sign in</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
