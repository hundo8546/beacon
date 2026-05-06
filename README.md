# Beacon - AI-Powered Portfolio Intelligence Platform

Beacon is a smart portfolio management tool that analyzes your investments, identifies risk patterns, ranks buying opportunities, and surfaces actionable insights. Built for investors who want to make informed decisions with complete visibility into their holdings.

## Why Beacon

**Smarter Decision Making**
Beacon transforms raw portfolio data into actionable intelligence. Upload your holdings and get immediate analysis of concentration risk, performance trends, and buying opportunities. No more spreadsheets or guesswork.

**Local-First Privacy**
Your data stays on your computer or in your own Firebase instance. Beacon is read-only and never places trades. You maintain complete control over sensitive financial information.

**Comprehensive Analysis**
Beacon analyzes your portfolio across multiple dimensions: risk concentration, unrealized gains, sector exposure, tax implications, and market sentiment. Each analysis includes clear reasoning so you understand why Beacon recommends specific actions.

**AI-Powered Insights**
Optional integration with OpenAI provides plain-English portfolio analysis and investment reasoning. Factor scoring reveals which investment themes are working in your portfolio.

**Strategy Planning**
Beacon generates staged deployment plans for cash, suggests allocation targets aligned with your risk tolerance, and estimates tax implications for rebalancing decisions.

## How Beacon Compares

| Feature | Beacon | Robinhood | E*TRADE | Fidelity Go | Betterment |
|---------|--------|-----------|---------|-------------|-----------|
| Holdings Analysis | Yes | Limited | Paid | Paid | Paid |
| Risk Concentration | Yes | No | No | No | No |
| Buy Idea Ranking | Yes | No | No | No | Limited |
| Strategy Planning | Yes | No | Limited | Limited | Yes |
| Factor Analysis | Yes | No | No | No | No |
| Local-First Option | Yes | No | No | No | No |
| Read-Only Mode | Yes | No | Yes | Yes | Yes |
| Free | Yes | Free brokerage | Free brokerage | Managed fee | 0.25% |

Beacon fills a gap between simple brokerage tools and expensive wealth management platforms. It's the analysis layer your portfolio has been missing.

## Key Features

**Smart Holdings Import**
Upload CSV or XLSX exports from any broker. Beacon automatically detects your brokerage format and normalizes holdings instantly.

**Risk Dashboard**
See your portfolio concentration at a glance. Beacon shows position weights, drawdown scenarios, sector exposure, and tax estimates for every holding.

**Buy Idea Engine**
Get ranked buying suggestions based on momentum, valuation, fundamentals, and analyst targets. Each suggestion includes clear reasoning.

**Strategy Planner**
Turn available cash into a deployment plan. Beacon suggests phased entry, target allocation, and exit strategies aligned with your risk level.

**Market Intelligence**
Access factor snapshots, strategy signal monitoring, headline context, and analyst sentiment for each holding in your portfolio.

**Ticker Lookup**
Search any stock, ETF, or fund to see price history, fundamental metrics, factor scores, and Beacon's assessment in seconds.

## Getting Started

### Quick Start (Demo Mode)

```bash
git clone https://github.com/yourusername/beacon.git
cd beacon/SignalPilot
npm install
npm run dev
```

Visit `http://127.0.0.1:5173` to see Beacon with sample data.

### Full Setup (With Backend Analysis)

Backend:
```bash
cd beacon
pip install -r signalpilotv0/requirements.txt
python3 signalpilotv0/api.py 8787
```

Frontend:
```bash
cd SignalPilot
npm install
npm run dev
```

### Production Deployment

See [HOSTING.md](HOSTING.md) for detailed instructions on deploying Beacon to Firebase Hosting, Cloud Run, Heroku, or your own server.

## How It Works

1. **Upload Holdings**: Export CSV or XLSX from your brokerage
2. **Instant Analysis**: Beacon analyzes your portfolio in seconds
3. **Get Insights**: Review risk, opportunities, and strategy recommendations
4. **Take Action**: Use insights to make informed portfolio decisions

Beacon connects a React frontend to a Python analysis engine:
- Frontend displays dashboards, research, and strategy tools
- Backend handles CSV parsing, market data fetching, scoring, and analysis
- Data syncs with optional Firebase for multi-device access

## What's Included

### Frontend Features
- Responsive dashboard with holdings summary
- Portfolio risk analysis with concentration metrics
- Strategy planner with allocation suggestions
- Buy idea ranker with scoring and reasons
- Ticker search with price history and fundamentals
- PDF export for offline review
- Multi-device sync via Firebase (optional)

### Backend Analysis
- Automatic brokerage format detection
- Market data from Yahoo Finance
- News and sentiment context
- Momentum, volatility, and valuation scoring
- Factor performance analysis
- Strategy signal monitoring
- Optional OpenAI portfolio summary

### Data Integration
- Direct Robinhood access (read-only, local testing)
- CSV/XLSX import from any broker
- Manual holdings entry for testing
- Multi-portfolio support with Firestore persistence

## Documentation

- [IMPLEMENTATION.md](IMPLEMENTATION.md): Technical architecture, features, and code overview
- [HOSTING.md](HOSTING.md): Production deployment guide for frontend, backend, and database
- [signalpilotv0/README.md](signalpilotv0/README.md): Python backend API reference
- [SignalPilot/README.md](SignalPilot/README.md): React frontend setup and components

## For Developers

### Project Structure

```
beacon/
├── SignalPilot/              # React frontend application
│   ├── src/
│   │   ├── components/       # UI components and pages
│   │   ├── services/         # Firebase, backend API, demo data
│   │   └── styles.css        # Application styles
│   ├── vite.config.js        # Frontend build config
│   └── package.json
│
├── signalpilotv0/            # Python backend analysis engine
│   ├── api.py                # HTTP server for React app
│   ├── portfolio_bot.py       # Analysis and scoring logic
│   ├── app.py                # Legacy Streamlit dashboard
│   └── requirements.txt
│
├── firestore.rules           # Firestore security rules
├── firebase.json             # Firebase deployment config
├── IMPLEMENTATION.md         # Technical documentation
├── HOSTING.md                # Deployment guide
└── README.md                 # This file
```

### Local Development

**Start the backend:**
```bash
cd beacon
python3 -m pip install -r signalpilotv0/requirements.txt
python3 signalpilotv0/api.py 8787
```

**In a new terminal, start the frontend:**
```bash
cd beacon/SignalPilot
npm install
npm run dev -- --port 5173
```

**Open** `http://127.0.0.1:5173` in your browser.

The frontend works in three modes:
- **Demo mode**: No backend or Firebase. Uses sample data.
- **Backend mode**: Connects to local Python API for analysis. No login required.
- **Full mode**: Uses Firebase Auth and Firestore. Enables multi-device sync.

### Configuration

**Frontend environment** (`.env.local` in `SignalPilot/`):
```
VITE_SIGNALPILOT_API_URL=http://127.0.0.1:8787
VITE_FIREBASE_API_KEY=<your-key>
VITE_FIREBASE_AUTH_DOMAIN=<your-domain>
VITE_FIREBASE_PROJECT_ID=<your-project>
```

**Backend environment** (`credentials.md` in `signalpilotv0/`):
```
NEWS_API_KEY=<your-newsapi-key>
OPENAI_API_KEY=<your-openai-key>
ROBINHOOD_USERNAME=<your-username>
ROBINHOOD_PASSWORD=<your-password>
```

All credentials are optional. Configure only what you need.

### Stack Overview

**Frontend**: React 18, Vite, Firebase Auth, Firestore, Lucide icons
**Backend**: Python 3.8+, yfinance, pandas, robin_stocks, OpenAI
**Database**: Firestore (optional)
**Hosting**: Firebase Hosting (frontend) + Cloud Run / Heroku / VPS (backend)

## Example Workflow

### 1. Upload Holdings
Export holdings from any broker as CSV or XLSX. Click "Import" and select your file.

### 2. View Analysis
Beacon shows:
- Portfolio composition and concentration
- Risk metrics and scenarios
- Unrealized gains and tax impact
- Top opportunities to research

### 3. Review Strategy
Get allocation suggestions for your cash based on your risk profile.

### 4. Research Ideas
See ranked buy candidates with factor analysis, analyst targets, and recent news.

### 5. Save and Share
Export analysis as PDF for offline review or sharing with advisors.

## Architecture Highlights

**Decoupled Services**: Frontend and backend communicate via REST API. Either component can be deployed independently.

**No Embedded Credentials**: Brokerage credentials never travel to the frontend. Robinhood support is for local testing only.

**Graceful Degradation**: Frontend works without backend (demo mode) or Firebase (backend mode).

**Firestore Optional**: All data can flow through the backend API. Firestore adds multi-device sync but is not required.

**Security First**: Firestore rules restrict data access. Raw uploaded files are deleted immediately after analysis.

## Security Note

Beacon is read-only and never places trades. It does not provide financial advice. Your data stays private:

- Raw uploaded CSV/XLSX files are temporary backend inputs
- Files are parsed, analyzed, and deleted immediately
- Firestore stores results only when you sign in
- Robinhood credentials are for local testing only
- Production deployments should not expose broker access

For detailed security information, see [IMPLEMENTATION.md](IMPLEMENTATION.md#security-model).

## Supported Brokers

Automatic format detection for:
- Robinhood
- Fidelity
- Charles Schwab
- E*TRADE
- Webull
- Interactive Brokers
- Generic CSV with ticker, quantity, and cost columns

## Limitations and Disclaimers

- Beacon is a portfolio analysis tool, not a financial advisor
- Market data is delayed and may not reflect real-time prices
- Factor scores are based on historical patterns and may not predict future performance
- Tax estimates are simplified and should be reviewed with a tax professional
- Beacon does not place trades and provides no automatic portfolio rebalancing
- Past performance does not guarantee future results

## Contributing

Bug reports and suggestions are welcome. To contribute:

1. Fork the repository
2. Create a feature branch
3. Test locally with both backend and frontend running
4. Submit a pull request with a description of changes

## License

Beacon is provided as-is for personal use. See LICENSE file for details.

## Support

For issues, questions, or feedback:
- Check existing documentation in IMPLEMENTATION.md and HOSTING.md
- Review logs: Frontend console, Python backend stdout, Firestore console
- Test in demo mode to isolate frontend vs backend issues
- Verify backend is running: `curl http://127.0.0.1:8787/api/health`

## Roadmap

Planned features:
- Real-time price streaming
- Advanced factor construction and scenario analysis
- Tax-loss harvesting optimization
- Mobile application
- Additional broker integrations
- Advanced backtesting engine
- Collaborative portfolio review with advisors

---

**The current product name is Beacon.** Some folders still use the earlier SignalPilot name because they are part of the existing project structure.
