# Beacon Python Backend

This directory contains Beacon's Python analysis engine, local API, Streamlit dashboard, and CLI. The directory is still named `signalpilotv0/` from the earlier SignalPilot name.

Beacon is a read-only decision-support app for reviewing a portfolio, ranking potential buy ideas, and surfacing risk. It does not place trades.

## Current Components

- `api.py`: local `Beacon API` used by the React app.
- `portfolio_bot.py`: portfolio engine, Robinhood auth, market data, scoring, CLI, backtester, OpenAI integration, and logging.
- `app.py`: legacy Streamlit dashboard for the original local workflow.
- `credentials.example.md`: safe credentials template.
- `credentials.md`: private local credentials file. Keep private and do not commit.
- `requirements.txt`: Python dependencies.
- `code.md`, `improvmentsv1.md`, `quantimprovements.md`: design notes and improvement plans.

## Backend Responsibilities

The backend turns raw portfolio and market inputs into structured analysis for Beacon. It can import Robinhood holdings, read manual holdings, fetch market history, pull fundamentals, collect headline context, score holdings, rank candidate tickers, compute factor snapshots, run simple strategy monitoring, and return JSON for the React dashboard.

Robinhood support is read-only. The backend uses `robin_stocks` to load holdings and account totals. It uses Robinhood account values when available so portfolio weight and market value match the brokerage view instead of being reconstructed from delayed market prices.

Manual holdings are supported through `MANUAL_HOLDINGS`. This is useful for local testing, demo workflows, and cases where the user does not want to connect a broker.

Market data comes mainly from `yfinance`. The backend uses it for price history, trend fields, drawdown, volatility, fundamentals, analyst target gap, and candidate scoring. News context can come from NewsAPI when configured, with RSS fallback behavior in the portfolio engine.

OpenAI is optional. When `OPENAI_API_KEY` is configured and OpenAI analysis is enabled, the backend sends one consolidated prompt with holdings, metrics, available headlines, buy ideas, and strategy state. The response is used as context, not as an automatic trading decision.

## API Endpoints

Start the API from the repository root:

```bash
python3 signalpilotv0/api.py 8787
```

Available local endpoints:

- `GET /api/health`: returns API health and service name.
- `POST /api/analyze`: runs portfolio analysis for the React dashboard.
- `POST /api/security`: looks up a ticker, ETF, or fund with price history, factor snapshot, score, and reasons.
- `POST /api/connect-broker`: validates local broker credentials and returns broker metadata.
- `POST /api/backtest`: runs a strategy backtest for a supplied universe.

The local API binds to `127.0.0.1`. CORS is permissive so the local React app can call it during development. Restrict CORS before deploying any hosted backend.

## Portfolio Analysis Flow

`POST /api/analyze` starts by loading the private credentials file and any credential payload sent by the frontend. If Robinhood is enabled, it removes saved Robinhood fields from the credentials file and uses the active broker credential payload. This avoids silently falling back to old broker credentials.

The analysis flow then loads holdings, loads account totals when available, builds a dynamic candidate universe, analyzes holdings, ranks buy ideas, computes factor snapshots, builds strategy monitor output, and creates a summary. If OpenAI is enabled, it adds a consolidated plain-English portfolio analysis.

The response includes holdings, holdings report, account totals, portfolio summary, action cards, dynamic universe, watchlist, buy ideas, factor data, strategy monitor output, and optional master analysis.

## Security Lookup Flow

`POST /api/security` accepts a ticker-like symbol. It loads a market snapshot, computes a score, creates a signal label, builds plain-English reasons, and returns recent price history points. The React search screen uses this payload for factor tiles, score display, reasons, headlines, and price chart data.

## Setup

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create your private credentials file from the template:

```bash
cp credentials.example.md credentials.md
```

Then edit `credentials.md`:

```text
NEWS_API_KEY=your_newsapi_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

ROBINHOOD_USERNAME=your_robinhood_email_or_username
ROBINHOOD_PASSWORD=your_robinhood_password
ROBINHOOD_MFA_CODE=replace_with_current_mfa_code
ROBINHOOD_TOTP_SECRET=replace_with_authenticator_secret
ROBINHOOD_SESSION_DIR=.robinhood_tokens

MANUAL_HOLDINGS=MU:10:88.50,NVDA:2:650.00
```

Only Robinhood credentials are required for Robinhood portfolio import. `NEWS_API_KEY` and `OPENAI_API_KEY` are optional. `MANUAL_HOLDINGS` can be used without broker login.

Do not commit or share `credentials.md`. It is ignored by the root `.gitignore`.

## Robinhood Authentication

Test Robinhood login:

```bash
python3 portfolio_bot.py --test-robinhood-login
```

If Robinhood asks for MFA, put the fresh 6-digit code in:

```text
ROBINHOOD_MFA_CODE=123456
```

Then rerun immediately.

If using an authenticator app setup secret, put the reusable secret in:

```text
ROBINHOOD_TOTP_SECRET=YOUR_SECRET
```

The app will generate the current MFA code with `pyotp`.

## CLI Usage

Run with Robinhood holdings:

```bash
python3 portfolio_bot.py --use-robinhood
```

Run with OpenAI headline sentiment:

```bash
python3 portfolio_bot.py --use-robinhood --use-openai
```

Run with optional extra candidate tickers:

```bash
python3 portfolio_bot.py --use-robinhood --extra-tickers AAPL,AMZN,COST,JPM,LLY --limit 5
```

By default, owned tickers are excluded from new buy ideas. Include them with:

```bash
python3 portfolio_bot.py --use-robinhood --include-owned-ideas
```

## Streamlit UI

Start the legacy dashboard:

```bash
streamlit run app.py
```

If the default port is busy:

```bash
streamlit run app.py --server.port 8502
```

The Streamlit UI includes portfolio summary, current holdings, concentration risk, scenario impact, tax estimates, alpha factor research, strategy backtests, LLM sentiment, strategy monitor, buy ideas, and logs.

## Generated Files

Runtime artifacts are intentionally ignored by Git:

- `portfolio_bot.log`
- `factor_ic_log.csv`
- `signals_log.csv`
- `__pycache__/`
- `.robinhood_tokens/`

## Guardrails

- Beacon is for educational decision support.
- It does not place trades.
- Robinhood usage is read-only.
- Suggested actions require manual review.
- Tax estimates are simplified and should not be treated as tax advice.
- Market data may be delayed, incomplete, or rate-limited.
- OpenAI analysis is based on supplied portfolio, metrics, and headline context and should not be treated as a trading signal by itself.

## Production Work Remaining

The backend is still a local development service. Production work should include a hosted API, restricted CORS, server-side broker authorization, encrypted secret storage, request authentication, structured logging, retry and timeout policies, automated tests, CI, and clear data retention rules.
