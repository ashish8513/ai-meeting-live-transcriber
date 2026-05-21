import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

const VARIANTS = {
  success: { accent: "#22c55e", iconBg: "#f0fdf4", iconColor: "#16a34a" },
  error: { accent: "#ef4444", iconBg: "#fef2f2", iconColor: "#dc2626" },
  info: { accent: "#3b82f6", iconBg: "#eff6ff", iconColor: "#2563eb" },
};

function CheckIcon({ color }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M20 6 9 17l-5-5"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ErrorIcon({ color }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M18 6 6 18M6 6l12 12" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function InfoIcon({ color }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 16v-4M12 8h.01" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2" />
    </svg>
  );
}

function ToastItem({ toast, onDismiss }) {
  const v = VARIANTS[toast.variant] || VARIANTS.success;
  const Icon = toast.variant === "error" ? ErrorIcon : toast.variant === "info" ? InfoIcon : CheckIcon;

  return (
    <div
      role="alert"
      className="toast-item"
      style={{
        display: "flex",
        alignItems: "stretch",
        minWidth: 320,
        maxWidth: 400,
        background: "#ffffff",
        borderRadius: 10,
        boxShadow: "0 10px 40px rgba(15, 23, 42, 0.12), 0 2px 8px rgba(15, 23, 42, 0.08)",
        overflow: "hidden",
        animation: "toastSlideIn 0.35s ease-out",
        fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
      }}
    >
      <div style={{ width: 4, flexShrink: 0, background: v.accent }} />
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "16px 14px 16px 16px", flex: 1 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            background: v.iconBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Icon color={v.iconColor} />
        </div>
        <div style={{ flex: 1, paddingTop: 2, paddingRight: 8 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: "#1e293b",
              marginBottom: 4,
              textTransform: "uppercase",
            }}
          >
            {toast.title}
          </div>
          <div style={{ fontSize: 14, color: "#64748b", lineHeight: 1.45 }}>{toast.message}</div>
        </div>
        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss"
          style={{
            border: "none",
            background: "transparent",
            color: "#94a3b8",
            cursor: "pointer",
            fontSize: 18,
            lineHeight: 1,
            padding: 4,
            marginTop: -2,
          }}
        >
          ×
        </button>
      </div>
    </div>
  );
}

function ToastStack({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div
      className="toast-stack"
      style={{
        position: "fixed",
        top: 20,
        right: 20,
        zIndex: 99999,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        pointerEvents: "none",
      }}
    >
      {toasts.map((t) => (
        <div key={t.id} style={{ pointerEvents: "auto" }}>
          <ToastItem toast={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    ({ title = "UPDATED", message = "", variant = "success", duration = 4500 }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setToasts((prev) => [...prev.slice(-4), { id, title, message, variant }]);
      if (duration > 0) {
        setTimeout(() => dismiss(id), duration);
      }
      return id;
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ showToast, dismiss }}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      showToast: () => null,
      dismiss: () => {},
    };
  }
  return ctx;
}
