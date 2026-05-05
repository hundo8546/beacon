export const demoHoldings = [
  {
    ticker: "MU",
    action: "HOLD / DO NOT ADD, POSITION IS CONCENTRATED",
    portfolioWeight: 0.31,
    marketValue: 18540,
    unrealizedGain: 0.42,
    finalScore: 0.7,
    sector: "Technology",
  },
  {
    ticker: "NVDA",
    action: "HOLD / ADD ONLY IF UNDERWEIGHT",
    portfolioWeight: 0.18,
    marketValue: 10760,
    unrealizedGain: 0.36,
    finalScore: 0.47,
    sector: "Technology",
  },
  {
    ticker: "TSM",
    action: "HOLD / ADD ONLY IF UNDERWEIGHT",
    portfolioWeight: 0.15,
    marketValue: 9020,
    unrealizedGain: 0.21,
    finalScore: 0.7,
    sector: "Technology",
  },
  {
    ticker: "MSFT",
    action: "HOLD",
    portfolioWeight: 0.12,
    marketValue: 7180,
    unrealizedGain: 0.14,
    finalScore: 0.0,
    sector: "Technology",
  },
  {
    ticker: "AVGO",
    action: "HOLD / ADD ONLY IF UNDERWEIGHT",
    portfolioWeight: 0.09,
    marketValue: 5380,
    unrealizedGain: 0.18,
    finalScore: 0.47,
    sector: "Technology",
  },
  {
    ticker: "GOOGL",
    action: "HOLD / ADD ONLY IF UNDERWEIGHT",
    portfolioWeight: 0.08,
    marketValue: 4760,
    unrealizedGain: 0.11,
    finalScore: 0.7,
    sector: "Communication Services",
  },
  {
    ticker: "SPY",
    action: "HOLD",
    portfolioWeight: 0.07,
    marketValue: 4180,
    unrealizedGain: 0.08,
    finalScore: 0.23,
    sector: "Index",
  },
];

export const demoAnalysisRun = {
  id: "demo-run",
  portfolioValue: 59820,
  accountEquity: 62500,
  todayChange: 720,
  todayChangePct: 0.012,
  riskSummary: "Concentrated growth",
  plainEnglishSummary:
    "The portfolio is profitable but semiconductor exposure is carrying most of the risk. Avoid adding to MU and NVDA until weights decline; use new cash in staged entries across lower-correlation candidates.",
  investmentPlan: "Use a three-step deployment plan unless concentration falls below 20%.",
  status: "complete",
};

export const demoBuyIdeas = [
  {
    ticker: "COST",
    name: "Costco Wholesale",
    score: 0.82,
    price: 742,
    reasons: ["Defensive growth profile with strong earnings quality.", "Lower direct correlation to semiconductor winners."],
    modelDecision: "Research / consider staged buy",
  },
  {
    ticker: "LLY",
    name: "Eli Lilly",
    score: 0.78,
    price: 811,
    reasons: ["Quality and revenue growth screen remain strong.", "Healthcare exposure diversifies the current technology-heavy account."],
    modelDecision: "Research / consider staged buy",
  },
  {
    ticker: "JPM",
    name: "JPMorgan Chase",
    score: 0.66,
    price: 219,
    reasons: ["Financial exposure helps reduce single-sector risk.", "Trend remains constructive versus the broad market."],
    modelDecision: "Watch / staged entry",
  },
  {
    ticker: "AMZN",
    name: "Amazon",
    score: 0.61,
    price: 184,
    reasons: ["Momentum is positive, but mega-cap exposure overlaps with current growth tilt.", "Use only if existing tech weights are controlled."],
    modelDecision: "Watch / staged entry",
  },
  {
    ticker: "VTI",
    name: "Vanguard Total Stock Market",
    score: 0.58,
    price: 287,
    reasons: ["Broad market anchor reduces single-name decision risk.", "Useful for conservative staged deployment."],
    modelDecision: "Research / consider staged buy",
  },
];

export const demoFactorIc = [
  { factorName: "momentum_12_1", icValue: 0.2, universeSize: 4, status: "Active" },
  { factorName: "momentum_6_1", icValue: -0.6, universeSize: 4, status: "Active" },
  { factorName: "price_acceleration", icValue: 0.8, universeSize: 4, status: "Active" },
  { factorName: "mean_reversion_5d", icValue: 1.0, universeSize: 4, status: "Active" },
  { factorName: "rsi_reversal", icValue: 0.8, universeSize: 4, status: "Active" },
  { factorName: "vol_adj_mean_reversion", icValue: 0.8, universeSize: 4, status: "Active" },
  { factorName: "idiosyncratic_vol", icValue: 0.8, universeSize: 4, status: "Active" },
];

export const demoSignals = [
  { ticker: "MSFT", strategy: "Portfolio action engine", action: "HOLD", score: 0, status: "Active" },
  { ticker: "TSM", strategy: "Portfolio action engine", action: "HOLD / ADD ONLY IF UNDERWEIGHT", score: 0.7, status: "Active" },
  { ticker: "MU", strategy: "Portfolio action engine", action: "HOLD / DO NOT ADD, POSITION IS CONCENTRATED", score: 0.7, status: "Active" },
  { ticker: "NVDA", strategy: "Portfolio action engine", action: "HOLD / ADD ONLY IF UNDERWEIGHT", score: 0.47, status: "Active" },
  { ticker: "SPY", strategy: "Portfolio action engine", action: "HOLD", score: 0.23, status: "Active" },
  { ticker: "AVGO", strategy: "Portfolio action engine", action: "HOLD / ADD ONLY IF UNDERWEIGHT", score: 0.47, status: "Active" },
  { ticker: "GOOGL", strategy: "Portfolio action engine", action: "HOLD / ADD ONLY IF UNDERWEIGHT", score: 0.7, status: "Active" },
];

export const demoStrategyPlan = {
  deploymentMode: "Balanced three-step buy",
  schedule: [
    { interval: "Today", amount: 4080 },
    { interval: "In 1 week", amount: 3960 },
    { interval: "In 2 weeks", amount: 3960 },
  ],
};
