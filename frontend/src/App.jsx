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

function App() {
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

                        <a
                          href={claim.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {claim.source_title} ↗
                        </a>
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

              {report.sources.map(
                (source, index) => (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    key={index}
                  >
                    <div>
                      <strong>
                        {source.title}
                      </strong>

                      <small>
                        {source.official
                          ? t.official
                          : "Supporting source"}
                      </small>
                    </div>

                    <span>↗</span>
                  </a>
                )
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

export default App;