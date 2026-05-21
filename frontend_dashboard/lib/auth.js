const API_BASE = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8200";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("meetscribe_token");
}

export function getAuthUser() {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem("meetscribe_user") || "null");
  } catch {
    return null;
  }
}

export function setAuth(token, user) {
  localStorage.setItem("meetscribe_token", token);
  localStorage.setItem("meetscribe_user", JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem("meetscribe_token");
  localStorage.removeItem("meetscribe_user");
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      `Auth server nahi chal raha (${API_BASE}). Pehle run karo: .\\run_stack.ps1 ya python -m uvicorn api.main:app --port 8200`
    );
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.detail ?? res.statusText;
    if (Array.isArray(msg)) msg = msg.map((e) => e.msg || JSON.stringify(e)).join(", ");
    else if (typeof msg !== "string") msg = JSON.stringify(msg);
    throw new Error(msg);
  }
  return data;
}

export { API_BASE };
