import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Brain,
  Check,
  ChevronRight,
  CircleDollarSign,
  Database,
  Download,
  Gauge,
  LayoutDashboard,
  LineChart,
  Lock,
  LogOut,
  PieChart,
  RefreshCw,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Sparkles,
  Moon,
  Sun,
  Target,
  TrendingUp,
  User,
  WalletCards,
} from "lucide-react";
import "./styles.css";
import { BeaconIcon } from "./components/BeaconIcon";
import {
  addBrokerConnection,
  confirmPhoneVerificationCode,
  createEmailAccount,
  deleteBrokerConnection,
  ensureUserProfile,
  firebaseReady,
  sendPhoneVerificationCode,
  signInWithAnonymousTestUser,
  signInWithEmail,
  signOutOfFirebase,
  subscribeToBeaconData,
  updateUserSettings,
  upsertInvestmentPlan,
} from "./services/firebase";
import {
  demoAnalysisRun,
  demoBuyIdeas,
  demoFactorIc,
  demoHoldings,
  demoSignals,
  demoStrategyPlan,
} from "./services/demoData";
import { analyzePortfolio, analyzeSecurity, connectBrokerViaBackend, mapBackendAnalysis } from "./services/backend";

const nav = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "portfolio", label: "Portfolio", icon: PieChart },
  { id: "strategy", label: "Strategy", icon: Target },
  { id: "ideas", label: "Ideas", icon: Sparkles },
  { id: "research", label: "Research", icon: BarChart3 },
  { id: "sentiment", label: "Sentiment", icon: Brain },
  { id: "search", label: "Search", icon: Search },
  { id: "profile", label: "Profile", icon: User },
  { id: "connect", label: "Connect", icon: Lock },
];

const COMMON_SYMBOLS = [
  { ticker: "AAPL", name: "Apple" },
  { ticker: "MSFT", name: "Microsoft" },
  { ticker: "NVDA", name: "NVIDIA" },
  { ticker: "AMZN", name: "Amazon" },
  { ticker: "GOOGL", name: "Alphabet" },
  { ticker: "META", name: "Meta" },
  { ticker: "TSLA", name: "Tesla" },
  { ticker: "AMD", name: "Advanced Micro Devices" },
  { ticker: "AVGO", name: "Broadcom" },
  { ticker: "MU", name: "Micron" },
  { ticker: "COST", name: "Costco" },
  { ticker: "LLY", name: "Eli Lilly" },
  { ticker: "JPM", name: "JPMorgan Chase" },
  { ticker: "VTI", name: "Vanguard Total Stock Market ETF" },
  { ticker: "VOO", name: "Vanguard S&P 500 ETF" },
  { ticker: "SPY", name: "SPDR S&P 500 ETF" },
  { ticker: "QQQ", name: "Invesco QQQ" },
  { ticker: "FXAIX", name: "Fidelity 500 Index Fund" },
  { ticker: "SWPPX", name: "Schwab S&P 500 Index Fund" },
  { ticker: "VTSAX", name: "Vanguard Total Stock Market Index Fund" },
];

const PANEL_TOOLTIPS = {
  "Total Portfolio Value": "Current estimated market value across the loaded holdings.",
  Positions: "Number of positions in the current portfolio snapshot.",
  Concentrated: "Count of holdings above the portfolio concentration threshold.",
  "Cash proxy": "Estimated uninvested account value inferred from equity minus holdings value.",
  "Risk style": "Default investment posture used to generate staged allocation guidance.",
  "What To Review Today": "Highest-priority actions from the portfolio signal engine.",
  "Personal Portfolio Trend": "Estimated account value path based on current holdings and unrealized gains.",
  "Risk Snapshot": "Position weights that drive concentration and diversification risk.",
  "Top Buy Ideas": "Highest-ranked candidates from the backend factor and sentiment model.",
  "Current Holdings": "Loaded portfolio positions with action, weight, value, gain, and model score.",
  "Position Size": "Portfolio allocation by ticker.",
  "Unrealized Gain": "Gain or loss by position, scaled against the largest absolute move.",
  "Scenario Impact": "Estimated account impact from large moves in the most concentrated holding.",
  "Tax Impact Estimator": "Simple estimate of taxable gains and reserve for a partial trim.",
  "Exit Strategy & Tax Plan": "Personalized trim and tax planning guidance using current holdings and target allocations.",
  "Target Allocation By Ticker": "Suggested deployment split for new cash.",
  "Capital Allocation": "Cash amount available for staged deployment.",
  "Risk Style": "Controls how quickly the plan deploys cash and how strict exits should be.",
  "Factor Snapshot": "Momentum, volatility, drawdown, valuation, and target metrics for the searched security.",
  "Why It Scored This Way": "Plain-English reasons behind the security score.",
  "Recent Headlines": "Recent market/news context returned by the backend.",
};

function App() {
  const [appView, setAppView] = useState(() => readAppRoute());
  const [publicPage, setPublicPage] = useState("home");
  const [theme, setTheme] = useState(() => sessionStorage.getItem("beacon_theme") || "dark");
  const [active, setActive] = useState("dashboard");
  const [cash, setCash] = useState(12000);
  const [riskStyle, setRiskStyle] = useState("Balanced");
  const [includeOwned, setIncludeOwned] = useState(false);
  const [backendData, setBackendData] = useState(null);
  const [brokerCredentials, setBrokerCredentials] = useState(() => readSessionBrokerCredentials());
  const [topbarSearchQuery, setTopbarSearchQuery] = useState("");
  const [securityQuery, setSecurityQuery] = useState("");
  const [securityResult, setSecurityResult] = useState(null);
  const [securityLoading, setSecurityLoading] = useState(false);
  const [analysisOptions, setAnalysisOptions] = useState({
    useRobinhood: false,
    useOpenAi: false,
    extraTickersText: "COST,LLY,JPM,VTI",
    limit: 5,
    includeOwnedIdeas: false,
  });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [authRefreshKey, setAuthRefreshKey] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [firebaseState, setFirebaseState] = useState({
    user: null,
    profile: null,
    brokerConnections: [],
    holdings: [],
    latestRun: null,
    actions: [],
    buyIdeas: [],
    factorIc: [],
    signals: [],
    plan: null,
    loading: firebaseReady,
    error: null,
    authDisabled: false,
  });
  const [toast, setToast] = useState("");

  function navigateTo(view) {
    const path = view === "home" ? "/" : `/${view}`;
    window.history.pushState({}, "", path);
    setAppView(view);
  }

  useEffect(() => {
    const syncRoute = () => setAppView(readAppRoute());
    window.addEventListener("popstate", syncRoute);
    return () => window.removeEventListener("popstate", syncRoute);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    sessionStorage.setItem("beacon_theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!firebaseReady) return;
    let unsub = () => {};
    ensureUserProfile()
      .then(({ user }) => {
        if (!user) {
          setFirebaseState((current) => ({ ...current, user: null, loading: false, error: null }));
          return;
        }
        unsub = subscribeToBeaconData(user.uid, setFirebaseState);
      })
      .catch((error) => {
        setFirebaseState((current) => ({
          ...current,
          loading: false,
          authDisabled: error.code === "auth/configuration-not-found",
          error: firebaseErrorMessage(error),
        }));
      });
    return () => unsub();
  }, [authRefreshKey]);

  const data = useMemo(() => {
    if (backendData) return backendData;
    const holdings = (firebaseState.holdings || []).length ? firebaseState.holdings : demoHoldings;
    const latestRun = firebaseState.latestRun || demoAnalysisRun;
    const actions = (firebaseState.actions || []).length ? firebaseState.actions : demoSignals.slice(0, 5);
    const buyIdeas = (firebaseState.buyIdeas || []).length ? firebaseState.buyIdeas : demoBuyIdeas;
    const factorIc = (firebaseState.factorIc || []).length ? firebaseState.factorIc : demoFactorIc;
    const signals = (firebaseState.signals || []).length ? firebaseState.signals : demoSignals;
    const plan = firebaseState.plan || demoStrategyPlan;
    return { holdings, latestRun, actions, buyIdeas, factorIc, signals, plan };
  }, [backendData, firebaseState]);

  const summary = useMemo(() => buildSummary(data.holdings, data.latestRun), [data]);
  const generatedPlan = useMemo(
    () => buildPlan(cash, riskStyle, includeOwned, data.buyIdeas, data.holdings),
    [cash, riskStyle, includeOwned, data.buyIdeas, data.holdings],
  );

  async function handleAnalyze() {
    setIsAnalyzing(true);
    setToast("Running backend analysis. This can take a bit because it fetches market data.");
    try {
      const activeBrokerCredentials = brokerCredentials || readSessionBrokerCredentials();
      if (!activeBrokerCredentials) {
        setToast("Connect Robinhood first. Portfolio analysis now uses linked session credentials, not credentials.md.");
        return;
      }
      const result = await analyzePortfolio({
        ...analysisOptions,
        useRobinhood: true,
        brokerCredentials: activeBrokerCredentials,
      });
      setBackendData(mapBackendAnalysis(result));
      setToast(`Backend analysis complete in ${result.elapsedSeconds}s.`);
    } catch (error) {
      setToast(`Backend analysis failed: ${error.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleSavePlan() {
    if (!firebaseState.user) {
      setToast(firebaseState.error || "Sign in before saving a plan.");
      return;
    }
    await upsertInvestmentPlan(firebaseState.user.uid, {
      cashAmount: cash,
      riskStyle,
      deploymentMode: generatedPlan.mode,
      schedule: generatedPlan.schedule,
      allocations: generatedPlan.allocations,
    });
    setToast("Investment plan saved to Firestore.");
  }

  async function handleConnectBroker(options) {
    try {
      const result = await connectBrokerViaBackend(options);
      if (firebaseState.user) {
        await addBrokerConnection(firebaseState.user.uid, result);
      }
      if (result.status === "connected" && options.brokerCredentials) {
        setBrokerCredentials(options.brokerCredentials);
        sessionStorage.setItem("beacon_robinhood_credentials", JSON.stringify(options.brokerCredentials));
        setAnalysisOptions((current) => ({ ...current, useRobinhood: true }));
      }
      setToast(result.message || `${result.broker || options.broker} broker metadata saved.`);
    } catch (error) {
      setToast(`Broker connection failed: ${error.message}`);
      throw error;
    }
  }

  async function handleDeleteBrokerConnection(connection) {
    if (!firebaseState.user || !connection?.id) {
      setToast("Sign in before deleting a broker connection.");
      return;
    }
    await deleteBrokerConnection(firebaseState.user.uid, connection.id);
    if (connection.broker === "robinhood") {
      setBrokerCredentials(null);
      sessionStorage.removeItem("beacon_robinhood_credentials");
      setAnalysisOptions((current) => ({ ...current, useRobinhood: false }));
    }
    setToast(`${connection.nickname || connection.broker} connection deleted.`);
  }

  async function handleLogout() {
    await signOutOfFirebase();
    setBrokerCredentials(null);
    setBackendData(null);
    setFirebaseState((current) => ({
      ...current,
      user: null,
      profile: null,
      brokerConnections: [],
      holdings: [],
      latestRun: null,
      actions: [],
      buyIdeas: [],
      factorIc: [],
      signals: [],
      plan: null,
    }));
    sessionStorage.removeItem("beacon_robinhood_credentials");
    navigateTo("login");
    refreshAuth();
  }

  function refreshAuth() {
    setAuthRefreshKey((key) => key + 1);
  }

  async function handleSaveSettings(settings) {
    if (!firebaseState.user) {
      setToast(firebaseState.error || "Sign in before saving settings.");
      return;
    }
    await updateUserSettings(firebaseState.user.uid, settings);
    setToast("Settings saved.");
    setShowSettings(false);
  }

  async function handleSecuritySearch(queryText = securityQuery) {
    const ticker = queryText.trim().toUpperCase();
    if (!ticker) return;
    setSecurityQuery(ticker);
    setActive("search");
    setSecurityLoading(true);
    setToast(`Analyzing ${ticker}.`);
    try {
      const result = await analyzeSecurity({
        ticker,
        brokerCredentials: brokerCredentials || readSessionBrokerCredentials(),
      });
      setSecurityResult(result);
      setToast(`${ticker} analysis loaded.`);
    } catch (error) {
      setToast(`Search failed: ${error.message}`);
    } finally {
      setSecurityLoading(false);
    }
  }

  const notifications = useMemo(
    () => buildNotifications(data, summary, firebaseState, backendData),
    [data, summary, firebaseState, backendData],
  );
  const searchSuggestions = useMemo(() => buildSearchSuggestions(data), [data]);

  return (
    <div className="app-shell">
      {appView === "home" && (
        <PublicHome
          onSignIn={() => navigateTo("login")}
          onGetStarted={() => navigateTo("login")}
          onDemo={() => navigateTo("dashboard")}
          onDashboard={() => navigateTo("dashboard")}
          user={firebaseState.user}
          page={publicPage}
          setPage={setPublicPage}
        />
      )}
      {appView === "login" && (
        <LoginPage
          firebaseState={firebaseState}
          refreshAuth={refreshAuth}
          onBack={() => navigateTo("home")}
          onContinue={() => navigateTo("dashboard")}
        />
      )}
      {appView === "dashboard" && (
        <>
      <Sidebar active={active} setActive={setActive} onHome={() => navigateTo("home")} />
      <div className="content-shell">
        <Topbar
          profile={firebaseState.profile}
          firebaseState={firebaseState}
          notifications={notifications}
          onOpenNotifications={() => setShowNotifications(true)}
          onOpenSettings={() => setShowSettings(true)}
          searchQuery={topbarSearchQuery}
          onSearchQuery={setTopbarSearchQuery}
          onSearch={handleSecuritySearch}
          suggestions={searchSuggestions}
          theme={theme}
          onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          onLogout={handleLogout}
        />
        <main className="page-frame">
          {active === "dashboard" && (
            <Dashboard
              data={data}
              summary={summary}
              setActive={setActive}
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
            />
          )}
          {active === "portfolio" && <Portfolio data={data} summary={summary} />}
          {active === "strategy" && (
            <Strategy
              cash={cash}
              setCash={setCash}
              riskStyle={riskStyle}
              setRiskStyle={setRiskStyle}
              includeOwned={includeOwned}
              setIncludeOwned={setIncludeOwned}
              plan={generatedPlan}
              holdings={data.holdings}
              onSave={handleSavePlan}
            />
          )}
          {active === "ideas" && <Ideas data={data} />}
          {active === "research" && <Research data={data} />}
          {active === "sentiment" && <MarketSentiment data={data} />}
          {active === "search" && (
            <SecuritySearch
              query={securityQuery}
              setQuery={setSecurityQuery}
              result={securityResult}
              loading={securityLoading}
              onSearch={handleSecuritySearch}
              suggestions={searchSuggestions}
            />
          )}
          {active === "profile" && (
            <ProfileConnections profile={firebaseState.profile} connections={firebaseState.brokerConnections} user={firebaseState.user} />
          )}
          {active === "connect" && (
            <Connect
              onConnect={handleConnectBroker}
              connections={firebaseState.brokerConnections}
              user={firebaseState.user}
              brokerCredentials={brokerCredentials}
              onDelete={handleDeleteBrokerConnection}
              exportData={{ userId: firebaseState.user?.uid, connections: firebaseState.brokerConnections }}
            />
          )}
        </main>
      </div>
      {showNotifications && (
        <NotificationsDrawer notifications={notifications} onClose={() => setShowNotifications(false)} />
      )}
      {showSettings && (
        <SettingsModal
          profile={firebaseState.profile}
          user={firebaseState.user}
          onClose={() => setShowSettings(false)}
          onSave={handleSaveSettings}
        />
      )}
      {toast && (
        <button className="toast" onClick={() => setToast("")}>
          <Check size={16} />
          {toast}
        </button>
      )}
      </>
      )}
    </div>
  );
}

function Sidebar({ active, setActive, onHome }) {
  return (
    <aside className="sidebar">
      <button className="brand brand-button" onClick={onHome} title="Go to Beacon home">
        <div className="brand-mark"><BeaconIcon size={30} variant="mixed" /></div>
        <div>
          <h1>Beacon</h1>
          <p>Private Wealth</p>
        </div>
      </button>
      <nav>
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${active === item.id ? "active" : ""}`}
              onClick={() => setActive(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <Shield size={18} />
        <span>Read-only portfolio intelligence. No trade execution.</span>
      </div>
    </aside>
  );
}

function PublicHome({ onSignIn, onGetStarted, onDemo, onDashboard, user, page, setPage }) {
  const signedInLabel = user?.email || user?.phoneNumber || (user ? "Signed in" : "");
  return (
    <div className="public-shell">
      <header className="public-nav">
        <button className="public-brand brand-button" onClick={() => setPage("home")}>
          <BeaconIcon size={32} variant="mixed" />
          <span>Beacon</span>
        </button>
        <nav>
          <button className={page === "platform" ? "selected" : ""} onClick={() => setPage("platform")}>Platform</button>
          <button className={page === "solutions" ? "selected" : ""} onClick={() => setPage("solutions")}>Solutions</button>
          <button className={page === "pricing" ? "selected" : ""} onClick={() => setPage("pricing")}>Pricing</button>
        </nav>
        <div>
          {user ? (
            <>
              <span className="public-signed-in">{signedInLabel}</span>
              <button className="public-primary" onClick={onDashboard}>Dashboard</button>
            </>
          ) : (
            <>
              <button className="public-link" onClick={onSignIn}>Sign In</button>
              <button className="public-primary" onClick={onGetStarted}>Get Started</button>
            </>
          )}
        </div>
      </header>
      <main className="public-main">
        {page === "home" && <HomePanel onGetStarted={onGetStarted} onDemo={onDemo} />}
        {page === "platform" && <PublicInfoPage title="Platform" subtitle="A private wealth operating system for portfolio decisions." items={[
          ["Connected holdings", "Link read-only brokerage sessions, normalize holdings, and keep risk views account-specific."],
          ["Signal engine", "Score holdings and candidates with momentum, volatility, drawdown, quality, sentiment, and concentration context."],
          ["Action workspace", "Turn research into staged buys, trim rules, tax-aware exits, and exportable review packs."],
        ]} />}
        {page === "solutions" && <PublicInfoPage title="Solutions" subtitle="Built for investors who want disciplined decisions without spreadsheet sprawl." items={[
          ["Concentrated portfolios", "Identify oversized positions and decide whether to hold, trim, or redirect cash into lower-correlation ideas."],
          ["New cash deployment", "Build staged allocation plans that adapt to risk style, existing exposures, and candidate quality."],
          ["Tax-aware exits", "Compare trim timing, lot priority, donation alternatives, and reinvestment tradeoffs before acting."],
        ]} />}
        {page === "pricing" && <PublicInfoPage title="Pricing" subtitle="Beacon is free while this local build is in development." items={[
          ["Free", "$0 for the current local dashboard, Firebase auth, broker metadata, and portfolio analytics UI."],
          ["Bring your own services", "Market data, broker access, Firebase, and optional AI/API keys remain under your own accounts."],
          ["No trade execution", "Beacon is read-only decision support, not a trading platform."],
        ]} />}
        <section className="public-features">
          <div>
            <Sparkles />
            <h3>Portfolio Signal Engine</h3>
            <p>Highlights concentration, weak signals, and buy candidates that deserve review.</p>
          </div>
          <div>
            <Shield />
            <h3>Read-only by design</h3>
            <p>Broker credentials are used for local validation and are never saved to Firebase.</p>
          </div>
          <div>
            <Brain />
            <h3>Plain-English context</h3>
            <p>Transforms factor data, news, and strategy state into concise decision support.</p>
          </div>
        </section>
      </main>
    </div>
  );
}

function HomePanel({ onGetStarted, onDemo }) {
  return (
    <section className="public-hero">
      <div className="public-pill">
        <span />
        Interactive portfolio intelligence
      </div>
      <h1>Turn connected brokerage data into <strong>clear actions.</strong></h1>
      <p>
        Beacon aggregates holdings, risk, alpha signals, market sentiment, tax-aware exits, and buy ideas into a disciplined
        private wealth dashboard, then translates the data into staged actions you can review before committing capital.
      </p>
      <div className="public-actions">
        <button className="public-primary large" onClick={onGetStarted}>
          Start Beacon <ChevronRight size={18} />
        </button>
        <button className="public-secondary large" onClick={onDemo}>View Demo Dashboard</button>
      </div>
      <div className="public-logo-row">
        {["robinhood.com", "fidelity.com", "vanguard.com", "schwab.com", "jpmorgan.com"].map((domain) => (
          <CompanyLogo key={domain} domain={domain} name={domain.split(".")[0]} />
        ))}
      </div>
      <LogoAttribution />
      <div className="public-preview">
        <div className="preview-top">
          <span />
          <span />
          <span />
        </div>
        <div className="preview-grid">
          <div>
            <Label>Total Portfolio Value</Label>
            <h2>$59,820</h2>
            <p className="positive">+$720 today</p>
          </div>
          <div>
            <Label>Risk Warning</Label>
            <h3>MU concentration at 31%</h3>
          </div>
          <div>
            <Label>Top Idea</Label>
            <h3>COST · Score 0.82</h3>
          </div>
        </div>
      </div>
    </section>
  );
}

function PublicInfoPage({ title, subtitle, items }) {
  return (
    <section className="public-info-page">
      <Label>Beacon</Label>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <div className="public-info-grid">
        {items.map(([heading, body]) => (
          <div key={heading}>
            <h3>{heading}</h3>
            <p>{body}</p>
          </div>
        ))}
      </div>
      <LogoAttribution />
    </section>
  );
}

function LoginPage({ firebaseState, refreshAuth, onBack, onContinue }) {
  return (
    <div className="login-shell">
      <button className="public-link login-back" onClick={onBack}>Back to Home</button>
      <div className="login-panel">
        <div>
          <Label>Beacon Login</Label>
          <h1>Sign in to continue</h1>
          <p>Use email, phone, or anonymous testing. After sign-in, continue to your dashboard.</p>
        </div>
        <AuthPanel firebaseState={firebaseState} refreshAuth={refreshAuth} onAuthSuccess={onContinue} />
        <button className="primary-button" onClick={onContinue} disabled={!firebaseState.user}>
          Continue to Dashboard
        </button>
      </div>
    </div>
  );
}

function Topbar({
  profile,
  firebaseState,
  notifications,
  onOpenNotifications,
  onOpenSettings,
  searchQuery,
  onSearchQuery,
  onSearch,
  suggestions,
  theme,
  onToggleTheme,
  onLogout,
}) {
  const firebaseLabel = firebaseState.error ? "Firebase setup needed" : firebaseState.user ? "Firestore live" : "Backend mode";
  const unread = notifications.filter((item) => item.tone !== "positive").length;
  return (
    <header className="topbar">
      <form
        className="search-box autocomplete-field"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch(searchQuery);
        }}
      >
        <Search size={16} />
        <input
          value={searchQuery}
          onChange={(event) => onSearchQuery(event.target.value)}
          placeholder="Analyze a stock, ETF, or mutual fund"
          list="topbar-symbol-suggestions"
        />
        <datalist id="topbar-symbol-suggestions">
          {suggestions.map((item) => (
            <option key={`${item.ticker}-${item.name}-topbar`} value={item.ticker}>
              {item.name}
            </option>
          ))}
        </datalist>
      </form>
      <div className="topbar-actions">
        <StatusPill tone={firebaseState.error ? "warning" : firebaseState.user ? "positive" : "neutral"}>
          <Database size={13} />
          {firebaseLabel}
        </StatusPill>
        <button className="icon-button badge-button" aria-label="Notifications" onClick={onOpenNotifications}>
          <Bell size={18} />
          {unread > 0 && <span>{unread}</span>}
        </button>
        <button className="icon-button" aria-label="Settings" onClick={onOpenSettings}>
          <Settings size={18} />
        </button>
        <button className="icon-button" aria-label="Toggle theme" onClick={onToggleTheme}>
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <div className="avatar">
          <User size={18} />
        </div>
        <span className="profile-name">{profile?.displayName || "Investor"}</span>
        <button className="icon-button" aria-label="Log out" onClick={onLogout} title="Log out">
          <LogOut size={17} />
        </button>
      </div>
    </header>
  );
}

function Dashboard({
  data,
  summary,
  setActive,
  onAnalyze,
  isAnalyzing,
}) {
  return (
    <div className="stack">
      <section className="hero-grid">
        <div className="hero-card card">
          <div>
            <Label>Total Portfolio Value</Label>
            <h2>{money(summary.totalValue)}</h2>
            <div className="metric-row positive">
              <ArrowUpRight size={18} />
              <span>{money(summary.todayChange)} ({pct(summary.todayChangePct)}) today</span>
            </div>
          </div>
          <div className={`risk-callout ${summary.topConcentration.weight > 0.25 ? "warn" : "ok"}`}>
            <AlertTriangle size={20} />
            <div>
              <strong>{summary.topConcentration.ticker} concentration</strong>
              <span>{pct(summary.topConcentration.weight)} of portfolio</span>
            </div>
          </div>
        </div>
        <div className="card ai-card">
          <div className="card-heading">
            <Brain size={20} />
            <h3>Advisor Intelligence</h3>
          </div>
          <p>{data.latestRun.plainEnglishSummary}</p>
          <button className="primary-button" onClick={() => setActive("strategy")}>
            Review Strategy <ChevronRight size={16} />
          </button>
        </div>
      </section>

      <section>
        <SectionHeader
          title="What To Review Today"
          action={isAnalyzing ? "Analyzing" : "Run analysis"}
          icon={RefreshCw}
          onAction={onAnalyze}
          actionDisabled={isAnalyzing}
        />
        <div className="review-grid">
          {data.actions.slice(0, 4).map((action) => (
            <ActionCard key={`${action.ticker}-${action.action}`} action={action} />
          ))}
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="card wide">
          <SectionHeader title="Personal Portfolio Trend" icon={LineChart} compact />
          <PortfolioTrendChart holdings={data.holdings} summary={summary} />
        </div>
        <div className="card">
          <SectionHeader title="Risk Snapshot" icon={Gauge} compact />
          <RiskBars holdings={data.holdings} />
        </div>
        <div className="card">
          <SectionHeader title="Top Buy Ideas" icon={Sparkles} compact />
          <IdeaList ideas={data.buyIdeas.slice(0, 4)} />
        </div>
        <div className="card wide">
          <SectionHeader title="Current Holdings" icon={WalletCards} compact />
          <HoldingsTable holdings={data.holdings.slice(0, 6)} />
        </div>
      </section>
    </div>
  );
}

function Portfolio({ data, summary }) {
  return (
    <div className="stack">
      <PageTitle title="Portfolio Risk Analysis" subtitle="Concentration, exposure, gain, and action mix across connected accounts." />
      <div className="metric-grid">
        <MetricCard label="Positions" value={summary.positions} icon={WalletCards} />
        <MetricCard label="Concentrated" value={summary.concentratedCount} icon={AlertTriangle} tone="warning" />
        <MetricCard label="Cash proxy" value={money(data.latestRun.accountEquity - data.latestRun.portfolioValue)} icon={CircleDollarSign} />
        <MetricCard label="Risk style" value={data.latestRun.riskSummary} icon={Shield} />
      </div>
      <section className="portfolio-grid">
        <div className="card wide">
          <SectionHeader title="Personal Portfolio Trend" icon={LineChart} compact />
          <PortfolioTrendChart holdings={data.holdings} summary={summary} />
        </div>
        <div className="card">
          <SectionHeader title="Position Size" icon={PieChart} compact />
          <DonutChart holdings={data.holdings} />
        </div>
        <div className="card">
          <SectionHeader title="Unrealized Gain" icon={BarChart3} compact />
          <GainBars holdings={data.holdings} />
        </div>
        <div className="card">
          <SectionHeader title="Scenario Impact" icon={Activity} compact />
          <ScenarioImpact top={summary.topConcentration} total={summary.totalValue} />
        </div>
        <div className="card">
          <SectionHeader title="Tax Impact Estimator" icon={SlidersHorizontal} compact />
          <TaxPanel top={summary.topConcentration} />
        </div>
      </section>
      <div className="card">
        <SectionHeader title="Holdings Detail" icon={WalletCards} compact />
        <HoldingsTable holdings={data.holdings} />
      </div>
    </div>
  );
}

function Strategy({ cash, setCash, riskStyle, setRiskStyle, includeOwned, setIncludeOwned, plan, holdings, onSave }) {
  const exitPlan = buildExitStrategy(holdings, plan.allocations, cash, riskStyle);
  return (
    <div className="stack">
      <PageTitle title="Investment Strategy" subtitle="Turn new cash into a staged deployment plan that respects concentration risk." />
      <div className="strategy-grid">
        <div className="stack">
          <div className="card">
            <SectionHeader title="Capital Allocation" icon={CircleDollarSign} compact />
            <label className="field-label">Cash available</label>
            <div className="money-input">
              <span>$</span>
              <input value={cash} onChange={(event) => setCash(Number(event.target.value.replace(/[^0-9.]/g, "")) || 0)} />
            </div>
            <label className="toggle-row">
              <input type="checkbox" checked={includeOwned} onChange={(event) => setIncludeOwned(event.target.checked)} />
              Include existing holdings in buy candidates
            </label>
          </div>
          <div className="card">
            <SectionHeader title="Risk Style" icon={Shield} compact />
            <div className="risk-options">
              {["Conservative", "Balanced", "Aggressive"].map((style) => (
                <button
                  key={style}
                  className={`risk-option ${riskStyle === style ? "selected" : ""}`}
                  onClick={() => setRiskStyle(style)}
                >
                  <span>{style}</span>
                  <small>{riskCopy[style]}</small>
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="stack">
          <div className="card">
            <div className="split-heading">
              <SectionHeader title={plan.mode} icon={LineChart} compact />
              <button className="primary-button" onClick={onSave}>
                Save Plan
              </button>
            </div>
            <div className="phase-grid">
              {plan.schedule.map((phase) => (
                <div className="phase-card" key={phase.interval}>
                  <Label>{phase.interval}</Label>
                  <strong>{money(phase.amount)}</strong>
                  <span>{phase.note}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <SectionHeader title="Target Allocation By Ticker" icon={Target} compact />
            <AllocationTable rows={plan.allocations} />
          </div>
          <div className="card exit-card">
            <SectionHeader title="Exit Strategy & Tax Plan" icon={Shield} compact />
            <p>{exitPlan.summary}</p>
            <div className="exit-list">
              {exitPlan.steps.map((step) => (
                <div key={step.title}>
                  <strong>{step.title}</strong>
                  <span>{step.detail}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Ideas({ data }) {
  return (
    <div className="stack">
      <PageTitle title="Buy Ideas" subtitle="Ranked candidates from the dynamic universe, factor model, and headline context." />
      <div className="ideas-grid">
        {data.buyIdeas.map((idea) => (
          <div className="card idea-card" key={idea.ticker}>
            <div className="idea-top">
              <div className="ticker-badge">{idea.ticker}</div>
              <ScoreRing score={idea.score} />
            </div>
            <h3>{idea.name}</h3>
            <p>{idea.reasons.join(" ")}</p>
            <div className="idea-meta">
              <span>{money(idea.price)}</span>
              <StatusPill tone={idea.modelDecision.includes("Watch") ? "warning" : "positive"}>{idea.modelDecision}</StatusPill>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Research({ data }) {
  return (
    <div className="stack">
      <PageTitle title="Research" subtitle="Alpha factor IC, strategy monitor signals, and sentiment context." />
      <section className="research-grid">
        <div className="card">
          <SectionHeader title="Factor IC" icon={BarChart3} compact />
          <FactorChart rows={data.factorIc} />
        </div>
        <div className="card">
          <SectionHeader title="Strategy Monitor" icon={Activity} compact />
          <StrategySignals signals={data.signals} />
        </div>
        <div className="card wide">
          <SectionHeader title="Market Sentiment" icon={Brain} compact />
          <p className="ai-summary">
            Current signals indicate cautious optimism. Momentum remains strongest in semiconductors, but concentration and
            earnings-proximity risk argue for staged deployment instead of adding aggressively into existing winners.
          </p>
          <div className="sentiment-grid">
            <SentimentTile label="Primary driver" value="Semiconductor breadth" />
            <SentimentTile label="Volatility outlook" value="Moderate elevation" tone="warning" />
            <SentimentTile label="Strategy bias" value="Staged buy" tone="positive" />
          </div>
        </div>
      </section>
    </div>
  );
}

function MarketSentiment({ data }) {
  const topIdeas = data.buyIdeas.slice(0, 5);
  const riskSignals = data.signals.filter((signal) => signal.action?.includes("DO NOT ADD") || signal.action?.includes("TRIM"));
  return (
    <div className="stack">
      <PageTitle title="Market Sentiment" subtitle="Headline context, strategy bias, and risk flags for the current portfolio universe." />
      <section className="research-grid">
        <div className="card wide sentiment-hero">
          <SectionHeader title="Beacon Intelligence Summary" icon={Brain} compact />
          <p>
            Momentum remains constructive across the strongest candidates, but portfolio concentration means new risk should
            be staged. The highest-confidence setup is not necessarily the best add if it increases single-sector exposure.
          </p>
          <div className="sentiment-grid">
            <SentimentTile label="Primary driver" value="Portfolio concentration" tone="warning" />
            <SentimentTile label="Best candidate score" value={num(Math.max(...topIdeas.map((idea) => idea.score || 0), 0))} tone="positive" />
            <SentimentTile label="Risk flags" value={String(riskSignals.length)} tone={riskSignals.length ? "warning" : "positive"} />
          </div>
        </div>
        <div className="card">
          <SectionHeader title="Candidate Sentiment" icon={Sparkles} compact />
          <IdeaList ideas={topIdeas} />
        </div>
        <div className="card">
          <SectionHeader title="Risk Feed" icon={AlertTriangle} compact />
          <StrategySignals signals={riskSignals.length ? riskSignals : data.signals.slice(0, 5)} />
        </div>
      </section>
    </div>
  );
}

function SecuritySearch({ query, setQuery, result, loading, onSearch, suggestions }) {
  const snapshot = result?.snapshot || {};
  return (
    <div className="stack">
      <PageTitle title="Security Analysis" subtitle="Analyze a stock, ETF, or mutual fund by ticker using the same backend factor engine." />
      <section className="card search-analysis-card">
        <form
          className="security-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSearch(query);
          }}
        >
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value.toUpperCase())}
            placeholder="AAPL, SPY, VTI, FXAIX..."
            list="search-page-symbol-suggestions"
          />
          <datalist id="search-page-symbol-suggestions">
            {suggestions.map((item) => (
              <option key={`${item.ticker}-${item.name}-search`} value={item.ticker}>
                {item.name}
              </option>
            ))}
          </datalist>
          <button className="primary-button" disabled={loading}>
            <Search size={16} />
            {loading ? "Analyzing" : "Analyze"}
          </button>
        </form>
      </section>
      {result ? (
        <>
          <section className="metric-grid">
            <MetricCard label="Ticker" value={result.ticker} icon={Target} />
            <MetricCard label="Signal" value={result.signal} icon={TrendingUp} tone={result.score >= 0.45 ? "positive" : "warning"} />
            <MetricCard label="Score" value={num(result.score)} icon={Gauge} />
            <MetricCard label="Price" value={money(snapshot.price)} icon={CircleDollarSign} />
          </section>
          <section className="portfolio-grid">
            <div className="card wide">
              <SectionHeader title={`${result.ticker} Price Trend`} icon={LineChart} compact />
              <PriceTrendChart rows={result.priceHistory || []} />
            </div>
            <div className="card">
              <SectionHeader title="Factor Snapshot" icon={BarChart3} compact />
              <div className="security-stats">
                <SentimentTile label="12-1 momentum" value={pct(snapshot.momentum_12_1)} />
                <SentimentTile label="6M momentum" value={pct(snapshot.momentum_6m)} />
                <SentimentTile label="Volatility" value={pct(snapshot.volatility)} tone="warning" />
                <SentimentTile label="Max drawdown" value={pct(snapshot.max_drawdown)} tone="danger" />
                <SentimentTile label="52w high proximity" value={pct(snapshot.near_52w_high)} />
                <SentimentTile label="Target gap" value={pct(snapshot.target_gap)} tone={snapshot.target_gap >= 0 ? "positive" : "warning"} />
              </div>
            </div>
            <div className="card">
              <SectionHeader title="Why It Scored This Way" icon={Sparkles} compact />
              <div className="reason-list">
                {(result.reasons || []).map((reason) => (
                  <div key={reason}>
                    <Check size={15} />
                    <span>{reason}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card wide">
              <SectionHeader title="Recent Headlines" icon={Brain} compact />
              <div className="headline-list">
                {(snapshot.news_items || []).slice(0, 6).map((item) => (
                  <a key={item.link || item.title} href={item.link} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                ))}
              </div>
            </div>
          </section>
        </>
      ) : (
        <div className="card empty-state">
          <Search size={28} />
          <h3>Search a ticker to begin</h3>
          <p>Use common stock, ETF, and mutual fund symbols. The backend pulls price history, fundamentals, news, momentum, drawdown, volatility, and analyst fields where available.</p>
        </div>
      )}
    </div>
  );
}

function ProfileConnections({ profile, connections, user }) {
  return (
    <div className="stack">
      <PageTitle title="Profile & Connections" subtitle="Account identity, saved preferences, and broker connection metadata." />
      <section className="profile-grid">
        <div className="card">
          <SectionHeader title="Profile" icon={User} compact />
          <div className="profile-facts">
            <SentimentTile label="Display name" value={profile?.displayName || "Investor"} />
            <SentimentTile label="Email" value={user?.email || "Not set"} />
            <SentimentTile label="Risk style" value={profile?.defaultRiskStyle || "Balanced"} />
            <SentimentTile label="Tax rate" value={pct(profile?.defaultTaxRate ?? 0.24)} />
          </div>
        </div>
        <div className="card">
          <SectionHeader title="Broker Connections" icon={Lock} compact />
          <div className="connection-list">
            {connections.length ? (
              connections.map((connection) => (
                <div className="connection-row" key={connection.id}>
                  <span>
                    {connection.nickname}
                    <small>{connection.broker} · {connection.accountCount || 0} accounts</small>
                  </span>
                  <StatusPill tone={connection.status === "connected" ? "positive" : "warning"}>{connection.status}</StatusPill>
                </div>
              ))
            ) : (
              <p className="muted">No broker metadata saved yet.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function Connect({ onConnect, connections, user, brokerCredentials, onDelete, exportData }) {
  const [broker, setBroker] = useState("robinhood");
  const [nickname, setNickname] = useState("Robinhood Brokerage");
  const [testSavedCredentials, setTestSavedCredentials] = useState(true);
  const [username, setUsername] = useState(brokerCredentials?.ROBINHOOD_USERNAME || "");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const stepState = buildConnectionSteps({ broker, busy, connections, message });

  async function submitConnection() {
    if (broker === "robinhood" && testSavedCredentials && (!username.trim() || !password)) {
      setMessage("Enter your Robinhood username and password before linking.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await onConnect({
        broker,
        nickname,
        testSavedCredentials,
        brokerCredentials:
          broker === "robinhood"
            ? {
                ROBINHOOD_USERNAME: username,
                ROBINHOOD_PASSWORD: password,
                ROBINHOOD_MFA_CODE: mfaCode,
              }
            : null,
      });
      setMessage("Connection metadata saved.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="connect-page">
      <div>
        <PageTitle
          title="Secure Broker Connection"
          subtitle="Store only metadata in Firestore. Credentials should be handled by Cloud Functions and Secret Manager."
          exportData={exportData}
        />
        <div className="stepper">
          {stepState.map((step, index) => (
            <div className="step" key={step.label}>
              <div className={step.state}>{step.state === "done" ? <Check size={16} /> : index + 1}</div>
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="card connect-card">
        <SectionHeader title="Broker Link" icon={Lock} compact />
        <p>
          This creates a read-only broker metadata record. For local Robinhood testing, the API validates the username,
          password, and MFA code entered here. Passwords are kept only in this browser session and are not stored in
          Firebase.
        </p>
        <div className="broker-form">
          <label>
            <span>Broker</span>
            <select value={broker} onChange={(event) => {
              setBroker(event.target.value);
              setNickname(event.target.value === "robinhood" ? "Robinhood Brokerage" : "Fidelity Brokerage");
            }}>
              <option value="robinhood">Robinhood</option>
              <option value="fidelity">Fidelity</option>
            </select>
          </label>
          <label>
            <span>Nickname</span>
            <input value={nickname} onChange={(event) => setNickname(event.target.value)} />
          </label>
          {broker === "robinhood" && (
            <>
              <label>
                <span>Robinhood username/email</span>
                <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
              </label>
              <label>
                <span>Robinhood password</span>
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type="password"
                  autoComplete="current-password"
                />
              </label>
              <label>
                <span>MFA code</span>
                <input value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} placeholder="Optional fresh 6-digit code" />
              </label>
            </>
          )}
          <label className="toggle-row compact">
            <input
              type="checkbox"
              checked={testSavedCredentials}
              onChange={(event) => setTestSavedCredentials(event.target.checked)}
              disabled={broker !== "robinhood"}
            />
            Validate Robinhood credentials now
          </label>
          <button className="primary-button" onClick={submitConnection} disabled={busy || !user}>
            {busy ? "Linking" : "Link Account"}
          </button>
          {!user && <p className="setup-text">Sign in before saving broker metadata.</p>}
          {message && <p className="setup-text">{message}</p>}
        </div>
        <div className="broker-grid">
          {["robinhood", "fidelity"].map((broker) => (
            <button className="broker-card" key={broker} onClick={() => {
              setBroker(broker);
              setNickname(broker === "robinhood" ? "Robinhood Brokerage" : "Fidelity Brokerage");
            }}>
              <BrokerLogo broker={broker} />
              <div>
                <strong>{broker}</strong>
                <span>Read-only holdings and balances</span>
              </div>
            </button>
          ))}
        </div>
        <LogoAttribution />
        <div className="connection-list">
          {connections.length ? (
            connections.map((connection) => (
              <div className="connection-row" key={connection.id}>
                <span>
                  {connection.nickname}
                  {connection.lastError && <small>{connection.lastError}</small>}
                </span>
                <div className="row-actions">
                  <StatusPill tone={connection.status === "connected" ? "positive" : "warning"}>{connection.status}</StatusPill>
                  <button className="secondary-button compact-button" onClick={() => onDelete(connection)}>
                    Delete
                  </button>
                </div>
              </div>
            ))
          ) : (
            <p className="muted">No broker metadata saved yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function NotificationsDrawer({ notifications, onClose }) {
  return (
    <div className="overlay">
      <aside className="drawer">
        <div className="drawer-head">
          <div>
            <Label>Notifications</Label>
            <h3>Beacon alerts</h3>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close notifications">×</button>
        </div>
        <div className="notification-list">
          {notifications.map((item) => (
            <div className={`notification-card ${item.tone}`} key={item.id}>
              <StatusPill tone={item.tone}>{item.label}</StatusPill>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

function SettingsModal({ profile, user, onClose, onSave }) {
  const [displayName, setDisplayName] = useState(profile?.displayName || "");
  const [riskStyle, setRiskStyle] = useState(profile?.defaultRiskStyle || "Balanced");
  const [taxRate, setTaxRate] = useState(String(profile?.defaultTaxRate ?? 0.24));
  const [openAiEnabled, setOpenAiEnabled] = useState(Boolean(profile?.openAiEnabled));
  const [subscriptionTier, setSubscriptionTier] = useState(profile?.subscriptionTier || "local-dev");
  const [busy, setBusy] = useState(false);

  async function submitSettings() {
    setBusy(true);
    try {
      await onSave({
        displayName: displayName || "Beacon Investor",
        defaultRiskStyle: riskStyle,
        defaultTaxRate: Number(taxRate) || 0,
        openAiEnabled,
        subscriptionTier,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay">
      <section className="modal card">
        <div className="drawer-head">
          <div>
            <Label>Settings</Label>
            <h3>Profile and defaults</h3>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close settings">×</button>
        </div>
        <div className="settings-grid">
          <label>
            <span>Signed-in user</span>
            <input value={user?.email || user?.phoneNumber || user?.uid || "Not signed in"} disabled />
          </label>
          <label>
            <span>Display name</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </label>
          <label>
            <span>Default risk style</span>
            <select value={riskStyle} onChange={(event) => setRiskStyle(event.target.value)}>
              <option>Conservative</option>
              <option>Balanced</option>
              <option>Aggressive</option>
            </select>
          </label>
          <label>
            <span>Default tax rate</span>
            <input value={taxRate} onChange={(event) => setTaxRate(event.target.value)} />
          </label>
          <label>
            <span>Subscription tier</span>
            <select value={subscriptionTier} onChange={(event) => setSubscriptionTier(event.target.value)}>
              <option value="local-dev">Local dev</option>
              <option value="free">Free</option>
              <option value="private-wealth">Private wealth</option>
            </select>
          </label>
          <label className="toggle-row compact">
            <input type="checkbox" checked={openAiEnabled} onChange={(event) => setOpenAiEnabled(event.target.checked)} />
            Enable OpenAI summaries by default
          </label>
        </div>
        <div className="modal-actions">
          <button className="secondary-button" onClick={onClose}>Cancel</button>
          <button className="primary-button" onClick={submitSettings} disabled={busy || !user}>
            {busy ? "Saving" : "Save Settings"}
          </button>
        </div>
      </section>
    </div>
  );
}

function AuthPanel({ firebaseState, refreshAuth, onAuthSuccess }) {
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [smsCode, setSmsCode] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function runAuth(label, action) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      setMessage(label);
      refreshAuth();
      if (onAuthSuccess) onAuthSuccess();
    } catch (error) {
      setMessage(firebaseErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  const signedInLabel = firebaseState.user
    ? firebaseState.user.isAnonymous
      ? `Anonymous test user: ${firebaseState.user.uid.slice(0, 8)}`
      : firebaseState.user.email || firebaseState.user.phoneNumber || firebaseState.user.uid
    : "Not signed in";

  return (
    <section className="auth-card card">
      <div className="split-heading">
        <div>
          <Label>Firebase Authentication</Label>
          <h3>{signedInLabel}</h3>
          <p>
            Email, phone, and anonymous test auth are wired to Firebase Auth. Phone sign-in uses the SDK reCAPTCHA flow
            from Firebase’s web phone-auth guide.
          </p>
        </div>
        <StatusPill tone={firebaseState.user ? "positive" : "warning"}>
          {firebaseState.user ? "Signed in" : "Auth required"}
        </StatusPill>
      </div>
      <div className="auth-tabs">
        {[
          ["signin", "Sign In"],
          ["create", "Create Account"],
          ["phone", "Phone"],
          ["anonymous", "Anonymous"],
        ].map(([item, label]) => (
          <button key={item} className={mode === item ? "selected" : ""} onClick={() => setMode(item)}>
            {label}
          </button>
        ))}
      </div>
      {mode === "signin" && (
        <div className="auth-mode-panel">
          <div>
            <h4>Sign in</h4>
            <p>Use an existing Beacon account to open your dashboard.</p>
          </div>
          <input className="text-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
          <input className="text-input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
          <button className="primary-button" disabled={busy} onClick={() => runAuth("Signed in with email.", () => signInWithEmail(email, password))}>
            Sign In
          </button>
        </div>
      )}
      {mode === "create" && (
        <div className="auth-mode-panel">
          <div>
            <h4>Create account</h4>
            <p>Create a new Beacon profile, then continue to your dashboard.</p>
          </div>
          <input className="text-input" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" />
          <input className="text-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
          <input className="text-input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
          <button className="primary-button" disabled={busy} onClick={() => runAuth("Email account created.", () => createEmailAccount(email, password, displayName))}>
            Create Account
          </button>
        </div>
      )}
      {mode === "phone" && (
        <div className="auth-grid">
          <input className="text-input" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+1 650-555-3434" />
          <button className="secondary-button" disabled={busy} onClick={() => runAuth("Verification code sent.", () => sendPhoneVerificationCode(phone))}>
            Send SMS Code
          </button>
          <input className="text-input" value={smsCode} onChange={(event) => setSmsCode(event.target.value)} placeholder="6-digit code" />
          <button className="primary-button" disabled={busy} onClick={() => runAuth("Signed in with phone.", () => confirmPhoneVerificationCode(smsCode))}>
            Verify Code
          </button>
          <div id="recaptcha-container" className="recaptcha-box" />
        </div>
      )}
      {mode === "anonymous" && (
        <div className="auth-grid two">
          <button className="primary-button" disabled={busy} onClick={() => runAuth("Signed in anonymously.", signInWithAnonymousTestUser)}>
            Anonymous Test Sign In
          </button>
          <button className="secondary-button" disabled={busy || !firebaseState.user} onClick={() => runAuth("Signed out.", signOutOfFirebase)}>
            Sign Out
          </button>
        </div>
      )}
      {mode !== "anonymous" && (
        <button className="secondary-button auth-signout" disabled={busy || !firebaseState.user} onClick={() => runAuth("Signed out.", signOutOfFirebase)}>
          Sign Out
        </button>
      )}
      {message && <p className="setup-text">{message}</p>}
    </section>
  );
}

function ActionCard({ action }) {
  const risk = action.action.includes("CONCENTRATED") ? "danger" : action.action.includes("UNDERWEIGHT") ? "positive" : "neutral";
  return (
    <div className="card action-card">
      <StatusPill tone={risk}>{action.ticker}</StatusPill>
      <h3>{action.action}</h3>
      <div className="action-metrics">
        <span>Score {num(action.score ?? action.finalScore)}</span>
        <span>{action.status || "Active"}</span>
      </div>
    </div>
  );
}

function RiskBars({ holdings }) {
  return (
    <div className="risk-bars">
      {holdings.slice(0, 6).map((holding) => (
        <div className="risk-bar" key={holding.ticker}>
          <span>{holding.ticker}</span>
          <div>
            <i style={{ width: `${Math.min(100, holding.portfolioWeight * 100)}%` }} />
          </div>
          <strong>{pct(holding.portfolioWeight)}</strong>
        </div>
      ))}
    </div>
  );
}

function IdeaList({ ideas }) {
  return (
    <div className="idea-list">
      {ideas.map((idea) => (
        <div className="idea-row" key={idea.ticker}>
          <div className="ticker-badge small">{idea.ticker}</div>
          <div>
            <strong>{idea.name}</strong>
            <span>{idea.reasons[0]}</span>
          </div>
          <b>{num(idea.score)}</b>
        </div>
      ))}
    </div>
  );
}

function HoldingsTable({ holdings }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Action</th>
            <th>Weight</th>
            <th>Value</th>
            <th>Gain</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr key={holding.ticker}>
              <td><span className="ticker-cell">{holding.ticker}</span></td>
              <td>{holding.action}</td>
              <td>{pct(holding.portfolioWeight)}</td>
              <td>{money(holding.marketValue)}</td>
              <td className={holding.unrealizedGain >= 0 ? "positive" : "danger"}>{pct(holding.unrealizedGain)}</td>
              <td>{num(holding.finalScore)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DonutChart({ holdings }) {
  let start = 0;
  const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#64748b"];
  const gradient = holdings
    .slice(0, 7)
    .map((holding, index) => {
      const end = start + holding.portfolioWeight * 100;
      const part = `${colors[index]} ${start}% ${end}%`;
      start = end;
      return part;
    })
    .join(", ");
  return (
    <div className="donut-layout">
      <div className="donut" style={{ background: `conic-gradient(${gradient}, #334155 ${start}% 100%)` }} />
      <div className="legend">
        {holdings.slice(0, 7).map((holding, index) => (
          <div key={holding.ticker}>
            <i style={{ background: colors[index] }} />
            <span>{holding.ticker}</span>
            <strong>{pct(holding.portfolioWeight)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function GainBars({ holdings }) {
  const rows = holdings.slice(0, 8);
  const maxGain = Math.max(...rows.map((holding) => Math.abs(holding.unrealizedGain || 0)), 0.01);
  return (
    <div className="gain-chart-wrap" title="Unrealized gain or loss by holding, scaled against the largest absolute gain in this view.">
      <div className="gain-y-axis">
        <span>{pct(maxGain)}</span>
        <span>0%</span>
        <span>{pct(-maxGain)}</span>
      </div>
      <div className="gain-chart">
        {rows.map((holding) => {
          const value = holding.unrealizedGain || 0;
          return (
            <div key={holding.ticker} title={`${holding.ticker}: ${pct(value)} unrealized ${value >= 0 ? "gain" : "loss"}`}>
              <span className="gain-value">{pct(value)}</span>
              <div className={value >= 0 ? "up" : "down"} style={{ height: `${Math.max(14, Math.min(95, (Math.abs(value) / maxGain) * 92))}%` }} />
              <span>{holding.ticker}</span>
            </div>
          );
        })}
      </div>
      <div className="chart-axis gain-x-axis">
        <span>Holdings</span>
        <span>Unrealized gain/loss</span>
      </div>
    </div>
  );
}

function TooltipWrap({ tip, children }) {
  return (
    <span className="tooltip-wrap" title={tip}>
      {children}
    </span>
  );
}

function InfoDot({ tip }) {
  return (
    <span className="info-dot" title={tip} aria-label={tip}>
      ?
    </span>
  );
}

function withTip(label, tip) {
  return (
    <>
      {label}
      <InfoDot tip={tip} />
    </>
  );
}

function ScenarioImpact({ top, total }) {
  return (
    <div className="scenario-grid">
      {[-0.2, -0.3, -0.4].map((drop) => (
        <div key={drop}>
          <Label>{pct(drop)} move in {top.ticker}</Label>
          <strong>{money(total * top.weight * drop)}</strong>
          <span>Portfolio impact {pct(top.weight * drop)}</span>
        </div>
      ))}
    </div>
  );
}

function TaxPanel({ top }) {
  const trimValue = top.value * 0.2;
  const taxableGain = trimValue * Math.max(0, top.gainPct || 0);
  return (
    <div className="tax-panel">
      <div>
        <Label>Trim target</Label>
        <strong>{money(trimValue)}</strong>
      </div>
      <div>
        <Label>Est. taxable gain</Label>
        <strong>{money(taxableGain)}</strong>
      </div>
      <div>
        <Label>Tax reserve @ 24%</Label>
        <strong>{money(taxableGain * 0.24)}</strong>
      </div>
    </div>
  );
}

function AllocationTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Target</th>
            <th>Amount</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker}>
              <td><span className="ticker-cell">{row.ticker}</span></td>
              <td>{pct(row.weight)}</td>
              <td>{money(row.amount)}</td>
              <td>{row.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FactorChart({ rows }) {
  return (
    <div className="factor-chart">
      {rows.map((row) => (
        <div className="factor-row" key={row.factorName}>
          <span>{row.factorName.replaceAll("_", " ")}</span>
          <div>
            <i className={row.icValue >= 0 ? "positive-bg" : "danger-bg"} style={{ width: `${Math.abs(row.icValue) * 100}%` }} />
          </div>
          <strong>{num(row.icValue)}</strong>
        </div>
      ))}
    </div>
  );
}

function StrategySignals({ signals }) {
  return (
    <div className="signal-list">
      {signals.slice(0, 8).map((signal) => (
        <div className="signal-row" key={`${signal.ticker}-${signal.strategy}`}>
          <span>{signal.ticker}</span>
          <strong>{signal.action}</strong>
          <b>{num(signal.score)}</b>
        </div>
      ))}
    </div>
  );
}

function ScoreRing({ score }) {
  const percent = Math.max(0, Math.min(100, score * 100));
  return <div className="score-ring" style={{ "--score": `${percent}%` }}>{num(score)}</div>;
}

function MetricCard({ label, value, icon: Icon, tone = "neutral" }) {
  const tip = PANEL_TOOLTIPS[label] || `Beacon metric: ${label}`;
  return (
    <div className={`card metric-card ${tone}`} title={tip}>
      <Icon size={20} />
      <Label>{withTip(label, tip)}</Label>
      <strong>{value}</strong>
    </div>
  );
}

function SectionHeader({ title, action, icon: Icon, compact = false, onAction, actionDisabled = false }) {
  const tip = PANEL_TOOLTIPS[title] || "This panel summarizes the latest account-specific Beacon analysis.";
  return (
    <div className={`section-header ${compact ? "compact" : ""}`} title={tip}>
      <div>
        {Icon && <Icon size={20} />}
        <h2>{title}</h2>
        <InfoDot tip={tip} />
      </div>
      {action && (
        <button className="secondary-button" onClick={onAction} disabled={actionDisabled}>
          {action}
        </button>
      )}
    </div>
  );
}

function PageTitle({ title, subtitle, exportData = null }) {
  return (
    <header className="page-title" title={subtitle}>
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <button className="secondary-button" onClick={() => exportJson(slugify(title), exportData || { title, subtitle, exportedAt: new Date().toISOString() })}>
        <Download size={16} />
        Export
      </button>
    </header>
  );
}

function Label({ children }) {
  return <span className="label">{children}</span>;
}

function StatusPill({ children, tone = "neutral" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function SentimentTile({ label, value, tone = "neutral" }) {
  return (
    <div className={`sentiment-tile ${tone}`}>
      <Label>{label}</Label>
      <strong>{value}</strong>
    </div>
  );
}

function BrokerLogo({ broker }) {
  const domain = broker === "robinhood" ? "robinhood.com" : broker === "fidelity" ? "fidelity.com" : `${broker}.com`;
  return <CompanyLogo domain={domain} name={broker} />;
}

function CompanyLogo({ domain, name }) {
  return (
    <span className="company-logo">
      <img src={`https://logos-api.apistemic.com/domain:${domain}`} alt={`${name} logo`} width="32" height="32" loading="lazy" />
    </span>
  );
}

function LogoAttribution() {
  return (
    <p className="logo-attribution">
      Logos by <a href="https://logos.apistemic.com">apistemic logos</a>
    </p>
  );
}

function PriceTrendChart({ rows }) {
  const points = (rows || [])
    .filter((row) => Number.isFinite(Number(row.close)))
    .map((row) => ({
      label: row.date,
      value: Number(row.close),
      open: Number(row.open ?? row.close),
      high: Number(row.high ?? row.close),
      low: Number(row.low ?? row.close),
      close: Number(row.close),
    }));
  return <LineSeriesChart points={points} valueLabel={(value) => money(value)} emptyText="Search data did not include price history." />;
}

function PortfolioTrendChart({ holdings, summary }) {
  const points = buildPortfolioTrend(holdings, summary.totalValue);
  return <LineSeriesChart points={points} valueLabel={(value) => money(value)} emptyText="Run analysis after linking an account to refresh portfolio trend." />;
}

function LineSeriesChart({ points, valueLabel, emptyText }) {
  const [range, setRange] = useState("6M");
  const [chartType, setChartType] = useState("line");
  const [hoverPoint, setHoverPoint] = useState(null);
  const allPoints = (points || []).filter((point) => Number.isFinite(point.value));
  const cleanPoints = sliceChartRange(allPoints, range);
  if (cleanPoints.length < 2) {
    return (
      <div className="chart-empty">
        <LineChart size={24} />
        <span>{emptyText}</span>
      </div>
    );
  }
  const width = 720;
  const height = 230;
  const padding = 24;
  const values = cleanPoints.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const valueRange = max - min || 1;
  const coordinates = cleanPoints.map((point, index) => {
    const x = padding + (index / Math.max(1, cleanPoints.length - 1)) * (width - padding * 2);
    const y = height - padding - ((point.value - min) / valueRange) * (height - padding * 2);
    return { ...point, x, y };
  });
  const linePath = coordinates.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
  const areaPath = `${linePath} L ${coordinates.at(-1).x.toFixed(2)} ${height - padding} L ${coordinates[0].x.toFixed(2)} ${height - padding} Z`;
  const start = cleanPoints[0].value;
  const latest = cleanPoints.at(-1).value;
  const change = start ? latest / start - 1 : 0;

  return (
    <div className="line-chart-card">
      <div className="chart-controls">
        <div className="segmented-control">
          {["1M", "3M", "6M", "1Y"].map((item) => (
            <button key={item} className={range === item ? "selected" : ""} onClick={() => setRange(item)}>
              {item}
            </button>
          ))}
        </div>
        <div className="segmented-control">
          {["line", "candles"].map((item) => (
            <button key={item} className={chartType === item ? "selected" : ""} onClick={() => setChartType(item)}>
              {item === "line" ? "Line" : "Candles"}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-meta">
        <div>
          <Label>Latest</Label>
          <strong>{valueLabel(latest)}</strong>
        </div>
        <span className={change >= 0 ? "positive" : "danger"}>{pct(change)}</span>
      </div>
      <svg
        className="line-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Price trend chart"
        onMouseLeave={() => setHoverPoint(null)}
        onMouseMove={(event) => {
          const box = event.currentTarget.getBoundingClientRect();
          const x = ((event.clientX - box.left) / box.width) * width;
          const nearest = coordinates.reduce((best, point) => (Math.abs(point.x - x) < Math.abs(best.x - x) ? point : best), coordinates[0]);
          setHoverPoint(nearest);
        }}
      >
        {[max, min + valueRange / 2, min].map((tick) => {
          const y = height - padding - ((tick - min) / valueRange) * (height - padding * 2);
          return (
            <g className="chart-gridline" key={tick}>
              <line x1={padding} x2={width - padding} y1={y} y2={y} />
              <text x={4} y={y + 4}>{valueLabel(tick)}</text>
            </g>
          );
        })}
        {chartType === "line" ? (
          <>
            <path className="line-area" d={areaPath} />
            <path className="line-path" d={linePath} />
            {coordinates.filter((_, index) => index === 0 || index === coordinates.length - 1).map((point) => (
              <circle key={`${point.label}-${point.value}`} cx={point.x} cy={point.y} r="4" />
            ))}
          </>
        ) : (
          <Candles coordinates={coordinates} min={min} valueRange={valueRange} height={height} padding={padding} />
        )}
        {hoverPoint && (
          <g className="chart-hover">
            <line x1={hoverPoint.x} x2={hoverPoint.x} y1={padding} y2={height - padding} />
            <circle cx={hoverPoint.x} cy={hoverPoint.y} r="5" />
          </g>
        )}
      </svg>
      {hoverPoint && (
        <div className="chart-tooltip-inline">
          <strong>{hoverPoint.label || "Point"}</strong>
          <span>{valueLabel(hoverPoint.value)}</span>
        </div>
      )}
      <div className="chart-axis">
        <span>{cleanPoints[0].label}</span>
        <span>{valueLabel(min)}</span>
        <span>{valueLabel(max)}</span>
        <span>{cleanPoints.at(-1).label}</span>
      </div>
    </div>
  );
}

function Candles({ coordinates, min, valueRange, height, padding }) {
  const chartHeight = height - padding * 2;
  const candleWidth = Math.max(3, Math.min(12, 360 / Math.max(1, coordinates.length)));
  const yFor = (value) => height - padding - ((value - min) / valueRange) * chartHeight;
  return (
    <g className="candles">
      {coordinates.map((point, index) => {
        const open = Number.isFinite(point.open) ? point.open : point.value;
        const close = Number.isFinite(point.close) ? point.close : point.value;
        const high = Number.isFinite(point.high) ? point.high : Math.max(open, close, point.value);
        const low = Number.isFinite(point.low) ? point.low : Math.min(open, close, point.value);
        const up = close >= open;
        const bodyTop = yFor(Math.max(open, close));
        const bodyHeight = Math.max(2, Math.abs(yFor(open) - yFor(close)));
        return (
          <g key={`${point.label}-${index}`} className={up ? "candle up" : "candle down"}>
            <line x1={point.x} x2={point.x} y1={yFor(high)} y2={yFor(low)} />
            <rect x={point.x - candleWidth / 2} y={bodyTop} width={candleWidth} height={bodyHeight} rx="1.5" />
          </g>
        );
      })}
    </g>
  );
}

function buildSummary(holdings, latestRun) {
  const totalValue = latestRun.portfolioValue || holdings.reduce((sum, row) => sum + row.marketValue, 0);
  const sorted = [...holdings].sort((a, b) => b.portfolioWeight - a.portfolioWeight);
  const top = sorted[0] || {};
  return {
    totalValue,
    todayChange: latestRun.todayChange || 0,
    todayChangePct: latestRun.todayChangePct || 0,
    positions: holdings.length,
    concentratedCount: holdings.filter((row) => row.portfolioWeight >= 0.2).length,
    topConcentration: {
      ticker: top.ticker || "N/A",
      weight: top.portfolioWeight || 0,
      value: top.marketValue || 0,
      gainPct: top.unrealizedGain || 0,
    },
  };
}

function buildSearchSuggestions(data) {
  const names = new Map(COMMON_SYMBOLS.map((item) => [item.ticker, item.name]));
  const tickers = new Set();
  for (const row of [...(data.holdings || []), ...(data.buyIdeas || []), ...(data.signals || [])]) {
    if (row.ticker) {
      tickers.add(row.ticker.toUpperCase());
      if (row.name) names.set(row.ticker.toUpperCase(), row.name);
      if (row.sector && !names.has(row.ticker.toUpperCase())) names.set(row.ticker.toUpperCase(), row.sector);
    }
  }
  for (const item of COMMON_SYMBOLS) tickers.add(item.ticker);
  return [...tickers]
    .sort((a, b) => a.localeCompare(b))
    .map((ticker) => ({ ticker, name: names.get(ticker) || ticker }))
    .slice(0, 80);
}

function buildConnectionSteps({ broker, busy, connections, message }) {
  const hasConnection = connections.some((connection) => connection.broker === broker);
  const connected = connections.some((connection) => connection.broker === broker && connection.status === "connected");
  const hasError = message && !message.includes("saved");
  return [
    { label: "Choose Broker", state: broker ? "done" : "current" },
    { label: "Validate Session", state: connected ? "done" : busy ? "current" : hasError ? "error" : "current" },
    { label: "Save Metadata", state: hasConnection ? "done" : connected ? "current" : "" },
    { label: "Sync Holdings", state: connected ? "done" : hasConnection ? "current" : "" },
  ];
}

function sliceChartRange(points, range) {
  const counts = { "1M": 22, "3M": 66, "6M": 126, "1Y": 252 };
  return points.slice(-Math.min(points.length, counts[range] || 126));
}

function buildPortfolioTrend(holdings, totalValue) {
  const base = totalValue || holdings.reduce((sum, holding) => sum + (holding.marketValue || 0), 0);
  if (!base) return [];
  const weightedGain = holdings.reduce((sum, holding) => {
    const weight = holding.portfolioWeight || 0;
    return sum + weight * (holding.unrealizedGain || 0);
  }, 0);
  const startValue = base / (1 + Math.max(-0.85, weightedGain || 0.08));
  const points = [];
  for (let index = 0; index < 26; index += 1) {
    const progress = index / 25;
    const wave = Math.sin(progress * Math.PI * 3) * 0.018 + Math.cos(progress * Math.PI * 5) * 0.01;
    const value = startValue + (base - startValue) * progress + base * wave;
    const previous = points[index - 1]?.value ?? value * 0.995;
    const high = Math.max(value, previous) * 1.006;
    const low = Math.min(value, previous) * 0.994;
    points.push({
      label: index === 0 ? "6M ago" : index === 25 ? "Today" : "",
      value: Math.max(0, value),
      open: previous,
      high,
      low,
      close: value,
    });
  }
  return points;
}

function buildExitStrategy(holdings, allocations, cash, riskStyle) {
  const topTargets = allocations.slice(0, 3).map((row) => row.ticker).join(", ") || "new positions";
  const concentrated = [...holdings].sort((a, b) => (b.portfolioWeight || 0) - (a.portfolioWeight || 0))[0];
  const weak = holdings.filter((holding) => (holding.finalScore || 0) < 0.25).map((holding) => holding.ticker).slice(0, 3);
  const pace = riskStyle === "Aggressive" ? "tighter price and drawdown triggers" : riskStyle === "Conservative" ? "slower staged exits and wider confirmation windows" : "balanced staged trims";
  const firstReview = concentrated?.ticker || weak[0] || "the largest current holding";
  const targetWeight = riskStyle === "Conservative" ? 0.18 : riskStyle === "Aggressive" ? 0.28 : 0.22;
  const excessWeight = Math.max(0, (concentrated?.portfolioWeight || 0) - targetWeight);
  const estimatedPortfolio = holdings.reduce((sum, holding) => sum + (holding.marketValue || 0), 0);
  const suggestedTrim = Math.min(concentrated?.marketValue || 0, estimatedPortfolio * excessWeight);
  const taxableGain = suggestedTrim * Math.max(0, concentrated?.unrealizedGain || 0);
  const taxReserve = taxableGain * 0.24;
  const deployable = Math.max(0, cash + suggestedTrim - taxReserve);
  const buyList = allocations.slice(0, 3).map((row) => `${row.ticker} ${money(deployable * row.weight)}`).join(", ");
  return {
    summary: `For this portfolio, the first concrete exit review is ${firstReview}${concentrated ? ` at ${pct(concentrated.portfolioWeight)} portfolio weight and ${money(concentrated.marketValue)} market value` : ""}. With a ${riskStyle.toLowerCase()} risk style, a practical target is about ${pct(targetWeight)} max weight per single name, implying an estimated trim of ${money(suggestedTrim)} from ${concentrated?.ticker || "the largest holding"} if tax lots allow it. Assuming a 24% reserve on embedded gains, set aside roughly ${money(taxReserve)} and redeploy about ${money(deployable)} total across the staged plan. The first buys to compare are ${buyList || topTargets}. This is planning support, not tax advice; confirm exact lots, wash-sale constraints, and account transfer limitations before placing trades.`,
    steps: [
      {
        title: `Sell/trim candidate: ${concentrated?.ticker || firstReview}`,
        detail: `Consider trimming about ${money(suggestedTrim)} to move closer to a ${pct(targetWeight)} position cap. If the best lots are short-term gains, split the trim into smaller orders or wait for long-term treatment unless risk reduction is urgent.`,
      },
      {
        title: "Tax lot order",
        detail: `Prefer loss lots first, then long-term gain lots. For this estimate, ${money(taxableGain)} of taxable gain creates a rough ${money(taxReserve)} reserve. If taxable accounts hold the position, compare donating appreciated shares or transferring shares in-kind before selling.`,
      },
      {
        title: "Redeploy target",
        detail: `Use ${pace}: deploy into the target plan over the same staged schedule. Based on current inputs, first-pass redeploy dollars are ${buyList || "not available until buy ideas load"}. Keep cash uninvested if the candidate score drops before the next stage.`,
      },
      {
        title: "Account placement",
        detail: "If you have multiple account types, prefer high-turnover or income-heavy positions in tax-advantaged accounts and broad ETF/core holdings in taxable accounts. If transferring accounts, use in-kind ACATS where possible so you do not trigger taxes just to move custodians.",
      },
    ],
  };
}

function exportJson(filename, payload) {
  const body = JSON.stringify({ exportedAt: new Date().toISOString(), ...payload }, null, 2);
  const blob = new Blob([body], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename || "beacon-export"}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function slugify(value) {
  return String(value || "beacon-export").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function buildNotifications(data, summary, firebaseState, backendData) {
  const notifications = [];
  if (!firebaseState.user) {
    notifications.push({
      id: "auth",
      label: "Auth",
      tone: "warning",
      title: "Sign in to save data",
      body: "Portfolio analysis still works locally, but broker metadata and settings require Firebase Auth.",
    });
  }
  if (firebaseState.error) {
    notifications.push({
      id: "firebase",
      label: "Firebase",
      tone: "warning",
      title: "Firebase needs attention",
      body: firebaseState.error,
    });
  }
  const connections = firebaseState.brokerConnections || [];
  if (firebaseState.user && !connections.length) {
    notifications.push({
      id: `broker-none-${firebaseState.user.uid}`,
      label: "Connect",
      tone: "warning",
      title: "No broker linked",
      body: "Connect a read-only brokerage session before running live portfolio analysis.",
    });
  }
  for (const connection of connections.filter((item) => item.status !== "connected")) {
    notifications.push({
      id: `broker-${connection.id}`,
      label: "Broker",
      tone: "warning",
      title: `${connection.nickname || connection.broker} needs attention`,
      body: connection.lastError || "The account metadata exists, but the session is not fully validated.",
    });
  }
  if (summary.topConcentration.weight >= 0.2) {
    notifications.push({
      id: "concentration",
      label: "Risk",
      tone: "danger",
      title: `${summary.topConcentration.ticker} concentration is high`,
      body: `${summary.topConcentration.ticker} is ${pct(summary.topConcentration.weight)} of the portfolio. Avoid adding until the weight comes down.`,
    });
  }
  const urgentAction = data.actions.find((action) => action.action?.includes("DO NOT ADD") || action.action?.includes("TRIM"));
  if (urgentAction) {
    notifications.push({
      id: "action",
      label: "Review",
      tone: "warning",
      title: `${urgentAction.ticker} needs review`,
      body: urgentAction.action,
    });
  }
  if (backendData?.backendMeta) {
    notifications.push({
      id: "backend",
      label: "Analysis",
      tone: "positive",
      title: "Backend analysis completed",
      body: `Last run finished in ${backendData.backendMeta.elapsedSeconds}s using ${(backendData.backendMeta.watchlist || []).length} candidate tickers.`,
    });
  }
  if (!notifications.length) {
    notifications.push({
      id: "clear",
      label: "Status",
      tone: "positive",
      title: "No urgent alerts",
      body: "Authentication, portfolio risk, and analysis state look normal.",
    });
  }
  return notifications;
}

function firebaseErrorMessage(error) {
  if (error.code === "auth/configuration-not-found") {
    return "Firebase Auth is not enabled for this project. In Firebase Console, open Authentication, click Get started, enable Anonymous sign-in, then refresh this page.";
  }
  if (error.code === "PERMISSION_DENIED" || error.code === "permission-denied") {
    return "Firestore rejected the request. Check Firestore rules for users/{userId} access.";
  }
  return error.message || "Firebase is not available.";
}

function readSessionBrokerCredentials() {
  try {
    const saved = sessionStorage.getItem("beacon_robinhood_credentials");
    return saved ? JSON.parse(saved) : null;
  } catch {
    sessionStorage.removeItem("beacon_robinhood_credentials");
    return null;
  }
}

function readAppRoute() {
  const path = window.location.pathname.replace(/\/+$/, "");
  if (path.endsWith("/login")) return "login";
  if (path.endsWith("/dashboard")) return "dashboard";
  return "home";
}

function buildPlan(cash, riskStyle, includeOwned, ideas, holdings) {
  const owned = new Set(holdings.map((holding) => holding.ticker));
  const eligible = ideas
    .filter((idea) => includeOwned || !owned.has(idea.ticker))
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);
  const chunks = riskStyle === "Aggressive" ? [0.5, 0.25, 0.25] : riskStyle === "Conservative" ? [0.25, 0.25, 0.25, 0.25] : [0.34, 0.33, 0.33];
  const labels = chunks.length === 4 ? ["Today", "In 1 week", "In 2 weeks", "In 3 weeks"] : ["Today", "In 1 week", "In 2 weeks"];
  const totalScore = eligible.reduce((sum, idea) => sum + Math.max(idea.score, 0.1), 0) || 1;
  return {
    mode: riskStyle === "Aggressive" ? "Front-loaded staged buy" : riskStyle === "Conservative" ? "Split over four buys" : "Balanced three-step buy",
    schedule: chunks.map((chunk, index) => ({
      interval: labels[index],
      amount: cash * chunk,
      note: index === 0 ? "Ready after review" : "Reassess before entry",
    })),
    allocations: eligible.map((idea) => {
      const weight = Math.max(idea.score, 0.1) / totalScore;
      return {
        ticker: idea.ticker,
        weight,
        amount: cash * weight,
        rationale: idea.reasons[0],
      };
    }),
  };
}

const riskCopy = {
  Conservative: "Capital preservation and slower deployment",
  Balanced: "Moderate growth with staged entry",
  Aggressive: "Higher beta with faster deployment",
};

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
}

function pct(value) {
  return `${((value || 0) * 100).toFixed(1)}%`;
}

function num(value) {
  return Number(value || 0).toFixed(2);
}

createRoot(document.getElementById("root")).render(<App />);
