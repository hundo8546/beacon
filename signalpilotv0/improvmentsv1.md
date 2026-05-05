# Streamlit Dashboard Enhancements (Portfolio AI)

This document adds high-impact features to your existing Streamlit app. The focus is **decision quality**, not just visuals. Each section includes what to show, why it matters, and minimal implementation guidance.

---

## 1) Executive Summary (Top Card)

**What to show**

* Total portfolio value, P&L (realized/unrealized)
* Today change vs. total return
* Top 3 contributors (by $ gain)
* Concentration risk (largest position %)

**Why**
Gives a one-glance status and highlights concentration immediately.

**Implementation**

* Aggregate from your positions dict
* Use `st.metric` + a small bar chart of top contributors

---

## 2) Decision Table (Core Panel)

**Columns**

* Ticker
* Weight %
* Avg Cost | Price | P&L %
* Signal Score (quant)
* Sentiment Score (LLM)
* Earnings proximity (days)
* Suggested Action (HOLD / TRIM 5% / TRIM 10%)

**Why**
Becomes your **single source of truth** for actions.

**Implementation**

* `st.dataframe` with color scales (green/red)
* Add a column `action` from your rule engine

---

## 3) Risk Panel (Do-not-skip)

**What to show**

* Position concentration (top 5 weights)
* Scenario: portfolio impact if a top holding drops 20/30/40%
* Rolling volatility (30d) per position

**Why**
Prevents givebacks from a single winner (e.g., semis concentration).

**Implementation (scenario)**

```python
import pandas as pd

def scenario_impact(positions, shock_ticker, drop_pct):
    before = sum(p['quantity']*p['price'] for p in positions.values())
    after = 0
    for t, p in positions.items():
        price = p['price'] * (1 - drop_pct) if t == shock_ticker else p['price']
        after += p['quantity'] * price
    return (after - before) / before
```

* Render a small table for drops: 20%, 30%, 40%

---

## 4) Tax Impact Panel (Action-aware)

**What to show**

* For a chosen ticker + trim %:

  * Estimated proceeds
  * Cost basis sold
  * Taxable gain (LT/ST)
  * Estimated tax (federal + state)
  * Net reinvestable

**Why**
Answers: “Is selling now worth it?”

**Implementation**

* Add inputs: ticker dropdown, trim % slider
* Use your existing tax model; display outputs via `st.metric`

---

## 5) Momentum & Trend Panel

**What to show**

* 3m / 6m returns
* Relative strength vs S&P (SPY)
* Drawdown from recent peak

**Why**
Helps avoid trimming strong trends too early and flags fading momentum.

**Implementation**

```python
import yfinance as yf

def momentum(ticker):
    h = yf.Ticker(ticker).history(period='6mo')['Close']
    m3 = h.iloc[-1]/h.iloc[-63] - 1
    m6 = h.iloc[-1]/h.iloc[0] - 1
    peak = h.max()
    dd = h.iloc[-1]/peak - 1
    return m3, m6, dd
```

---

## 6) News + LLM Sentiment Panel

**What to show**

* Top 5 headlines per ticker
* LLM sentiment score (-1 to 1)
* Confidence (0–1)
* Key risks (bullets)
* 1–2 line summary

**Why**
Context-aware interpretation beats keyword sentiment.

**Implementation (LLM scoring)**

```python
from openai import OpenAI
client = OpenAI()

SCHEMA = {
  "type": "object",
  "properties": {
    "overall_sentiment": {"type": "number"},
    "confidence": {"type": "number"},
    "key_risks": {"type": "array", "items": {"type": "string"}},
    "summary": {"type": "string"}
  },
  "required": ["overall_sentiment","confidence","key_risks","summary"]
}

def llm_sentiment(headlines):
    prompt = f"Analyze sentiment of these financial headlines and return JSON only: {headlines}"
    resp = client.responses.create(
        model="gpt-5",
        input=prompt,
        response_format={"type":"json_schema","json_schema": SCHEMA}
    )
    return resp.output[0].content[0].text
```

* Cache results with `st.cache_data(ttl=900)` to control costs

---

## 7) Earnings Proximity & Event Risk

**What to show**

* Next earnings date
* Days to earnings
* Flag if < 10 days

**Why**
Large moves cluster around earnings; adjust trim aggressiveness.

**Implementation**

* Pull via `yfinance.Ticker(t).calendar` or `earnings_dates`

---

## 8) Action Engine (Combine signals)

**Inputs**

* Quant signal (analyst + momentum + price/target)
* LLM sentiment
* Earnings proximity

**Scoring**

```python
def final_score(quant, sentiment, days_to_earnings):
    score = 0.6*quant + 0.4*sentiment
    if days_to_earnings is not None and days_to_earnings < 10:
        score -= 0.5  # de-risk near earnings
    return score


def decide_action(ticker, score):
    if score >= 1.5:
        return "HOLD"
    elif score >= 0.5:
        return "TRIM 5%"
    else:
        return "TRIM 10%"
```

---

## 9) “What Should I Do Today?” Card

**What to show**

* Top 1–2 actions across portfolio (highest urgency)
* Rationale (1–2 bullets): overextended vs target, negative sentiment, earnings risk

**Why**
Converts data into **clear next steps**.

**Implementation**

* Rank by lowest final score * weight * unrealized gain

---

## 10) Scenario Simulator (Interactive)

**What to show**

* Sliders for shocks (e.g., MU -30%, NVDA -20%)
* Portfolio impact and new weights

**Why**
Stress-tests concentration risk before it happens.

**Implementation**

* Use the `scenario_impact` function with multiple shocks

---

## 11) Position Decay Tracker

**What to show**

* Peak-to-current drawdown
* Momentum rollover (3m decreasing while price near highs)

**Why**
Identifies when a winner is losing steam.

---

## 12) Caching & Performance

* `@st.cache_data` for market/news/LLM (ttl 10–30 min)
* Batch API calls (yfinance multi-ticker where possible)
* Rate-limit NewsAPI calls

---

## 13) UI Layout (Suggested)

```
[ Executive Summary ]

[ Risk Panel ]      [ Tax Panel ]

[ Decision Table ]

[ Momentum & Trends ]

[ News + Sentiment ]

[ What Should I Do Today? ]
```

---

## 14) Guardrails

* Do not auto-trade via Robinhood APIs (read-only only)
* Log all suggested actions with timestamp
* Keep manual confirmation step

---

## 15) Future Upgrades

* Backtesting your action rules (paper trade)
* Regime detection (bull / correction) to scale trimming
* Move to a broker with official API (e.g., Alpaca) for optional automation

---

## Key Outcome

This upgrade turns your app into a **decision engine** that:

* Quantifies risk
* Incorporates real-time sentiment
* Produces tax-aware actions
* Reduces emotional decisions
