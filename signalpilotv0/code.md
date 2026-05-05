# Smart Portfolio Management System (Robinhood + Python)

## Overview

This document defines a hybrid investment system that combines:

* Portfolio data from Robinhood (read-only)
* Market data (prices, fundamentals)
* News + sentiment
* Rule-based decision engine

Goal:

> Make tax-aware, data-driven decisions on when to trim or hold positions (especially concentrated winners like MU)

---

## System Architecture

```
Robinhood API (read-only)
        ↓
Portfolio Positions (avg cost, qty)
        ↓
Market Data (yfinance)
        ↓
News + Analyst Data (NewsAPI / Yahoo)
        ↓
Signal Engine
        ↓
Action Output (SELL / HOLD / TRIM)
```

---

## Step 1: Robinhood Data Extraction (Read-Only)

### Install

```
pip install robin-stocks
```

### Code

```python
import robin_stocks.robinhood as rh

USERNAME = "your_email"
PASSWORD = "your_password"

rh.login(USERNAME, PASSWORD)

holdings = rh.account.build_holdings()

portfolio = {}

for symbol, data in holdings.items():
    portfolio[symbol] = {
        "quantity": float(data["quantity"]),
        "avg_cost": float(data["average_buy_price"]),
        "price": float(data["price"])
    }

print(portfolio)
```

---

## Step 2: Market + Fundamental Data

### Install

```
pip install yfinance
```

### Code

```python
import yfinance as yf

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)

    info = stock.info
    hist = stock.history(period="3mo")

    return {
        "price": info.get("currentPrice"),
        "target_price": info.get("targetMeanPrice"),
        "recommendation": info.get("recommendationKey"),
        "momentum_3m": (hist["Close"][-1] / hist["Close"][0]) - 1
    }
```

---

## Step 3: News Data

### Install

```
pip install requests
```

### Code

```python
import requests

NEWS_API_KEY = "your_api_key"


def get_news(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    res = requests.get(url).json()

    articles = []
    for a in res.get("articles", [])[:5]:
        articles.append(a["title"])

    return articles
```

---

## Step 4: Signal Engine

### Logic

* Analyst rating
* Momentum
* Price vs target

### Code

```python
def build_signal(stock_data):
    score = 0

    if stock_data["recommendation"] in ["buy", "strong_buy"]:
        score += 1
    elif stock_data["recommendation"] == "sell":
        score -= 1

    if stock_data["momentum_3m"] > 0.2:
        score += 1
    elif stock_data["momentum_3m"] < -0.1:
        score -= 1

    if stock_data["target_price"]:
        if stock_data["price"] > stock_data["target_price"]:
            score -= 1
        else:
            score += 1

    return score
```

---

## Step 5: More Exact Signal + Buy-Idea Engine

The working implementation now lives in:

* `portfolio_bot.py` - CLI portfolio analysis and live buy-idea ranking
* `app.py` - Streamlit UI
* `credentials.md` - local credential template
* `requirements.txt` - dependencies

The new engine keeps the original `decide_action()` idea, but makes it more exact by scoring:

* 12-minus-1 month momentum and 6 month trend
* Price relative to 50/200 day moving averages
* Proximity to 52 week high
* Realized volatility and drawdown penalty
* ROE, profit margin, revenue growth, and forward P/E
* Analyst target gap and consensus rating
* Optional current news sentiment using NewsAPI

This is inspired by recent quant research emphasizing momentum, quality/profitability filters, non-linear factor scoring, and volatility-managed exposure. It intentionally avoids fully automated trading.

### Run CLI

```bash
pip install -r requirements.txt
python portfolio_bot.py
python portfolio_bot.py --watchlist MSFT,NVDA,AVGO,GOOGL,AMZN,TSM,QQQ --limit 5
python portfolio_bot.py --use-robinhood
```

### Run UI

```bash
streamlit run app.py
```

### Updated `decide_action`

```python
def decide_action(ticker, signal, unrealized_gain=None):
    ticker = ticker.upper()
    if signal >= 2:
        return "HOLD / ADD ONLY IF UNDERWEIGHT"
    if signal == 1:
        return "HOLD"
    if ticker == "MU":
        if unrealized_gain is not None and unrealized_gain > 0.25:
            return "TRIM 5-10% OF MU"
        return "HOLD MU, DO NOT ADD"
    if signal <= -1:
        return "REVIEW / TRIM WEAK POSITION"
    return "HOLD"
```

### Credentials Needed

See `credentials.md`.

* `NEWS_API_KEY` - optional, for current headlines and sentiment.
* `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD` - optional, only if importing Robinhood holdings.
* `ROBINHOOD_MFA_CODE` - optional, current one-time MFA code if Robinhood asks for it.
* `MANUAL_HOLDINGS` - optional fallback, formatted as `MU:10:88.50,NVDA:2:650.00`.

The script uses current Yahoo Finance market data through `yfinance` when executed, so the buy candidates update at runtime.

---

## Original Step 5: Tax-Aware MU Exit Strategy

### Strategy

* Sell gradually (10–20% per period)
* Prefer long-term shares
* Offset gains with losses

### Code

```python
def decide_action(ticker, signal):
    if ticker == "MU":
        if signal >= 2:
            return "HOLD"
        elif signal == 1:
            return "TRIM 5%"
        else:
            return "TRIM 10%"

    return "HOLD"
```

---

## Step 6: Full Pipeline

```python
results = []

for ticker in portfolio:
    market_data = get_stock_data(ticker)
    signal = build_signal(market_data)
    news = get_news(ticker)
    action = decide_action(ticker, signal)

    results.append({
        "ticker": ticker,
        "signal": signal,
        "action": action,
        "news": news
    })

for r in results:
    print("\n===", r["ticker"], "===")
    print("Signal:", r["signal"])
    print("Action:", r["action"])
    print("News:")
    for n in r["news"]:
        print("-", n)
```

---

## Step 7: Advanced Improvements

### 1. Sentiment Analysis

* Use FinBERT or LLM scoring on news

### 2. Earnings Awareness

```python
if days_to_earnings < 10:
    reduce_position = True
```

### 3. Volatility-Based Selling

```python
if momentum > 0.5:
    trim_more = True
```

### 4. Loss Harvesting

* Sell losing positions (AMD, ASML)
* Offset MU gains

---

## Step 8: Output Example

```
=== MU ===
Signal: 1
Action: TRIM 5%
News:
- Micron beats earnings expectations
- AI demand driving memory surge
```

---

## Future Upgrade Path

### Short-Term

* CLI tool
* Daily execution

### Mid-Term

* Streamlit dashboard

### Long-Term

* Move to Alpaca
* Full automation

---

## Key Takeaways

* Do not automate trades on Robinhood
* Use it as a data source only
* Combine quant + discretionary signals
* Focus on risk management, not just returns

---

## Final Insight

This system converts:

> Concentrated gains → structured decision making

Instead of reacting emotionally, you now:

* Measure
* Evaluate
* Act systematically
