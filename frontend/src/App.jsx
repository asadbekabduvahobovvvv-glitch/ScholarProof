import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "https://scholarproof.onrender.com";

const translations = {
  en: {
    verify: "Verify",
    how: "How it works",
    history: "History",
    badge: "AI + Official Source Verification",
    title1: "Don't trust it.",
    title2: "Verify it.",
    subtitle:
      "Check scholarships, admissions, deadlines and suspicious offers against reliable official sources.",
    text: "Text",
    url: "URL",
    screenshot: "Screenshot",
    verifyButton: "Verify with ScholarProof",
    verifying: "Verifying...",
    textarea:
      "Paste a scholarship offer, university requirement, Telegram message or suspicious claim...",
    urlPlaceholder: "https://example.com/scholarship",
    upload: "Upload screenshot",
    uploadHelp:
      "Instagram, Telegram, WhatsApp, email or website screenshot",
    demo: "DEMO MODE",
    demoText: "No API credits are being used.",
    recent: "Recent verifications",
    clear: "Clear",
    noHistory: "No recent verification history yet.",
    howTitle: "From claim to evidence.",
    step1: "Extract",
    step1d: "Important factual claims are separated.",
    step2: "Research",
    step2d: "Official and current sources are checked.",
    step3: "Verify",
    step3d: "Each claim receives an evidence-based verdict.",
    step4: "Protect",
    step4d: "Suspicious payment and impersonation signals are flagged.",
    report: "SCHOLARPROOF REPORT",
    verdict: "OVERALL VERDICT",
    claims: "CLAIM ANALYSIS",
    security: "SECURITY REVIEW",
    next: "WHAT TO DO NEXT",
    sources: "SOURCES",
    another: "Start another verification",
    copy: "Copy report",
    copied: "Copied!",
    official: "Official source",
    evidence: "Official evidence",
    deep: "DEEP VERIFICATION",
    accuracy: "Accuracy matters more than speed.",
    openSource: "Open source",
    supporting: "Supporting source",
    sourceUnavailable: "No validated source link",
  },

  uz: {
    verify: "Tekshirish",
    how: "Qanday ishlaydi",
    history: "Tarix",
    badge: "AI + Rasmiy manbalar orqali tekshiruv",
    title1: "Ishonishdan oldin.",
    title2: "Tekshir.",
    subtitle:
      "Grant, qabul talablari, deadline va shubhali takliflarni rasmiy manbalar orqali tekshiring.",
    text: "Matn",
    url: "Havola",
    screenshot: "Skrinshot",
    verifyButton: "ScholarProof bilan tekshirish",
    verifying: "Tekshirilmoqda...",
    textarea:
      "Grant e'loni, universitet talabi, Telegram xabari yoki shubhali ma'lumotni kiriting...",
    urlPlaceholder: "https://example.com/scholarship",
    upload: "Skrinshot yuklash",
    uploadHelp:
      "Instagram, Telegram, WhatsApp, email yoki sayt skrinshoti",
    demo: "DEMO REJIM",
    demoText: "API balans ishlatilmayapti.",
    recent: "Oxirgi tekshiruvlar",
    clear: "Tozalash",
    noHistory: "Hali tekshiruv tarixi yo'q.",
    howTitle: "Da'vodan dalilgacha.",
    step1: "Ajratish",
    step1d: "Muhim faktlar alohida ajratiladi.",
    step2: "Izlanish",
    step2d: "Eng yangi rasmiy manbalar tekshiriladi.",
    step3: "Tekshirish",
    step3d: "Har bir da'voga dalil asosida hukm beriladi.",
    step4: "Himoya",
    step4d: "Shubhali to'lov va soxta profil belgilari aniqlanadi.",
    report: "SCHOLARPROOF HISOBOTI",
    verdict: "UMUMIY XULOSA",
    claims: "DA'VOLAR TAHLILI",
    security: "XAVFSIZLIK TAHLILI",
    next: "KEYINGI QADAMLAR",
    sources: "MANBALAR",
    another: "Yangi tekshiruv boshlash",
    copy: "Hisobotni nusxalash",
    copied: "Nusxalandi!",
    official: "Rasmiy manba",
    evidence: "Rasmiy dalil",
    deep: "CHUQUR TEKSHIRUV",
    accuracy: "Tezlikdan ko'ra aniqlik muhim.",
    openSource: "Manbani ochish",
    supporting: "Qo‘shimcha manba",
    sourceUnavailable: "Tasdiqlangan manba havolasi yo‘q",
  },

  ru: {
    verify: "Проверить",
    how: "Как это работает",
    history: "История",
    badge: "AI + проверка официальных источников",
    title1: "Не доверяй сразу.",
    title2: "Проверь.",
    subtitle:
      "Проверяйте стипендии, требования, дедлайны и подозрительные предложения по официальным источникам.",
    text: "Текст",
    url: "Ссылка",
    screenshot: "Скриншот",
    verifyButton: "Проверить с ScholarProof",
    verifying: "Проверяем...",
    textarea:
      "Вставьте предложение о стипендии, требование университета или подозрительное сообщение...",
    urlPlaceholder: "https://example.com/scholarship",
    upload: "Загрузить скриншот",
    uploadHelp:
      "Скриншот из Instagram, Telegram, WhatsApp, email или сайта",
    demo: "ДЕМО РЕЖИМ",
    demoText: "API-кредиты не используются.",
    recent: "Последние проверки",
    clear: "Очистить",
    noHistory: "Истории проверок пока нет.",
    howTitle: "От заявления к доказательству.",
    step1: "Извлечение",
    step1d: "Важные утверждения выделяются отдельно.",
    step2: "Исследование",
    step2d: "Проверяются актуальные официальные источники.",
    step3: "Проверка",
    step3d: "Каждое утверждение получает обоснованный статус.",
    step4: "Защита",
    step4d: "Выявляются подозрительные платежи и признаки мошенничества.",
    report: "ОТЧЕТ SCHOLARPROOF",
    verdict: "ОБЩИЙ ВЕРДИКТ",
    claims: "АНАЛИЗ УТВЕРЖДЕНИЙ",
    security: "ПРОВЕРКА БЕЗОПАСНОСТИ",
    next: "ЧТО ДЕЛАТЬ ДАЛЬШЕ",
    sources: "ИСТОЧНИКИ",
    another: "Начать новую проверку",
    copy: "Копировать отчет",
    copied: "Скопировано!",
    official: "Официальный источник",
    evidence: "Официальное подтверждение",
    deep: "ГЛУБОКАЯ ПРОВЕРКА",
    accuracy: "Точность важнее скорости.",
    openSource: "Открыть источник",
    supporting: "Дополнительный источник",
    sourceUnavailable: "Нет подтвержденной ссылки на источник",
  },
};

const STATUS = {
  verified: {
    icon: "✓",
    label: "VERIFIED",
    className: "verified",
  },
  partial: {
    icon: "!",
    label: "PARTIALLY VERIFIED",
    className: "partial",
  },
  contradicted: {
    icon: "×",
    label: "CONTRADICTED",
    className: "contradicted",
  },
  insufficient: {
    icon: "?",
    label: "INSUFFICIENT EVIDENCE",
    className: "insufficient",
  },
};


function sourceDomain(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase();

    return hostname.startsWith("www.")
      ? hostname.slice(4)
      : hostname;
  } catch {
    return "";
  }
}

function sourceKey(url) {
  try {
    const parsed = new URL(url);

    const hostname = parsed.hostname
      .toLowerCase()
      .replace(/^www\./, "");

    const pathname =
      parsed.pathname === "/"
        ? "/"
        : parsed.pathname.replace(/\/+$/, "");

    return `${hostname}${pathname}`.toLowerCase();
  } catch {
    return (url || "").trim().toLowerCase();
  }
}

function uniqueSources(sources = []) {
  const seen = new Set();

  return sources.filter((source) => {
    if (!source?.url) return false;

    const key = sourceKey(source.url);

    if (!key || seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}


function AdminPanel() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const adminStyles = `
    * { box-sizing: border-box; }

    .admin-shell {
      min-height: 100vh;
      padding: 40px 18px;
      background:
        radial-gradient(circle at 15% 15%, rgba(95, 96, 255, .18), transparent 35%),
        radial-gradient(circle at 85% 85%, rgba(35, 208, 255, .12), transparent 35%),
        #080b12;
      color: #f5f7ff;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .admin-wrap {
      width: min(980px, 100%);
      margin: 0 auto;
    }

    .admin-brand {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 28px;
    }

    .admin-brand h1 {
      margin: 0;
      font-size: clamp(26px, 4vw, 42px);
      letter-spacing: -0.04em;
    }

    .admin-brand p {
      margin: 6px 0 0;
      color: #9da8bd;
    }

    .admin-back {
      color: #c9d1ff;
      text-decoration: none;
      border: 1px solid #27314a;
      border-radius: 12px;
      padding: 10px 14px;
      background: rgba(255,255,255,.03);
    }

    .admin-card {
      background: rgba(15, 20, 32, .88);
      border: 1px solid #242c42;
      border-radius: 22px;
      padding: 24px;
      box-shadow: 0 24px 90px rgba(0,0,0,.28);
      backdrop-filter: blur(14px);
    }

    .admin-login {
      width: min(460px, 100%);
      margin: 70px auto 0;
    }

    .admin-login h2 {
      margin: 0 0 8px;
    }

    .admin-muted {
      color: #98a4ba;
      line-height: 1.55;
    }

    .admin-field {
      display: grid;
      gap: 8px;
      margin-top: 18px;
    }

    .admin-field label {
      font-size: 13px;
      color: #b6c0d4;
    }

    .admin-field input {
      width: 100%;
      border: 1px solid #2b3550;
      background: #0b101b;
      color: #fff;
      border-radius: 12px;
      padding: 13px 14px;
      outline: none;
    }

    .admin-field input:focus {
      border-color: #6978ff;
      box-shadow: 0 0 0 3px rgba(105,120,255,.13);
    }

    .admin-primary,
    .admin-secondary,
    .admin-danger {
      border: 0;
      border-radius: 12px;
      padding: 12px 16px;
      cursor: pointer;
      font-weight: 700;
    }

    .admin-primary {
      width: 100%;
      margin-top: 20px;
      color: #fff;
      background: linear-gradient(135deg, #6875ff, #925fff);
    }

    .admin-secondary {
      color: #e9edff;
      background: #1b2234;
      border: 1px solid #2c3650;
    }

    .admin-danger {
      color: #fff;
      background: #b72f42;
    }

    button:disabled {
      opacity: .55;
      cursor: not-allowed;
    }

    .admin-error {
      margin-top: 16px;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid #6d2936;
      color: #ffc4ce;
      background: #2a1118;
    }

    .admin-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .admin-stat {
      background: #0c111d;
      border: 1px solid #222b40;
      border-radius: 16px;
      padding: 18px;
    }

    .admin-stat small {
      display: block;
      color: #8f9ab0;
      margin-bottom: 8px;
    }

    .admin-stat strong {
      font-size: 22px;
      overflow-wrap: anywhere;
    }

    .admin-status-ok { color: #5de2a2; }
    .admin-status-warn { color: #ffd36b; }
    .admin-status-danger { color: #ff798b; }

    .admin-controls {
      display: grid;
      gap: 14px;
      margin-top: 22px;
    }

    .admin-control {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 18px;
      background: #0c111d;
      border: 1px solid #222b40;
      border-radius: 16px;
    }

    .admin-control h3 {
      margin: 0 0 5px;
      font-size: 16px;
    }

    .admin-control p {
      margin: 0;
      color: #8f9ab0;
      font-size: 13px;
      line-height: 1.45;
    }

    .admin-switch {
      min-width: 96px;
    }

    .admin-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }

    .admin-note {
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 14px;
      background: #15131f;
      border: 1px solid #332d49;
      color: #c9c2db;
      font-size: 13px;
      line-height: 1.55;
    }

    @media (max-width: 700px) {
      .admin-grid { grid-template-columns: 1fr; }
      .admin-control { align-items: flex-start; flex-direction: column; }
      .admin-switch { width: 100%; }
      .admin-switch button { width: 100%; }
      .admin-brand { align-items: flex-start; flex-direction: column; }
    }
  `;

  async function adminFetch(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401) {
        setAuthenticated(false);
        setStatus(null);
      }

      throw new Error(
        data.detail || "Admin request failed."
      );
    }

    return data;
  }

  async function loadStatus() {
    setBusy(true);
    setError("");

    try {
      const data = await adminFetch(
        "/admin/status",
        {
          method: "GET",
        }
      );

      setStatus(data);
      setAuthenticated(true);
    } catch (err) {
      if (!/login required/i.test(err.message)) {
        setError(err.message);
      }

      setAuthenticated(false);
      setStatus(null);
    } finally {
      setBusy(false);
      setCheckingSession(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await adminFetch("/admin/login", {
        method: "POST",
        body: JSON.stringify({
          username,
          password,
        }),
      });

      setPassword("");

      await loadStatus();

      if (!authenticated) {
        // loadStatus updates state asynchronously; status is the
        // authoritative confirmation that the HttpOnly cookie worked.
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateSettings(changes) {
    setBusy(true);
    setError("");

    try {
      if (changes.demo_mode === false) {
        const confirmed = window.confirm(
          "Enable REAL AI verification? Public Verify requests can spend your OpenAI API balance."
        );

        if (!confirmed) {
          setBusy(false);
          return;
        }
      }

      const data = await adminFetch(
        "/admin/settings",
        {
          method: "POST",
          body: JSON.stringify(changes),
        }
      );

      setStatus(data.status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    setError("");

    try {
      await adminFetch(
        "/admin/logout",
        {
          method: "POST",
          body: "{}",
        }
      );
    } catch {
      // Clear local UI state even when the cookie already expired.
    } finally {
      setAuthenticated(false);
      setStatus(null);
      setUsername("");
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <div className="admin-shell">
      <style>{adminStyles}</style>

      <div className="admin-wrap">
        <div className="admin-brand">
          <div>
            <h1>ScholarProof Admin</h1>
            <p>Private control panel · CYBERTEZ</p>
          </div>

          <a className="admin-back" href="/">
            ← Public site
          </a>
        </div>

        {checkingSession ? (
          <div className="admin-card admin-login">
            <p className="admin-muted">Checking secure session...</p>
          </div>
        ) : !authenticated ? (
          <form className="admin-card admin-login" onSubmit={login}>
            <h2>Admin login</h2>
            <p className="admin-muted">
              Secure admin login. Session is stored in an HttpOnly cookie.
            </p>

            <div className="admin-field">
              <label>Username</label>
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </div>

            <div className="admin-field">
              <label>Password</label>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            <button className="admin-primary" disabled={busy}>
              {busy ? "Signing in..." : "Sign in"}
            </button>

            {error && <div className="admin-error">{error}</div>}
          </form>
        ) : (
          <div className="admin-card">
            {!status ? (
              <p className="admin-muted">
                {busy ? "Loading control panel..." : "Status unavailable."}
              </p>
            ) : (
              <>
                <div className="admin-grid">
                  <div className="admin-stat">
                    <small>System</small>
                    <strong className="admin-status-ok">ONLINE</strong>
                  </div>

                  <div className="admin-stat">
                    <small>Paid AI</small>
                    <strong
                      className={
                        status.paid_ai_enabled
                          ? "admin-status-danger"
                          : "admin-status-ok"
                      }
                    >
                      {status.paid_ai_enabled ? "ENABLED" : "DISABLED"}
                    </strong>
                  </div>

                  <div className="admin-stat">
                    <small>Requests today</small>
                    <strong>
                      {status.daily_requests} / {status.daily_limit}
                    </strong>
                  </div>

                  <div className="admin-stat">
                    <small>Model</small>
                    <strong>{status.model}</strong>
                  </div>
                </div>

                <div className="admin-controls">
                  <div className="admin-control">
                    <div>
                      <h3>Demo Mode</h3>
                      <p>
                        ON = Smart Demo, zero OpenAI cost. OFF = real AI verification.
                      </p>
                    </div>

                    <div className="admin-switch">
                      <button
                        className={
                          status.demo_mode ? "admin-primary" : "admin-secondary"
                        }
                        disabled={busy || status.kill_switch}
                        onClick={() =>
                          updateSettings({
                            demo_mode: !status.demo_mode,
                          })
                        }
                      >
                        {status.demo_mode ? "ON" : "OFF"}
                      </button>
                    </div>
                  </div>

                  <div className="admin-control">
                    <div>
                      <h3>Deep Audit</h3>
                      <p>
                        Optional second verification pass. It can increase API usage.
                      </p>
                    </div>

                    <div className="admin-switch">
                      <button
                        className={
                          status.deep_audit ? "admin-primary" : "admin-secondary"
                        }
                        disabled={busy || status.demo_mode || status.kill_switch}
                        onClick={() =>
                          updateSettings({
                            deep_audit: !status.deep_audit,
                          })
                        }
                      >
                        {status.deep_audit ? "ON" : "OFF"}
                      </button>
                    </div>
                  </div>

                  <div className="admin-control">
                    <div>
                      <h3>Emergency Kill Switch</h3>
                      <p>
                        Immediately forces zero-cost Demo Mode and disables Deep Audit.
                      </p>
                    </div>

                    <div className="admin-switch">
                      <button
                        className={
                          status.kill_switch ? "admin-danger" : "admin-secondary"
                        }
                        disabled={busy}
                        onClick={() =>
                          updateSettings({
                            kill_switch: !status.kill_switch,
                          })
                        }
                      >
                        {status.kill_switch ? "ACTIVE" : "OFF"}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="admin-note">
                  <strong>Protection:</strong> {status.burst_limit} request burst limit
                  per {status.burst_window_seconds} seconds, {status.per_ip_limit} real AI
                  requests per IP every {Math.round(status.per_ip_window_seconds / 60)} minutes,
                  with a global limit of {status.daily_limit} per day.
                  <br />
                  <br />
                  Password hashing:{" "}
                  <strong>
                    {status.password_hash_enabled ? "ENABLED" : "MIGRATION NEEDED"}
                  </strong>
                  <br />
                  <br />
                  {status.runtime_note}
                </div>

                {error && <div className="admin-error">{error}</div>}

                <div className="admin-actions">
                  <button
                    className="admin-secondary"
                    disabled={busy}
                    onClick={() => loadStatus()}
                  >
                    Refresh status
                  </button>

                  <button
                    className="admin-secondary"
                    onClick={logout}
                  >
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function ScholarProofApp() {
  const [theme, setTheme] = useState(
    localStorage.getItem("scholarproof-theme") || "light"
  );

  const [language, setLanguage] = useState(
    localStorage.getItem("scholarproof-language") || "en"
  );

  const [mode, setMode] = useState("text");

  const [text, setText] = useState("");
  const [url, setUrl] = useState("");

  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [imageDataUrl, setImageDataUrl] = useState("");

  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const [copied, setCopied] = useState(false);

  const [history, setHistory] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem("scholarproof-history") || "[]"
      );
    } catch {
      return [];
    }
  });

  const t = translations[language];

  const loadingMessages = useMemo(
    () => [
      "Extracting important claims...",
      "Identifying the institution...",
      "Checking official sources...",
      "Reviewing security signals...",
      "Preparing evidence...",
    ],
    []
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("scholarproof-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("scholarproof-language", language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem(
      "scholarproof-history",
      JSON.stringify(history.slice(0, 8))
    );
  }, [history]);

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0);
      return;
    }

    const interval = setInterval(() => {
      setLoadingStep((current) =>
        Math.min(current + 1, loadingMessages.length - 1)
      );
    }, 850);

    return () => clearInterval(interval);
  }, [loading, loadingMessages.length]);

  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setResult(null);
  }

  function useExample(example) {
    setMode("text");
    setText(example);
    setResult(null);

    document
      .getElementById("verify")
      ?.scrollIntoView({ behavior: "smooth" });
  }

  function handleImageChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please upload a valid image.");
      return;
    }

    if (file.size > 7 * 1024 * 1024) {
      setError("Image must be smaller than 7 MB.");
      return;
    }

    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setError("");

    const reader = new FileReader();

    reader.onload = () => {
      setImageDataUrl(reader.result);
    };

    reader.readAsDataURL(file);
  }

  function removeImage() {
    setImageFile(null);
    setImagePreview("");
    setImageDataUrl("");
  }

  function validate() {
    if (mode === "text" && text.trim().length < 10) {
      return "Please provide more information.";
    }

    if (mode === "url" && !url.trim()) {
      return "Please enter a URL.";
    }

    if (mode === "image" && !imageDataUrl) {
      return "Please upload a screenshot.";
    }

    return "";
  }

  async function verifyScholarship() {
    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          mode,
          text: mode === "text" ? text : null,
          url: mode === "url" ? url : null,
          image_data_url:
            mode === "image" ? imageDataUrl : null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed.");
      }

      setResult(data);

      const historyItem = {
        id: Date.now(),
        mode,
        title:
          data.report.institution ||
          (mode === "url"
            ? url
            : mode === "image"
              ? imageFile?.name
              : text.slice(0, 55)),
        risk: data.report.risk,
        verdict: data.report.verdict,
        date: new Date().toISOString(),
      };

      setHistory((current) => [
        historyItem,
        ...current,
      ].slice(0, 8));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyReport() {
    if (!result?.report) return;

    const report = result.report;

    const output = `
ScholarProof Report

Institution:
${report.institution}

Verdict:
${report.verdict}

Summary:
${report.summary}

Risk:
${report.risk.toUpperCase()}

Claims:
${report.claims
  .map(
    (claim) =>
      `- ${claim.claim}
  ${claim.status.toUpperCase()}
  ${claim.evidence}`
  )
  .join("\n\n")}
`;

    await navigator.clipboard.writeText(output);

    setCopied(true);

    setTimeout(() => {
      setCopied(false);
    }, 1600);
  }

  function resetVerification() {
    setText("");
    setUrl("");
    removeImage();

    setResult(null);
    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  const report = result?.report;

  const displaySources = useMemo(
    () => uniqueSources(report?.sources || []),
    [report?.sources]
  );

  return (
    <div className="app">
      <div className="background-orb orb-one" />
      <div className="background-orb orb-two" />

      <header className="navbar">
        <a className="brand" href="/">
          <div className="brand-icon">
            SP
          </div>

          <div>
            <strong>ScholarProof</strong>
            <small>Evidence before trust</small>
          </div>
        </a>

        <nav>
          <a href="#verify">{t.verify}</a>
          <a href="#how">{t.how}</a>
          <a href="#history">{t.history}</a>
        </nav>

        <div className="nav-actions">
          <div className="demo-badge">
            <span />
            {t.demo}
          </div>

          <select
            className="language-select"
            value={language}
            onChange={(event) =>
              setLanguage(event.target.value)
            }
          >
            <option value="en">EN</option>
            <option value="uz">UZ</option>
            <option value="ru">RU</option>
          </select>

          <button
            className="theme-button"
            onClick={() =>
              setTheme(theme === "dark" ? "light" : "dark")
            }
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-badge">
            <span className="live-dot" />
            {t.badge}
          </div>

          <h1>
            {t.title1}
            <span> {t.title2}</span>
          </h1>

          <p className="hero-subtitle">
            {t.subtitle}
          </p>

          <div className="hero-points">
            <span>✓ Official sources</span>
            <span>✓ Security analysis</span>
            <span>✓ Multilingual</span>
            <span>✓ Evidence-based</span>
          </div>

          <div className="verify-card" id="verify">
            <div className="card-glow" />

            <div className="mode-tabs">
              <button
                className={mode === "text" ? "active" : ""}
                onClick={() => switchMode("text")}
              >
                ✦ {t.text}
              </button>

              <button
                className={mode === "url" ? "active" : ""}
                onClick={() => switchMode("url")}
              >
                ↗ {t.url}
              </button>

              <button
                className={mode === "image" ? "active" : ""}
                onClick={() => switchMode("image")}
              >
                ▧ {t.screenshot}
              </button>
            </div>

            {mode === "text" && (
              <div className="input-area">
                <textarea
                  value={text}
                  maxLength={15000}
                  onChange={(event) =>
                    setText(event.target.value)
                  }
                  placeholder={t.textarea}
                />

                <div className="input-footer">
                  <span>
                    🌐 Any language
                  </span>

                  <span>
                    {text.length.toLocaleString()} / 15,000
                  </span>
                </div>
              </div>
            )}

            {mode === "url" && (
              <div className="url-area">
                <div className="url-icon">
                  ↗
                </div>

                <input
                  value={url}
                  onChange={(event) =>
                    setUrl(event.target.value)
                  }
                  placeholder={t.urlPlaceholder}
                />
              </div>
            )}

            {mode === "image" && (
              <>
                {!imagePreview ? (
                  <>
                    <input
                      id="upload"
                      type="file"
                      hidden
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handleImageChange}
                    />

                    <label
                      htmlFor="upload"
                      className="upload-zone"
                    >
                      <div className="upload-icon">
                        ↑
                      </div>

                      <strong>
                        {t.upload}
                      </strong>

                      <p>
                        {t.uploadHelp}
                      </p>

                      <small>
                        PNG · JPG · WEBP · max 7 MB
                      </small>
                    </label>
                  </>
                ) : (
                  <div className="image-preview">
                    <img
                      src={imagePreview}
                      alt="preview"
                    />

                    <div>
                      <span>
                        {imageFile?.name}
                      </span>

                      <button onClick={removeImage}>
                        Remove
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {error && (
              <div className="error">
                ⚠ {error}
              </div>
            )}

            <button
              className="verify-main"
              onClick={verifyScholarship}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="small-spinner" />
                  {t.verifying}
                </>
              ) : (
                <>
                  ✦ {t.verifyButton}
                  <span>→</span>
                </>
              )}
            </button>

            <div className="demo-info">
              🔒 {t.demoText}
            </div>
          </div>

          <div className="quick-examples">
            <span>Try an example:</span>

            <button
              onClick={() =>
                useExample(
                  "KAIST gives every international student a full scholarship and applications must be submitted through Telegram."
                )
              }
            >
              KAIST scholarship
            </button>

            <button
              onClick={() =>
                useExample(
                  "The University of Toronto guarantees a full scholarship to every international student with IELTS 6.0."
                )
              }
            >
              Toronto scholarship
            </button>
          </div>
        </section>

        {loading && (
          <section className="loading-card">
            <div className="loader-circle">
              <div />
            </div>

            <div className="loading-content">
              <span>{t.deep}</span>

              <h2>
                {loadingMessages[loadingStep]}
              </h2>

              <div className="progress">
                <div
                  style={{
                    width: `${
                      ((loadingStep + 1) /
                        loadingMessages.length) *
                      100
                    }%`,
                  }}
                />
              </div>

              <p>{t.accuracy}</p>
            </div>
          </section>
        )}

        {report && !loading && (
          <section className="report-section">
            <div className="report-top">
              <div>
                <span>{t.report}</span>

                <h2>
                  {report.institution ||
                    "Verification"}
                </h2>

                <p>{report.summary}</p>
              </div>

              <div
                className={`risk-pill risk-${report.risk}`}
              >
                {report.risk === "high" && "🚨 "}
                {report.risk.toUpperCase()} RISK
              </div>
            </div>

            {result.demo && (
              <div className="demo-notice">
                <strong>
                  {t.demo}
                </strong>

                <span>
                  {t.demoText}
                </span>
              </div>
            )}

            <div className="overall-card">
              <span>
                {t.verdict}
              </span>

              <h3>
                {report.verdict}
              </h3>
            </div>

            <div className="section-heading">
              <span>
                {t.claims}
              </span>

              <h3>
                {report.claims.length} claims reviewed
              </h3>
            </div>

            <div className="claims-grid">
              {report.claims.map(
                (claim, index) => {
                  const status =
                    STATUS[claim.status] ||
                    STATUS.insufficient;

                  return (
                    <article
                      className={`claim ${status.className}`}
                      key={index}
                    >
                      <div className="claim-head">
                        <div className="status-icon">
                          {status.icon}
                        </div>

                        <span>
                          {status.label}
                        </span>
                      </div>

                      <h3>
                        {claim.claim}
                      </h3>

                      <p>
                        {claim.evidence}
                      </p>

                      <div className="evidence">
                        <small>
                          {t.evidence}
                        </small>

                        {claim.source_url ? (
                          <a
                            href={claim.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {claim.source_title ||
                              sourceDomain(claim.source_url) ||
                              t.official} ↗
                          </a>
                        ) : (
                          <small>
                            {t.sourceUnavailable}
                          </small>
                        )}
                      </div>
                    </article>
                  );
                }
              )}
            </div>

            <div className="report-grid">
              <div className="security-card">
                <span>
                  {t.security}
                </span>

                <h3>
                  Security signals
                </h3>

                {report.security_signals.map(
                  (signal, index) => (
                    <div
                      className="security-item"
                      key={index}
                    >
                      <div
                        className={`signal signal-${signal.severity}`}
                      />

                      <div>
                        <strong>
                          {signal.title}
                        </strong>

                        <p>
                          {signal.detail}
                        </p>
                      </div>
                    </div>
                  )
                )}
              </div>

              <div className="next-card">
                <span>
                  {t.next}
                </span>

                <h3>
                  Safer next steps
                </h3>

                {report.next_steps.map(
                  (step, index) => (
                    <div
                      className="next-step"
                      key={index}
                    >
                      <div>
                        {index + 1}
                      </div>

                      <p>
                        {step}
                      </p>
                    </div>
                  )
                )}
              </div>
            </div>

            <div className="sources">
              <span>
                {t.sources}
              </span>

              {displaySources.length > 0 ? (
                displaySources.map(
                  (source) => (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      key={sourceKey(source.url)}
                    >
                      <div>
                        <strong>
                          {source.title ||
                            sourceDomain(source.url) ||
                            t.official}
                        </strong>

                        <small>
                          {source.official
                            ? `✓ ${t.official}`
                            : t.supporting}
                        </small>

                        <small>
                          {sourceDomain(source.url)}
                        </small>

                        <small>
                          {t.openSource} ↗
                        </small>
                      </div>

                      <span>↗</span>
                    </a>
                  )
                )
              ) : (
                <div className="empty">
                  <p>{t.sourceUnavailable}</p>
                </div>
              )}
            </div>

            <div className="report-actions">
              <button onClick={copyReport}>
                {copied ? "✓ " + t.copied : "⌘ " + t.copy}
              </button>

              <button
                className="primary"
                onClick={resetVerification}
              >
                {t.another}
              </button>
            </div>
          </section>
        )}

        <section className="how-section" id="how">
          <div className="section-title">
            <span>
              {t.how}
            </span>

            <h2>
              {t.howTitle}
            </h2>
          </div>

          <div className="steps">
            <article>
              <div>01</div>
              <h3>{t.step1}</h3>
              <p>{t.step1d}</p>
            </article>

            <article>
              <div>02</div>
              <h3>{t.step2}</h3>
              <p>{t.step2d}</p>
            </article>

            <article>
              <div>03</div>
              <h3>{t.step3}</h3>
              <p>{t.step3d}</p>
            </article>

            <article>
              <div>04</div>
              <h3>{t.step4}</h3>
              <p>{t.step4d}</p>
            </article>
          </div>
        </section>

        <section className="history-section" id="history">
          <div className="history-head">
            <div>
              <span>
                HISTORY
              </span>

              <h2>
                {t.recent}
              </h2>
            </div>

            {history.length > 0 && (
              <button
                onClick={() =>
                  setHistory([])
                }
              >
                {t.clear}
              </button>
            )}
          </div>

          {history.length === 0 ? (
            <div className="empty">
              ◌
              <p>{t.noHistory}</p>
            </div>
          ) : (
            <div className="history-list">
              {history.map((item) => (
                <div
                  className="history-item"
                  key={item.id}
                >
                  <div className="history-type">
                    {item.mode === "text"
                      ? "T"
                      : item.mode === "url"
                        ? "↗"
                        : "▧"}
                  </div>

                  <div className="history-info">
                    <strong>
                      {item.title}
                    </strong>

                    <small>
                      {new Date(
                        item.date
                      ).toLocaleString()}
                    </small>
                  </div>

                  <span
                    className={`mini-risk risk-${item.risk}`}
                  >
                    {item.risk}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer>
        <div className="brand">
          <div className="brand-icon">
            SP
          </div>

          <div>
            <strong>ScholarProof</strong>
            <small>Evidence before trust</small>
          </div>
        </div>

        <p>
          AI can make mistakes. Important decisions should
          always be confirmed with original official sources.
        </p>
      </footer>
    </div>
  );
}

function App() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  if (path === "/admin") {
    return <AdminPanel />;
  }

  return <ScholarProofApp />;
}

export default App;