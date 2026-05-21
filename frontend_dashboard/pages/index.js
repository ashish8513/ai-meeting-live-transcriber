import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { clearAuth, getAuthUser, getToken } from "../lib/auth";
import { useToast } from "../components/ToastProvider";

const palette = [
  "#1f77b4",
  "#ff7f0e",
  "#2ca02c",
  "#d62728",
  "#9467bd",
  "#8c564b",
  "#e377c2",
  "#7f7f7f",
  "#bcbd22",
  "#17becf",
];

const SIGNAL_URL = process.env.NEXT_PUBLIC_SIGNAL_URL || "http://localhost:8081/offer";

const FILLER_RE =
  /^(yeah|yea|yes|no|oh|ooh|ok|okay|um|uh|hmm|right|trim|done|all right|alright|i'm done|i should have|i love you|i love it|i love|mm-?hmm|mmm|and that's it|you should be fine)$/i;

function isFillerTranscript(text) {
  const t = (text || "").trim();
  if (!t) return true;
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length >= 3) return false;
  if (FILLER_RE.test(t)) return true;
  return words.length === 1 && t.length < 6;
}

function IconDot({ color = "#22c55e", size = 10 }) {
  return (
    <span style={{ display: "inline-block", width: size, height: size, borderRadius: 9999, background: color }} />
  );
}

function IconMic({ muted = false, size = 18, color = "currentColor" }) {
  return muted ? (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M19 11a7 7 0 0 1-14 0" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 18v3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  ) : (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M19 11a7 7 0 0 1-14 0" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 18v3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function IconVideo({ off = false, size = 18, color = "currentColor" }) {
  return off ? (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M3 7a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M21 8l-4 3v2l4 3V8Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  ) : (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M3 7a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M21 8l-4 3v2l4 3V8Z" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function IconUsers({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" stroke="currentColor" strokeWidth="1.8" />
      <path d="M19 7a3 3 0 1 1-6 0" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function IconChat({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V6a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v9Z" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function IconCC({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 12c0-1.1.9-2 2-2h1" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 12c0 1.1.9 2 2 2h1" stroke="currentColor" strokeWidth="1.8" />
      <path d="M14 12c0-1.1.9-2 2-2h1" stroke="currentColor" strokeWidth="1.8" />
      <path d="M14 12c0 1.1.9 2 2 2h1" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function IconSettings({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6 1.65 1.65 0 0 0-.33 1.82 2 2 0 1 1-3.34 0 1.65 1.65 0 0 0-.33-1.82 1.65 1.65 0 0 0-1-.6 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-.6-1 1.65 1.65 0 0 0-1.82-.33 2 2 0 1 1 0-3.34 1.65 1.65 0 0 0 1.82-.33 1.65 1.65 0 0 0 .6-1A1.65 1.65 0 0 0 4.6 4.6a1.65 1.65 0 0 0-1-.6 2 2 0 1 1 2.83-2.83 1.65 1.65 0 0 0 1 .6 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 15 4.6c.38 0 .74-.14 1-.4a1.65 1.65 0 0 0 .6-1 2 2 0 1 1 3.34 0 1.65 1.65 0 0 0-.33 1.82c.26.26.4.62.4 1s-.14.74-.4 1c-.26.26-.62.4-1 .4Z" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function IconPhoneEnd({ size = 18, color = "#fff" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }}>
      <path d="M21 15.46v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 1.27 2.72 2 2 0 0 1 3.24.55h3a2 2 0 0 1 2 1.72l.2 1.68a2 2 0 0 1-.57 1.68L6.9 7.33a16 16 0 0 0 6 6l1.7-1a2 2 0 0 1 1.68-.2l1.68.2a2 2 0 0 1 1.72 2v1.91Z" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function VoiceWave({ active, levels, color = "#22c55e" }) {
  const bars = Array.isArray(levels) && levels.length ? levels : [0.2, 0.6, 0.9, 0.6, 0.2];
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 16 }}>
      {bars.map((h, idx) => (
        <div
          key={idx}
          style={{
            width: 3,
            borderRadius: 9999,
            background: color,
            opacity: active ? 0.95 : 0.35,
            height: `${8 + h * 8}px`,
            transition: "height 0.12s ease-out, opacity 0.2s ease-out",
          }}
        />
      ))}
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const { showToast } = useToast();
  const [authReady, setAuthReady] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  const [lines, setLines] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [fullSummary, setFullSummary] = useState(null);
  const [summaryView, setSummaryView] = useState("list");
  const [live, setLive] = useState(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [showLive, setShowLive] = useState(true);
  const [subtitle, setSubtitle] = useState(null);
  const [subtitleMode, setSubtitleMode] = useState(true);
  const [subtitleLang, setSubtitleLang] = useState("en");
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [displayName, setDisplayName] = useState("");
  const [wsUrl, setWsUrl] = useState(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8765");
  const [webrtcStatus, setWebrtcStatus] = useState("disconnected");
  const [audioTransport, setAudioTransport] = useState("none");
  const [monitorVolume, setMonitorVolume] = useState(0.85);
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatUnread, setChatUnread] = useState(0);
  const [chatToast, setChatToast] = useState(null);
  const [chatDraft, setChatDraft] = useState("");
  const [chatImage, setChatImage] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showSummaries, setShowSummaries] = useState(true);
  const chatScrollRef = useRef(null);
  const chatFileRef = useRef(null);
  const chatToastTimerRef = useRef(null);
  const showLiveRef = useRef(true);
  const displayNameRef = useRef("");
  const chatOpenRef = useRef(false);
  const speakerColorsRef = useRef({});
  const colorIndexRef = useRef(0);
  const wsRef = useRef(null);
  const scrollRef = useRef(null);
  const participantsRef = useRef(new Set());
  const [participants, setParticipants] = useState([]);
  const lastActiveRef = useRef({});
  const lastInterimTimeRef = useRef({});
  const liveRef = useRef(null);
  const audioCtxRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const monitorGainRef = useRef(null);
  const videoRef = useRef(null);
  const pcRef = useRef(null);
  const streamIdRef = useRef("stream_ui_" + Math.random().toString(36).slice(2, 10));

  const [theme, setTheme] = useState("dark");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [waveLevels, setWaveLevels] = useState([0.2, 0.6, 1, 0.6, 0.2]);
  const waveIntervalRef = useRef(null);
  const connectTimeoutRef = useRef(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setAuthUser(getAuthUser());
    setAuthReady(true);
  }, [router]);

  function handleLogout() {
    clearAuth();
    disconnect();
    router.replace("/login");
  }

  function clearConnectTimeout() {
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
  }

  function themed(dark, light) {
    return theme === "dark" ? dark : light;
  }

  const cardBorder = themed("1px solid #1e293b", "1px solid #e5e7eb");

  useEffect(() => {
    showLiveRef.current = showLive;
    if (!showLive) {
      setLive(null);
      liveRef.current = null;
    }
  }, [showLive]);

  useEffect(() => {
    displayNameRef.current = (displayName || "").trim();
  }, [displayName]);

  useEffect(() => {
    chatOpenRef.current = chatOpen;
    if (chatOpen) setChatUnread(0);
  }, [chatOpen]);

  function myDisplayName() {
    return (displayNameRef.current || displayName || "").trim() || "User";
  }

  function notifyChatMessage(msg) {
    const sender = (msg.sender || "User").trim();
    const isSelf = sender === myDisplayName();
    if (isSelf) return;
    if (!chatOpenRef.current) {
      setChatUnread((n) => n + 1);
    }
    const preview = (msg.text || "").trim() || (msg.image ? "📷 Sent an image" : "New message");
    setChatToast({ sender, text: preview });
    if (chatToastTimerRef.current) clearTimeout(chatToastTimerRef.current);
    chatToastTimerRef.current = setTimeout(() => setChatToast(null), 4500);
  }

  function toggleChatPanel() {
    setChatOpen((open) => {
      const next = !open;
      if (next) setChatUnread(0);
      return next;
    });
  }

  function formatDuration(totalSeconds) {
    const s = Math.max(0, totalSeconds | 0);
    const hours = Math.floor(s / 3600);
    const minutes = Math.floor((s % 3600) / 60);
    const seconds = s % 60;
    if (hours > 0) {
      return (
        String(hours).padStart(2, "0") +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(seconds).padStart(2, "0")
      );
    }
    return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
  }

  function colorFor(speaker) {
    if (!speaker) return "#333";
    if (!speakerColorsRef.current[speaker]) {
      speakerColorsRef.current[speaker] = palette[colorIndexRef.current % palette.length];
      colorIndexRef.current += 1;
    }
    return speakerColorsRef.current[speaker];
  }

  function initialsFor(name) {
    if (!name) return "U";
    const parts = String(name)
      .split(/\s+/)
      .filter(Boolean);
    const first = parts[0] ? parts[0][0] : "";
    const second = parts[1] ? parts[1][0] : "";
    const letters = (first + second) || first;
    const up = (letters || "U").toUpperCase();
    return up;
  }

  function addParticipant(name) {
    const n = (name || "").trim();
    if (!n) return;
    participantsRef.current.add(n);
    setParticipants(Array.from(participantsRef.current));
    lastActiveRef.current[n] = Date.now();
  }

  function closeWebSocketSilently() {
    clearConnectTimeout();
    const ws = wsRef.current;
    if (!ws) return;
    ws.onopen = null;
    ws.onmessage = null;
    ws.onerror = null;
    ws.onclose = null;
    wsRef.current = null;
    try {
      ws.close();
    } catch {}
  }

  function resetCallUiState() {
    setConnected(false);
    setConnecting(false);
    setElapsedSeconds(0);
    setLive(null);
    liveRef.current = null;
    setSubtitle(null);
    setChatToast(null);
    setChatUnread(0);
    setWebrtcStatus("disconnected");
    setAudioTransport("none");
    participantsRef.current = new Set();
    setParticipants([]);
  }

  function endCall() {
    closeWebSocketSilently();
    stopAllMedia();
    resetCallUiState();
    setConnectionError("");
  }

  function sendWsConfig(sampleRate) {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    try {
      wsRef.current.send(
        JSON.stringify({
          type: "config",
          stream_id: streamIdRef.current,
          language: "en",
          translate_to: subtitleLang === "en" ? "" : subtitleLang,
          sample_rate: sampleRate || 48000,
        })
      );
    } catch {}
  }

  function connect(url) {
    const trimmed = (url || "").trim();
    if (!trimmed) {
      setConnectionError("Enter WebSocket URL (ws://localhost:8765)");
      return;
    }
    if (!/^wss?:\/\//i.test(trimmed)) {
      setConnectionError("URL must start with ws:// or wss://");
      return;
    }

    closeWebSocketSilently();
    setConnectionError("");
    setConnecting(true);
    setElapsedSeconds(0);

    let ws;
    try {
      ws = new WebSocket(trimmed);
    } catch {
      setConnecting(false);
      setConnectionError("Invalid WebSocket URL");
      return;
    }
    wsRef.current = ws;

    clearConnectTimeout();
    connectTimeoutRef.current = setTimeout(() => {
      if (wsRef.current !== ws || ws.readyState !== WebSocket.CONNECTING) return;
      setConnecting(false);
      setConnected(false);
      setElapsedSeconds(0);
      setConnectionError("Timeout — start backend on ws://localhost:8765");
      closeWebSocketSilently();
    }, 10000);

    ws.onopen = async () => {
      clearConnectTimeout();
      setConnecting(false);
      setConnected(true);
      setElapsedSeconds(0);
      showToast({
        title: "CONNECTED",
        message: "Meeting workspace connected successfully.",
        variant: "success",
      });
      const streamId = streamIdRef.current;
      let nameToUse = (displayName || "").trim();
      if (!nameToUse && typeof window !== "undefined") {
        try {
          const promptName = window.prompt("What is your name?", "");
          if (promptName && promptName.trim()) {
            nameToUse = promptName.trim();
            setDisplayName(promptName.trim());
          }
        } catch {}
      }
      const localName = nameToUse || "You";
      addParticipant(localName);
      try {
        sendWsConfig((audioCtxRef.current && audioCtxRef.current.sampleRate) || 48000);
        ws.send(
          JSON.stringify({
            type: "register_user",
            stream_id: streamId,
            name: localName,
          })
        );
      } catch {}
      try {
        await syncMediaAndAudio();
        if (audioCtxRef.current?.state === "suspended") {
          await audioCtxRef.current.resume();
        }
      } catch {
        setConnectionError("Mic allow karo — browser mein microphone permission deni hogi");
      }
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "participant" && data.speaker) {
          addParticipant(data.speaker);
        } else if (data.speaker) {
          addParticipant(data.speaker);
        }
        if (data.type === "interim") {
          const interimText = (data.text || "").trim();
          if (!interimText) return;
          console.log("WS interim IN:", data.speaker, "::", interimText);
          // Heuristic segmentation: keep updating one live box while speech is continuous.
          // If there is a gap of silence before the next interim from the same speaker,
          // freeze the previous live box into the transcript history and start a new one.
          const nowMs = Date.now();
          const lastTimes = lastInterimTimeRef.current;
          const lastTime = lastTimes[data.speaker] || 0;
          const gap = nowMs - lastTime;
          const SILENCE_GAP_MS = 2500;
          const currentLive = liveRef.current;
          const prevText = (currentLive?.text || "").trim();
          const wordCount = prevText ? prevText.split(/\s+/).filter(Boolean).length : 0;

          if (
            gap > SILENCE_GAP_MS &&
            currentLive &&
            currentLive.speaker === data.speaker &&
            prevText &&
            (wordCount >= 3 || prevText.length >= 12)
          ) {
            setLines((prev) =>
              [
                {
                  type: "transcript",
                  timestamp: currentLive.ts,
                  speaker: currentLive.speaker,
                  text: prevText,
                  stream_id: currentLive.stream_id,
                },
                ...prev,
              ].slice(0, 200)
            );
          }
          lastTimes[data.speaker] = nowMs;
          lastInterimTimeRef.current = lastTimes;

          const displayText = (data.text || "").trim();
          const nextLive = {
            ts: data.timestamp,
            speaker: data.speaker,
            text: displayText,
            stream_id: data.stream_id,
          };
          if (showLiveRef.current) {
            setLive(nextLive);
            liveRef.current = nextLive;
            if (subtitleMode) {
              setSubtitle({
                ts: data.timestamp,
                speaker: data.speaker,
                text: displayText,
                stream_id: data.stream_id,
              });
            }
          }
        } else if (data.type === "caption") {
          console.log("WS caption IN (", data.lang, "):", data.speaker, "::", data.text);
          setSubtitle({
            ts: data.timestamp,
            speaker: data.speaker,
            text: data.text,
            stream_id: data.stream_id,
            lang: data.lang,
            original: data.original,
          });
        } else if (data.type === "transcript") {
          if (isFillerTranscript(data.text)) return;
          setLive(null);
          liveRef.current = null;
          console.log("Final transcript IN:", data.speaker, "::", data.text);
          setLines((prev) => [data, ...prev].slice(0, 200));
          if (data.text) {
            setSubtitle({
              ts: data.timestamp,
              speaker: data.speaker,
              text: data.text,
              stream_id: data.stream_id,
            });
          }
        } else if (data.type === "summary") {
          setSummaries((prev) => [data, ...prev].slice(0, 10));
        } else if (data.type === "summary_final") {
          setFullSummary(data);
        } else if (data.type === "chat") {
          const entry = {
            id: `${Date.now()}_${Math.random()}`,
            sender: data.sender || "User",
            text: data.text || "",
            image: data.image || null,
            timestamp: data.timestamp || new Date().toLocaleTimeString(),
          };
          setChatMessages((prev) => [entry, ...prev].slice(0, 100));
          notifyChatMessage(entry);
        }
      } catch (e) {}
    };
    ws.onerror = () => {
      clearConnectTimeout();
      setConnecting(false);
      setConnected(false);
      setElapsedSeconds(0);
      setConnectionError("Cannot connect — start backend on port 8765");
      closeWebSocketSilently();
    };
    ws.onclose = () => {
      clearConnectTimeout();
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      setConnecting(false);
      setConnected(false);
      setElapsedSeconds(0);
      stopAllMedia();
    };
  }

  function disconnect() {
    endCall();
  }

  function attachVideoPreview(stream) {
    if (!videoRef.current) return;
    if (camOn && stream && stream.getVideoTracks().length > 0) {
      videoRef.current.srcObject = new MediaStream(stream.getVideoTracks());
      videoRef.current.muted = true;
      videoRef.current.play().catch(() => {});
    } else if (!camOn) {
      videoRef.current.srcObject = null;
    }
  }

  function setAudioTracksEnabled(enabled) {
    try {
      mediaStreamRef.current?.getAudioTracks().forEach((t) => {
        t.enabled = enabled;
      });
    } catch {}
  }

  async function ensureMediaStream() {
    if (typeof window === "undefined") return null;
    if (!navigator.mediaDevices?.getUserMedia) return null;

    let stream = mediaStreamRef.current;

    if (camOn) {
      if (!stream?.getVideoTracks().length) {
        const vStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (!stream) stream = vStream;
        else vStream.getVideoTracks().forEach((t) => stream.addTrack(t));
      } else {
        stream.getVideoTracks().forEach((t) => {
          t.enabled = true;
        });
      }
    } else if (stream) {
      stream.getVideoTracks().forEach((t) => {
        t.stop();
        try {
          stream.removeTrack(t);
        } catch {}
      });
    }

    if (micOn || stream?.getAudioTracks().length) {
      if (!stream?.getAudioTracks().length) {
        const aStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
            sampleRate: 48000,
            autoGainControl: true,
            noiseSuppression: true,
            echoCancellation: true,
          },
          video: false,
        });
        if (!stream) stream = aStream;
        else aStream.getAudioTracks().forEach((t) => stream.addTrack(t));
        setPermissionGranted(true);
        const allDevices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = allDevices.filter((d) => d.kind === "audioinput");
        setDevices(audioInputs);
        if (!selectedDeviceId && audioInputs[0]) {
          setSelectedDeviceId(audioInputs[0].deviceId || "");
        }
      }
      setAudioTracksEnabled(!!micOn);
    }

    if (!stream) return null;
    mediaStreamRef.current = stream;
    attachVideoPreview(stream);
    return stream;
  }

  async function requestMicPermission() {
    try {
      await ensureMediaStream();
      if (connected && micOn) await startAudioPipeline();
    } catch (e) {
      // ignore
    }
  }

  async function startWebRtc(stream) {
    if (typeof window === "undefined") return false;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
    if (pcRef.current) {
      const ice = pcRef.current.iceConnectionState;
      if (ice === "connected" || ice === "completed") return true;
      stopWebRtc();
    }
    if (!stream || !stream.getAudioTracks().length) return false;

    try {
      const pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
      pcRef.current = pc;
      setWebrtcStatus("connecting");

      pc.oniceconnectionstatechange = () => {
        const state = pc.iceConnectionState || "unknown";
        setWebrtcStatus(state);
        if ((state === "failed" || state === "disconnected" || state === "closed") && micOn) {
          startMicStream(stream).catch(() => {});
        }
      };

      stream.getAudioTracks().forEach((t) => pc.addTrack(t, stream));

      await pc.setLocalDescription(await pc.createOffer());

      await new Promise((resolve) => {
        if (pc.iceGatheringState === "complete") {
          resolve();
        } else {
          const timer = setTimeout(resolve, 2500);
          pc.onicegatheringstatechange = () => {
            if (pc.iceGatheringState === "complete") {
              clearTimeout(timer);
              resolve();
            }
          };
        }
      });

      const response = await fetch(SIGNAL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sdp: pc.localDescription.sdp,
          type: pc.localDescription.type,
          stream_id: streamIdRef.current,
        }),
      });
      if (!response.ok) {
        throw new Error(`WebRTC signal HTTP ${response.status}`);
      }
      const answer = await response.json();
      await pc.setRemoteDescription(answer);
      setWebrtcStatus("connected");
      setAudioTransport("webrtc");
      return true;
    } catch (e) {
      setWebrtcStatus("failed");
      try {
        if (pcRef.current) pcRef.current.close();
      } catch {}
      pcRef.current = null;
      return false;
    }
  }

  function stopWebRtc() {
    try {
      if (pcRef.current) {
        try { pcRef.current.close(); } catch {}
      }
    } catch {}
    pcRef.current = null;
    if (audioTransport === "webrtc") {
      setWebrtcStatus("disconnected");
      setAudioTransport("none");
    }
  }

  async function startMicStream(existingStream) {
    if (typeof window === "undefined") return false;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return false;
    if (audioCtxRef.current && processorRef.current) return true;

    try {
      const stream = existingStream || (await ensureMediaStream());
      if (!stream || !stream.getAudioTracks().length) return false;

      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContextCtor();
      audioCtxRef.current = audioCtx;
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      sendWsConfig(audioCtx.sampleRate);

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(1024, 1, 1);
      processorRef.current = processor;

      const monitorGain = audioCtx.createGain();
      monitorGain.gain.value = monitorVolume;
      monitorGainRef.current = monitorGain;

      const silentGain = audioCtx.createGain();
      silentGain.gain.value = 0.0001;

      processor.onaudioprocess = (event) => {
        try {
          if (!micOn) return;
          if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
          const input = event.inputBuffer.getChannelData(0);
          const copy = new Float32Array(input.length);
          let sum = 0;
          for (let i = 0; i < input.length; i++) {
            const s = input[i];
            sum += s * s;
            copy[i] = s;
          }
          const rms = Math.sqrt(sum / (input.length || 1));
          if (rms > 1e-6 && rms < 0.04) {
            const gain = Math.min(0.06 / rms, 8);
            for (let i = 0; i < copy.length; i++) {
              copy[i] = Math.max(-1, Math.min(1, copy[i] * gain));
            }
          }
          wsRef.current.send(copy.buffer);
        } catch {}
      };

      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioCtx.destination);
      source.connect(monitorGain);
      monitorGain.connect(audioCtx.destination);

      setAudioTransport("ws");
      setWebrtcStatus("ws-direct");
      return true;
    } catch (e) {
      return false;
    }
  }

  function stopMicStream() {
    try {
      if (processorRef.current) {
        try { processorRef.current.disconnect(); } catch {}
        processorRef.current.onaudioprocess = null;
      }
      if (monitorGainRef.current) {
        try { monitorGainRef.current.disconnect(); } catch {}
      }
      if (audioCtxRef.current) {
        try { audioCtxRef.current.close(); } catch {}
      }
    } catch {}
    processorRef.current = null;
    monitorGainRef.current = null;
    audioCtxRef.current = null;
    if (audioTransport === "ws") {
      setAudioTransport("none");
    }
  }

  function stopAudioOnly() {
    stopWebRtc();
    stopMicStream();
    setAudioTracksEnabled(false);
    if (audioTransport === "webrtc" || audioTransport === "ws") {
      setWebrtcStatus(micOn ? "disconnected" : "muted");
      setAudioTransport("none");
    }
  }

  function stopAllMedia() {
    stopAudioOnly();
    try {
      mediaStreamRef.current?.getVideoTracks().forEach((t) => {
        t.stop();
        try {
          mediaStreamRef.current.removeTrack(t);
        } catch {}
      });
      mediaStreamRef.current?.getAudioTracks().forEach((t) => t.stop());
    } catch {}
    mediaStreamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setWebrtcStatus("disconnected");
    setAudioTransport("none");
  }

  async function startAudioPipeline() {
    if (!connected || !micOn) return;
    stopWebRtc();
    stopMicStream();
    let stream = mediaStreamRef.current;
    try {
      stream = await ensureMediaStream();
    } catch {
      setWebrtcStatus("failed");
      return;
    }
    if (!stream?.getAudioTracks().length) return;
    setAudioTracksEnabled(true);

    // Prefer WebSocket audio on the same connection as transcripts (most reliable locally).
    const wsOk = await startMicStream(stream);
    if (wsOk) {
      setupWebRtcMonitor(stream);
      return;
    }
    const webrtcOk = await startWebRtc(stream);
    if (webrtcOk) {
      setupWebRtcMonitor(stream);
      sendWsConfig(48000);
    } else {
      setWebrtcStatus("failed");
    }
  }

  async function syncMediaAndAudio() {
    if (!connected) return;
    try {
      await ensureMediaStream();
      if (micOn) await startAudioPipeline();
      else stopAudioOnly();
    } catch {
      setWebrtcStatus("failed");
    }
  }

  function setupWebRtcMonitor(stream) {
    if (!stream || !stream.getAudioTracks().length) return;
    try {
      if (audioCtxRef.current) return;
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContextCtor();
      audioCtxRef.current = audioCtx;
      if (audioCtx.state === "suspended") {
        audioCtx.resume().catch(() => {});
      }
      const source = audioCtx.createMediaStreamSource(stream);
      const monitorGain = audioCtx.createGain();
      monitorGain.gain.value = monitorVolume;
      monitorGainRef.current = monitorGain;
      source.connect(monitorGain);
      monitorGain.connect(audioCtx.destination);
    } catch {}
  }

  useEffect(() => {
    if (monitorGainRef.current) {
      monitorGainRef.current.gain.value = monitorVolume;
    }
  }, [monitorVolume]);

  useEffect(() => {
    if (!connected) {
      stopAllMedia();
      return;
    }
    syncMediaAndAudio();
  }, [connected, camOn, selectedDeviceId]);

  useEffect(() => {
    if (!connected) return;
    if (micOn) startAudioPipeline();
    else {
      stopAudioOnly();
      setLive(null);
      liveRef.current = null;
    }
  }, [micOn]);

  useEffect(() => {
    if (!connected) {
      setElapsedSeconds(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => {
      const diff = Math.floor((Date.now() - start) / 1000);
      setElapsedSeconds(diff);
    }, 1000);
    return () => {
      clearInterval(id);
    };
  }, [connected]);

  useEffect(() => {
    if (!live) {
      if (waveIntervalRef.current) {
        clearInterval(waveIntervalRef.current);
        waveIntervalRef.current = null;
      }
      setWaveLevels([0.2, 0.6, 1, 0.6, 0.2]);
      return;
    }

    const id = setInterval(() => {
      setWaveLevels(prev => prev.map(() => 0.2 + Math.random() * 0.8));
    }, 120);
    waveIntervalRef.current = id;

    return () => {
      clearInterval(id);
      waveIntervalRef.current = null;
    };
  }, [live]);

  function sendChatMessage() {
    const text = chatDraft.trim();
    if (!text && !chatImage) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const sender = (displayName || "").trim() || "User";
    try {
      wsRef.current.send(
        JSON.stringify({
          type: "chat",
          sender,
          text,
          image: chatImage,
          stream_id: streamIdRef.current,
        })
      );
      setChatDraft("");
      setChatImage(null);
    } catch {}
  }

  function onChatImagePick(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 600000) {
      alert("Image too large (max ~600KB)");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setChatImage(reader.result);
    reader.readAsDataURL(file);
  }

  useEffect(() => {
    if (!chatOpen || !chatScrollRef.current) return;
    chatScrollRef.current.scrollTop = 0;
  }, [chatMessages, chatOpen]);

  useEffect(() => {
    if (!scrollRef.current) return;
  }, [lines, live]);
  useEffect(() => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 50;
    if (isNearBottom) {
      try {
        el.scrollTop = el.scrollHeight;
      } catch {}
    }
  }, [lines, live]);

  if (!authReady) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#0b0f1a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        Loading workspace…
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "Inter, system-ui, Arial", background: themed("#0b0f1a", "#f4f5fb"), color: themed("#e6e8f0", "#0b1120"), margin: 0 }}>
      {/* Header */}
      <div style={{ height: 56, borderBottom: "1px solid " + themed("#1f2430", "#e5e7eb"), display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 16px", background: themed("#0e1424", "#ffffff") }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg,#1f8ef1,#6a11cb)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>AI</div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 600 }}>Meeting Live</div>
            <div style={{ fontSize: 12, color: themed("#8a94a6", "#6b7280"), display: "flex", alignItems: "center", gap: 6 }}>
              <IconDot color={connected ? "#22c55e" : connecting ? "#eab308" : "#ef4444"} />
              {connected ? "Connected" : connecting ? "Connecting…" : "Disconnected"}
            </div>
            {authUser ? (
              <div style={{ fontSize: 11, color: themed("#8a94a6", "#6b7280"), marginTop: 4 }}>
                {authUser.full_name || authUser.email}
                {authUser.role === "admin" ? (
                  <span style={{ color: "#a78bfa" }}> · Admin</span>
                ) : null}
              </div>
            ) : null}
            {connectionError ? (
              <div style={{ fontSize: 11, color: "#f87171", marginTop: 2, maxWidth: 220 }}>{connectionError}</div>
            ) : null}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {authUser?.role === "admin" ? (
            <Link
              href="/admin"
              style={{
                padding: "7px 14px",
                borderRadius: 8,
                background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 4px 14px rgba(99, 102, 241, 0.45)",
                whiteSpace: "nowrap",
              }}
            >
              Admin Dashboard
            </Link>
          ) : null}
          <input
            value={wsUrl}
            onChange={(e) => setWsUrl(e.target.value)}
            placeholder="ws://localhost:8765"
            style={{ background: themed("#0b1120", "#f9fafb"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "6px 10px", borderRadius: 6, width: 260 }}
          />
          <button
            type="button"
            onClick={handleLogout}
            style={{
              background: "transparent",
              border: "1px solid " + themed("#334155", "#d1d5db"),
              color: themed("#94a3b8", "#6b7280"),
              padding: "6px 10px",
              borderRadius: 6,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Logout
          </button>
          <button
            onClick={() => connect(wsUrl)}
            disabled={connecting || connected}
            style={{
              background: themed("#1d3a7a", "#2563eb"),
              border: "1px solid " + themed("#2a3a6b", "#1d4ed8"),
              color: themed("#e6e8f0", "#f9fafb"),
              padding: "6px 10px",
              borderRadius: 6,
              opacity: connecting || connected ? 0.6 : 1,
            }}
          >
            {connecting ? "Connecting…" : "Connect"}
          </button>
          <button
            onClick={endCall}
            disabled={!connected && !connecting}
            style={{
              background: themed("#4b1120", "#fee2e2"),
              border: "1px solid " + themed("#702d3a", "#fecaca"),
              color: themed("#f87171", "#b91c1c"),
              padding: "6px 10px",
              borderRadius: 6,
              opacity: !connected && !connecting ? 0.6 : 1,
            }}
          >
            Disconnect
          </button>
          <button
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            style={{
              background: themed("#111827", "#f3f4f6"),
              border: "1px solid " + themed("#1f2937", "#d1d5db"),
              color: themed("#e5e7eb", "#111827"),
              padding: "6px 10px",
              borderRadius: 6,
            }}
          >
            {theme === "dark" ? "Light" : "Dark"} Mode
          </button>
        </div>
      </div>

      {/* Participants */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid " + themed("#1f2430", "#e5e7eb"), background: themed("#0d1322", "#f9fafb"), display: "flex", alignItems: "center", gap: 8, overflowX: "auto" }}>
        <IconUsers />
        <div style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 13, marginRight: 4 }}>Participants</div>
        {participants.length === 0 && <div style={{ color: themed("#6b7280", "#9ca3af"), fontSize: 13 }}>{connected ? "Joining…" : "Connect to join the meeting"}</div>}
        {participants.map((p, idx) => {
          const isActive = Date.now() - (lastActiveRef.current[p] || 0) < 2000;
          return (
            <div
              key={p + idx}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 10px",
                borderRadius: 9999,
                background: isActive ? themed("#12223d", "#e0ecff") : themed("#0f172a", "#f3f4f6"),
                border: "1px solid " + (isActive ? themed("#265ba6", "#2563eb") : themed("#1f2430", "#e5e7eb")),
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 9999, background: colorFor(p) }} />
              <span style={{ fontSize: 13 }}>{p}</span>
            </div>
          );
        })}
      </div>


      {/* Body: Zoom-style layout */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* Stage area (center video grid placeholder) */}
        <div style={{ flex: 3, minWidth: 0, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              flex: 1,
              minHeight: 0,
              borderRadius: 12,
              background: themed("#020617", "#e5e7eb"),
              border: "none",
              boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
              display: "flex",
              flexDirection: "column",
              padding: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <IconVideo off={!camOn} />
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>Meeting stage</span>
                  <span style={{ fontSize: 11, color: themed("#9ca3af", "#4b5563") }}>Video area (Zoom-like layout)</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 11, color: themed("#9ca3af", "#4b5563") }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <IconMic muted={!micOn} />
                  <span>{micOn ? "Mic on" : "Mic muted"}</span>
                </div>
                <div style={{ width: 1, height: 16, background: themed("#1f2937", "#d1d5db") }} />
                <span>{`Audio: ${audioTransport === "webrtc" ? "WebRTC" : audioTransport === "ws" ? "WebSocket" : webrtcStatus}`}</span>
                <div style={{ width: 1, height: 16, background: themed("#1f2937", "#d1d5db") }} />
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <IconDot color={connected ? "#22c55e" : "#6b7280"} size={8} />
                  <span>{formatDuration(elapsedSeconds)}</span>
                </div>
              </div>
            </div>
            <div
              style={{
                flex: 1,
                minHeight: 0,
                borderRadius: 12,
                border: "none",
                background: themed("radial-gradient(circle at top,#1e293b,#020617)", "linear-gradient(135deg,#e5e7eb,#f9fafb)"),
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 16,
                textAlign: "center",
                color: themed("#9ca3af", "#4b5563"),
                fontSize: 14,
                position: "relative",
                overflow: "hidden",
              }}
            >
              {camOn && (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    borderRadius: 12,
                  }}
                />
              )}
              {subtitleMode && showLive && subtitle?.text && (
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    bottom: 20,
                    transform: "translateX(-50%)",
                    maxWidth: "90%",
                    background: "rgba(0,0,0,0.72)",
                    color: "#fff",
                    padding: "10px 18px",
                    borderRadius: 8,
                    fontSize: 20,
                    fontWeight: 600,
                    textAlign: "center",
                    zIndex: 5,
                    pointerEvents: "none",
                  }}
                >
                  {subtitle.text}
                </div>
              )}
              {!camOn && participants.length > 0 ? (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
                  {participants.map((p, idx) => (
                    <div
                      key={p + idx}
                      style={{
                        width: 140,
                        height: 90,
                        borderRadius: 10,
                        background: themed("#020617", "#e5e7eb"),
                        border: "1px solid " + themed("#1f2937", "#d1d5db"),
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 6,
                      }}
                    >
                      <div
                        style={{
                          width: 36,
                          height: 36,
                          borderRadius: 9999,
                          background: colorFor(p),
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#ffffff",
                          fontSize: 14,
                          fontWeight: 700,
                        }}
                      >
                        {initialsFor(p)}
                      </div>
                      <span style={{ fontSize: 12 }}>{p}</span>
                    </div>
                  ))}
                </div>
              ) : !camOn ? (
                <div>
                  <div style={{ marginBottom: 8 }}>Click "Start Video" for your camera preview.</div>
                  <div>Live captions appear in the sidebar and as subtitles below.</div>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {/* Right sidebar: transcript + summaries */}
        <div
          style={{
            width: 380,
            maxWidth: "34%",
            minWidth: 320,
            borderLeft: "1px solid " + themed("#1f2430", "#e5e7eb"),
            background: themed("#020617", "#f9fafb"),
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          {/* Transcript panel */}
          <div style={{ borderBottom: "1px solid " + themed("#1f2430", "#e5e7eb"), padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>Live Transcript</span>
              {showLive && live && (
                <span style={{ fontSize: 11, color: themed("#22c55e", "#16a34a") }}>Listening…</span>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button onClick={() => setShowLive((s) => !s)} style={{ background: themed("#11162a", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "4px 8px", borderRadius: 6, fontSize: 12 }}>
                {showLive ? "Hide live" : "Show live"}
              </button>
              <button onClick={() => setLines([])} style={{ background: themed("#11162a", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "4px 8px", borderRadius: 6, fontSize: 12 }}>
                Clear
              </button>
            </div>
          </div>

          <div ref={scrollRef} style={{ padding: 16, overflowY: "auto", flex: 1, minHeight: 0 }}>
            {connected && !live && lines.length === 0 && (
              <div style={{ color: themed("#9ca3af", "#6b7280"), fontSize: 13, lineHeight: 1.5, padding: "8px 4px" }}>
                <div style={{ marginBottom: 6 }}>No transcript yet.</div>
                <div>1. URL must be <strong>ws://localhost:8765</strong></div>
                <div>2. Click <strong>Unmute</strong> (Mic on)</div>
                <div>3. Speak a full sentence, wait 3–5 seconds</div>
                <div style={{ marginTop: 8 }}>
                  Audio: {audioTransport === "ws" ? "WebSocket OK (sending to ASR)" : audioTransport === "webrtc" ? "WebRTC OK" : "NOT sending — Connect + Unmute mic"}
                </div>
              </div>
            )}
            {showLive && live && (
              <div style={{ marginBottom: 12, padding: 12, background: themed("#10182b", "#0f172a"), border: cardBorder, borderRadius: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 12 }}>[{live.ts}]</span>
                  <span style={{ fontWeight: 700, color: colorFor(live.speaker) }}>{live.speaker}</span>
                  <span style={{ marginLeft: 6, color: themed("#8a94a6", "#6b7280"), fontSize: 11 }}>(live)</span>
                </div>
                <div>{live.text}</div>
                <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
                  <VoiceWave
                    active={Boolean(live && live.text)}
                    levels={waveLevels}
                    color={colorFor(live.speaker)}
                  />
                </div>
              </div>
            )}
            {lines.map((ln, idx) => (
              <div key={idx} style={{ marginBottom: 10, padding: 12, background: themed("#0f1629", "#f8fafc"), border: cardBorder, borderRadius: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 12 }}>[{ln.timestamp}]</span>
                  <span style={{ fontWeight: 700, color: colorFor(ln.speaker) }}>{ln.speaker}</span>
                </div>
                <div>{ln.text}</div>
              </div>
            ))}
          </div>

          {/* Summaries panel */}
          {showSummaries && (
          <>
          <div style={{ borderTop: "1px solid " + themed("#1f2430", "#e5e7eb"), padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{summaryView === "full" ? "Meeting Summary" : "Rolling Summaries"}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => {
                  setSummaries([]);
                  setFullSummary(null);
                  setSummaryView("list");
                }}
                style={{
                  background: themed("#11162a", "#f3f4f6"),
                  border: "1px solid " + themed("#1f2430", "#d1d5db"),
                  color: themed("#e6e8f0", "#111827"),
                  padding: "4px 8px",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                Clear
              </button>
              <button
                onClick={() => setSummaryView("full")}
                disabled={!fullSummary}
                style={{
                  background: themed("#1d3a7a", "#2563eb"),
                  border: "1px solid " + themed("#2a3a6b", "#1d4ed8"),
                  color: themed("#e6e8f0", "#f9fafb"),
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 12,
                  opacity: fullSummary ? 1 : 0.7,
                  cursor: fullSummary ? "pointer" : "default",
                }}
              >
                Full summary
              </button>
            </div>
          </div>
          <div style={{ padding: 16, overflowY: "auto", display: "grid", gap: 12, maxHeight: "40vh" }}>
            {summaryView === "full" ? (
              <>
                {!fullSummary && (
                  <div style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 13 }}>
                    Full meeting summary will appear here after the call ends.
                  </div>
                )}
                {fullSummary && (
                  <div
                    style={{
                      background: themed("#0f172a", "#ffffff"),
                      border: "1px solid " + themed("#1f2430", "#e5e7eb"),
                      borderRadius: 12,
                      padding: 14,
                      boxShadow: "0 18px 40px rgba(0,0,0,0.35)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>Full meeting summary</span>
                        <span style={{ fontSize: 11, color: themed("#9ca3af", "#6b7280") }}>
                          High-level recap of everything discussed in this session.
                        </span>
                      </div>
                      <button
                        onClick={() => setSummaryView("list")}
                        style={{
                          background: themed("#11162a", "#f3f4f6"),
                          border: "1px solid " + themed("#1f2430", "#d1d5db"),
                          color: themed("#e6e8f0", "#111827"),
                          padding: "4px 10px",
                          borderRadius: 6,
                          fontSize: 12,
                        }}
                      >
                        Back to summaries
                      </button>
                    </div>
                    <div style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 12, marginBottom: 6 }}>[{fullSummary.timestamp}]</div>
                    <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{fullSummary.text}</div>
                  </div>
                )}
              </>
            ) : (
              <>
                {summaries.length === 0 && (
                  <div style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 13 }}>
                    Rolling summaries will appear here every 5 seconds as the meeting progresses.
                  </div>
                )}
                {summaries.map((s, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: themed("#11162a", "#ffffff"),
                      border: "1px solid " + themed("#1f2430", "#e5e7eb"),
                      borderRadius: 12,
                      padding: 12,
                      boxShadow: "0 0 0 1px rgba(255,255,255,0.02) inset",
                    }}
                  >
                    <div style={{ color: themed("#8a94a6", "#6b7280"), fontSize: 12, marginBottom: 8 }}>[{s.timestamp}]</div>
                    <div style={{ whiteSpace: "pre-wrap" }}>{s.text}</div>
                  </div>
                ))}
              </>
            )}
          </div>
          </>
          )}
        </div>
      </div>

      {/* Control Bar */}
      <div style={{ height: 64, borderTop: "1px solid " + themed("#1f2430", "#e5e7eb"), background: themed("#0e1424", "#ffffff"), display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        {/* Left controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button onClick={() => setMicOn((m) => !m)} style={{ background: themed("#0b1120", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "10px 14px", borderRadius: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <IconMic muted={!micOn} /> <span style={{ fontSize: 13 }}>{micOn ? "Mute" : "Unmute"}</span>
          </button>
          <button onClick={requestMicPermission} style={{ background: themed("#0b1120", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "10px 14px", borderRadius: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <IconMic muted={!permissionGranted} /> <span style={{ fontSize: 13 }}>{permissionGranted ? "Mic Allowed" : "Allow Mic"}</span>
          </button>
          {devices.length > 0 && (
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              style={{ background: themed("#0b1120", "#f9fafb"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "8px 10px", borderRadius: 8, fontSize: 13 }}
            >
              {devices.map((d) => (
                <option key={d.deviceId || d.label} value={d.deviceId}>
                  {d.label || d.deviceId || "Audio device"}
                </option>
              ))}
            </select>
          )}
          <button onClick={() => setCamOn((c) => !c)} style={{ background: themed("#0b1120", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "10px 14px", borderRadius: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <IconVideo off={!camOn} /> <span style={{ fontSize: 13 }}>{camOn ? "Stop Video" : "Start Video"}</span>
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: themed("#9ca3af", "#4b5563") }}>
            <span>Headphones</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={monitorVolume}
              onChange={(e) => setMonitorVolume(parseFloat(e.target.value))}
              style={{ width: 90 }}
            />
          </label>
        </div>

        {/* Center controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button onClick={() => setSubtitleMode((s) => !s)} style={{ background: themed("#0b1120", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "10px 14px", borderRadius: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <IconCC /> <span style={{ fontSize: 13 }}>{subtitleMode ? "Hide CC" : "Show CC"}</span>
          </button>
          <select
            value={subtitleLang}
            onChange={(e) => {
              const next = e.target.value;
              setSubtitleLang(next);
              try {
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                  wsRef.current.send(
                    JSON.stringify({
                      type: "config",
                      stream_id: streamIdRef.current,
                      language: "en",
                      translate_to: next === "en" ? "" : next,
                    })
                  );
                }
              } catch {}
            }}
            style={{ background: themed("#0b1120", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), padding: "8px 10px", borderRadius: 10, fontSize: 13 }}
          >
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="ta">Tamil</option>
          </select>
          <button
            onClick={() => setSettingsOpen((o) => !o)}
            style={{
              background: settingsOpen ? themed("#1d3a7a", "#2563eb") : themed("#0b1120", "#f3f4f6"),
              border: "1px solid " + themed("#1f2430", "#d1d5db"),
              color: themed("#e6e8f0", "#111827"),
              padding: "10px 14px",
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <IconSettings /> <span style={{ fontSize: 13 }}>Settings</span>
          </button>
          <button
            onClick={toggleChatPanel}
            style={{
              position: "relative",
              background: chatOpen ? themed("#1d3a7a", "#2563eb") : themed("#0b1120", "#f3f4f6"),
              border: "1px solid " + themed("#1f2430", "#d1d5db"),
              color: themed("#e6e8f0", "#111827"),
              padding: "10px 14px",
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <IconChat /> <span style={{ fontSize: 13 }}>{chatOpen ? "Hide Chat" : "Chat"}</span>
            {chatUnread > 0 && (
              <span
                style={{
                  position: "absolute",
                  top: -6,
                  right: -6,
                  minWidth: 20,
                  height: 20,
                  padding: "0 6px",
                  borderRadius: 9999,
                  background: "#ef4444",
                  color: "#fff",
                  fontSize: 11,
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 2px 8px rgba(239,68,68,0.6)",
                }}
              >
                {chatUnread > 99 ? "99+" : chatUnread}
              </span>
            )}
          </button>
        </div>

        {/* Right controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: themed("#e5e7eb", "#111827") }}>
            <IconDot color="red" size={8} />
            <span>{formatDuration(elapsedSeconds)}</span>
          </div>
          <button onClick={endCall} style={{ background: themed("#b91c1c", "#ef4444"), border: "1px solid " + themed("#7f1d1d", "#b91c1c"), color: "#fff", padding: "10px 14px", borderRadius: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <IconPhoneEnd /> <span style={{ fontSize: 13 }}>End</span>
          </button>
        </div>
      </div>

      {/* Chat message popup */}
      {chatToast && !chatOpen && (
        <button
          type="button"
          onClick={toggleChatPanel}
          style={{
            position: "fixed",
            right: 24,
            bottom: 88,
            zIndex: 60,
            maxWidth: 320,
            background: themed("#1e3a5f", "#2563eb"),
            border: "1px solid " + themed("#3b82f6", "#1d4ed8"),
            color: "#fff",
            padding: "12px 16px",
            borderRadius: 12,
            boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 4 }}>New chat message</div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{chatToast.sender}</div>
          <div style={{ fontSize: 13, marginTop: 4, opacity: 0.95 }}>{chatToast.text}</div>
        </button>
      )}

      {/* Settings panel */}
      {settingsOpen && (
        <div
          style={{
            position: "fixed",
            right: 24,
            bottom: 88,
            width: 300,
            background: themed("#0b1120", "#ffffff"),
            border: "1px solid " + themed("#1f2430", "#e5e7eb"),
            borderRadius: 12,
            boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
            zIndex: 55,
            padding: 14,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 15 }}>Settings</div>
          {[
            { label: "Show live transcript (sidebar)", value: showLive, set: setShowLive },
            { label: "Show subtitles (CC)", value: subtitleMode, set: setSubtitleMode },
            { label: "Show rolling summaries", value: showSummaries, set: setShowSummaries },
          ].map((row) => (
            <label
              key={row.label}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 0",
                fontSize: 13,
                cursor: "pointer",
                borderBottom: "1px solid " + themed("#1f2430", "#e5e7eb"),
              }}
            >
              <span>{row.label}</span>
              <input type="checkbox" checked={row.value} onChange={(e) => row.set(e.target.checked)} />
            </label>
          ))}
          <button
            type="button"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            style={{
              marginTop: 10,
              width: "100%",
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid " + themed("#1f2430", "#d1d5db"),
              background: themed("#11162a", "#f3f4f6"),
              color: themed("#e6e8f0", "#111827"),
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Switch to {theme === "dark" ? "Light" : "Dark"} mode
          </button>
          <button
            type="button"
            onClick={() => {
              setLines([]);
              setLive(null);
              liveRef.current = null;
            }}
            style={{
              marginTop: 8,
              width: "100%",
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid " + themed("#7f1d1d", "#fecaca"),
              background: themed("#4b1120", "#fee2e2"),
              color: themed("#f87171", "#b91c1c"),
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Clear transcript history
          </button>
        </div>
      )}

      {/* Chat panel */}
      {chatOpen && (
        <div
          style={{
            position: "fixed",
            left: 16,
            bottom: 80,
            width: 360,
            maxWidth: "92vw",
            height: 420,
            maxHeight: "55vh",
            background: themed("#0b1120", "#ffffff"),
            border: "1px solid " + themed("#1f2430", "#e5e7eb"),
            borderRadius: 12,
            boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
            display: "flex",
            flexDirection: "column",
            zIndex: 50,
          }}
        >
          <div style={{ padding: "12px 14px", borderBottom: "1px solid " + themed("#1f2430", "#e5e7eb"), fontWeight: 600 }}>
            Meeting Chat
          </div>
          <div ref={chatScrollRef} style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column-reverse", gap: 10 }}>
            {chatMessages.length === 0 && (
              <div style={{ color: themed("#9ca3af", "#6b7280"), fontSize: 13 }}>
                Say hi — e.g. ashish: hello, abhinandan: hi
              </div>
            )}
            {chatMessages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.sender === (displayName || "User") ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                  background: themed("#11162a", "#f3f4f6"),
                  border: "1px solid " + themed("#1f2430", "#e5e7eb"),
                  borderRadius: 10,
                  padding: "8px 10px",
                }}
              >
                <div style={{ fontSize: 11, color: colorFor(m.sender), fontWeight: 600, marginBottom: 4 }}>
                  {m.sender} · {m.timestamp}
                </div>
                {m.text && <div style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{m.text}</div>}
                {m.image && (
                  <img src={m.image} alt="shared" style={{ marginTop: 6, maxWidth: "100%", borderRadius: 8 }} />
                )}
              </div>
            ))}
          </div>
          <div style={{ padding: 10, borderTop: "1px solid " + themed("#1f2430", "#e5e7eb"), display: "flex", flexDirection: "column", gap: 8 }}>
            {chatImage && (
              <div style={{ position: "relative" }}>
                <img src={chatImage} alt="preview" style={{ maxHeight: 80, borderRadius: 8 }} />
                <button
                  type="button"
                  onClick={() => setChatImage(null)}
                  style={{ position: "absolute", top: 4, right: 4, background: "#ef4444", color: "#fff", border: "none", borderRadius: 4, padding: "2px 6px", fontSize: 11 }}
                >
                  ✕
                </button>
              </div>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={chatDraft}
                onChange={(e) => setChatDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                  }
                }}
                placeholder="Type a message..."
                style={{
                  flex: 1,
                  background: themed("#020617", "#f9fafb"),
                  border: "1px solid " + themed("#1f2430", "#d1d5db"),
                  color: themed("#e6e8f0", "#111827"),
                  borderRadius: 8,
                  padding: "8px 10px",
                  fontSize: 14,
                }}
              />
              <input ref={chatFileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={onChatImagePick} />
              <button
                type="button"
                onClick={() => chatFileRef.current?.click()}
                style={{ background: themed("#11162a", "#f3f4f6"), border: "1px solid " + themed("#1f2430", "#d1d5db"), color: themed("#e6e8f0", "#111827"), borderRadius: 8, padding: "8px 10px", fontSize: 12 }}
              >
                📷
              </button>
              <button
                type="button"
                onClick={sendChatMessage}
                disabled={!connected}
                style={{ background: themed("#2563eb", "#2563eb"), border: "none", color: "#fff", borderRadius: 8, padding: "8px 14px", fontSize: 13, opacity: connected ? 1 : 0.5 }}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Subtitle Overlay */}
      {subtitleMode && subtitle && (
        <div style={{ position: "fixed", left: 0, right: 0, bottom: 24, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
          <div
            style={{
              maxWidth: 960,
              background: "rgba(0,0,0,0.8)",
              border: "none",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: 8,
              fontSize: 22,
              fontWeight: 600,
              lineHeight: 1.35,
              textAlign: "center",
              boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
            }}
          >
            {subtitle.text}
          </div>
        </div>
      )}
    </div>
  );
}
