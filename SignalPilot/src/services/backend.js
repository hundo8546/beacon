const API_BASE = import.meta.env.VITE_SIGNALPILOT_API_URL || "http://127.0.0.1:8787";

export async function analyzePortfolio(options) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  return readJson(response);
}

export async function connectBrokerViaBackend(options) {
  const response = await fetch(`${API_BASE}/api/connect-broker`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(typeof options === "string" ? { broker: options } : options),
  });
  return readJson(response);
}

export async function analyzeSecurity(options) {
  const response = await fetch(`${API_BASE}/api/security`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(typeof options === "string" ? { ticker: options } : options),
  });
  return readJson(response);
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Beacon API request failed with ${response.status}`);
  }
  return data;
}

export function mapBackendAnalysis(payload) {
  const holdings = (payload.holdingsReport || []).filter((row) => !row.error).map(mapHolding);
  const ideas = (payload.ideas || []).filter((row) => !row.error).map(mapIdea);
  const actions = (payload.actions || []).filter((row) => !row.error).map(mapSignal);
  const factorIc = ((payload.alpha && payload.alpha.ic_table) || []).map(mapFactor);
  const signals = ((payload.monitor && payload.monitor.signals) || []).map(mapSignal);
  const summary = payload.summary || {};
  const master = payload.master || {};

  return {
    holdings,
    latestRun: {
      id: payload.asOf || "backend-run",
      portfolioValue: summary.total_value || 0,
      accountEquity: summary.account_equity || summary.total_value || 0,
      todayChange: summary.today_change || 0,
      todayChangePct: summary.today_change_pct || 0,
      riskSummary: (summary.concentrated || []).length ? "Concentrated growth" : "Balanced risk",
      plainEnglishSummary:
        master.plain_english_summary ||
        "Backend analysis completed. Review concentration, action cards, and ranked buy ideas before making any portfolio decision.",
      investmentPlan: "",
      status: "complete",
      asOf: payload.asOf,
    },
    actions,
    buyIdeas: ideas,
    factorIc,
    signals,
    backendMeta: {
      asOf: payload.asOf,
      elapsedSeconds: payload.elapsedSeconds,
      dynamicUniverse: payload.dynamicUniverse,
      watchlist: payload.watchlist,
    },
  };
}

function mapHolding(row) {
  return {
    ticker: row.ticker,
    action: row.action || "HOLD",
    portfolioWeight: row.portfolio_weight || 0,
    marketValue: row.market_value || 0,
    unrealizedGain: row.unrealized_gain || 0,
    finalScore: row.final_score || 0,
    sector: row.sector || "Unknown",
  };
}

function mapIdea(row) {
  return {
    ticker: row.ticker,
    name: row.name || row.ticker,
    score: row.score || 0,
    price: row.price || 0,
    reasons: row.reasons && row.reasons.length ? row.reasons : ["Ranked by the backend factor model."],
    modelDecision: row.model_decision || row.modelDecision || "Research / consider staged buy",
  };
}

function mapSignal(row) {
  return {
    ticker: row.ticker,
    strategy: row.strategy || "Portfolio action engine",
    action: row.action || "HOLD",
    score: row.score ?? row.final_score ?? 0,
    status: row.status || "Active",
  };
}

function mapFactor(row) {
  return {
    factorName: row.factor_name || row.factorName,
    icValue: row.ic_value ?? row.icValue ?? 0,
    universeSize: row.universe_size ?? row.universeSize ?? 0,
    status: row.status || "Active",
  };
}
