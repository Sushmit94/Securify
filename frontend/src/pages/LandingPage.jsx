import { useNavigate } from "react-router-dom";
import "./LandingPage.css";

const CODE_LINES = [
    { text: "def login(request):", vuln: false },
    { text: '    username = request.form["username"]', vuln: false },
    { text: '    password = request.form["password"]', vuln: false },
    { text: "", vuln: false },
    { text: '    query = "SELECT * FROM users WHERE username = \'" + username + "\'"', vuln: true },
    { text: "    cursor.execute(query)", vuln: false },
    { text: "    user = cursor.fetchone()", vuln: false },
    { text: "", vuln: false },
    { text: "    if user and check_password(user.hash, password):", vuln: false },
    { text: "        return create_session(user)", vuln: false },
    { text: "    return unauthorized()", vuln: false },
];

const LAYERS = [
    {
        label: "Layer 1",
        name: "Static Analysis",
        speed: "Fast · deterministic",
        copy:
            "Semgrep and Bandit scan against language-specific rulesets and return pattern-based findings with a rule ID, file, line, and CWE reference — no ambiguity, no waiting.",
    },
    {
        label: "Layer 2",
        name: "ML Classifier",
        speed: "Learned · Tier 1 languages",
        copy:
            "A fine-tuned CodeBERT/GraphCodeBERT model scores each function 0–1 for vulnerability likelihood, catching patterns no rule was ever written for.",
    },
    {
        label: "Layer 3",
        name: "LLM Reasoning",
        speed: "Contextual · every language",
        copy:
            "An LLM reviews the code alongside what the first two layers found, confirms or rejects each one, and writes the plain-English explanation and fix.",
    },
];

const TIERS = [
    {
        tier: "Tier 1",
        heading: "Deep coverage",
        languages: "Python, Java, C/C++",
        layers: "Static Analysis + ML Classifier + LLM Reasoning",
    },
    {
        tier: "Tier 2",
        heading: "Broad coverage",
        languages: "JS/TS, Go, PHP, Ruby, C#, Kotlin, Rust",
        layers: "Static Analysis + LLM Reasoning",
    },
    {
        tier: "Tier 3",
        heading: "Fallback coverage",
        languages: "Anything else",
        layers: "LLM Reasoning only",
    },
];

export default function Landing() {
    const navigate = useNavigate();
    const onLaunch = () => navigate("/dashboard");

    return (
        <div className="sf-page">
            <header className="sf-nav">
                <div className="sf-nav-inner">
                    <a className="sf-logo" href="#top">
                        Securify
                    </a>
                    <nav className="sf-nav-links">
                        <a href="#layers">Layers</a>
                        <a href="#coverage">Coverage</a>
                    </nav>
                    <button className="sf-btn sf-btn-primary sf-btn-small" onClick={onLaunch}>
                        Open dashboard
                    </button>
                </div>
            </header>

            <main>
                <section className="sf-hero" id="top">
                    <div className="sf-hero-copy">
                        <p className="sf-eyebrow">Static analysis · ML classifier · LLM reasoning</p>
                        <h1>
                            Three ways to catch <span className="sf-underline">what one misses.</span>
                        </h1>
                        <p className="sf-hero-sub">
                            Securify runs every file through a deterministic rule engine, a fine-tuned
                            classifier, and an LLM that argues with both — so what reaches you is a finding,
                            not a guess.
                        </p>
                        <div className="sf-hero-actions">
                            <button className="sf-btn sf-btn-primary" onClick={onLaunch}>
                                Launch scanner
                            </button>
                            <a className="sf-btn sf-btn-ghost" href="#layers">
                                See how it works
                            </a>
                        </div>
                    </div>

                    <div className="sf-hero-visual" aria-hidden="true">
                        <div className="sf-code-panel">
                            <div className="sf-code-titlebar">
                                <span className="sf-code-dot" />
                                <span className="sf-code-dot" />
                                <span className="sf-code-dot" />
                                <span className="sf-code-filename">app/routes/login.py</span>
                            </div>
                            <div className="sf-code-body">
                                <div className="sf-scanline" />
                                {CODE_LINES.map((line, i) => (
                                    <div className="sf-code-line" key={i}>
                                        <span className="sf-code-lineno">{i + 1}</span>
                                        <span className="sf-code-text">{line.text || "\u00A0"}</span>
                                        {line.vuln && (
                                            <span className="sf-badge-row">
                                                <span className="sf-badge sf-badge-static">Static</span>
                                                <span className="sf-badge sf-badge-ml">ML 0.93</span>
                                                <span className="sf-badge sf-badge-llm">CWE-89</span>
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>

                <section className="sf-section" id="layers">
                    <p className="sf-eyebrow sf-eyebrow-center">Three lenses, one verdict</p>
                    <h2 className="sf-section-title">Every finding earns its way to you.</h2>
                    <div className="sf-layers-grid">
                        {LAYERS.map((layer) => (
                            <div className="sf-layer-card" key={layer.name}>
                                <p className="sf-layer-label">{layer.label}</p>
                                <h3>{layer.name}</h3>
                                <p className="sf-layer-speed">{layer.speed}</p>
                                <p className="sf-layer-copy">{layer.copy}</p>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="sf-section sf-section-alt" id="coverage">
                    <p className="sf-eyebrow sf-eyebrow-center">Language coverage</p>
                    <h2 className="sf-section-title">
                        Coverage is tiered on purpose — and we tell you which tier you got.
                    </h2>
                    <p className="sf-section-sub">
                        Labeled vulnerability data only exists for a handful of languages, so Securify never
                        claims an ML-based confidence score it can't back up.
                    </p>
                    <div className="sf-tier-table">
                        {TIERS.map((t) => (
                            <div className="sf-tier-row" key={t.tier}>
                                <div className="sf-tier-name">
                                    <span className="sf-tier-badge">{t.tier}</span>
                                    <span className="sf-tier-heading">{t.heading}</span>
                                </div>
                                <div className="sf-tier-languages">{t.languages}</div>
                                <div className="sf-tier-layers">{t.layers}</div>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="sf-cta">
                    <h2>Ready to see what's hiding in your code?</h2>
                    <p>Upload a file or point Securify at a repo — the first report takes under a minute.</p>
                    <button className="sf-btn sf-btn-primary" onClick={onLaunch}>
                        Run your first scan
                    </button>
                </section>
            </main>

            <footer className="sf-footer">
                <span>Securify</span>
                <span className="sf-footer-muted">Hybrid vulnerability detection</span>
            </footer>
        </div>
    );
}