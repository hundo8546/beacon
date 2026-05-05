# Beacon

Beacon is a local-first portfolio intelligence app for people who want one place to review holdings, risk, research signals, buy ideas, and allocation plans before making their own decisions. The current product name is Beacon. Some folders still use the earlier SignalPilot name because they are part of the existing project structure.

Beacon is read-only. It does not place trades. It does not provide financial, investment, or tax advice. The app organizes data and model output so a user can review it with more context.

## Product Overview

Beacon has two main layers. The frontend is a React dashboard with Firebase authentication and Firestore persistence. The backend is a local Python service that reads portfolio inputs, pulls market data, scores holdings, ranks ideas, and returns structured analysis to the UI.

The React app is the primary user experience. It has a public home screen, login flow, authenticated dashboard, portfolio risk workspace, strategy planner, idea list, research panels, market sentiment screen, ticker search, profile view, and broker connection screen. It can run with demo data, Firestore data, backend data, or a mix of those states.

The Python backend is the analysis engine. It supports Robinhood import through `robin_stocks`, manual holdings through a credentials file, market data through `yfinance`, headline and RSS context, optional OpenAI analysis, factor scoring, strategy monitoring, and a simple backtest endpoint.

## Current Implementation

Beacon currently supports:

- Public pages for home, login, pricing, privacy, and security.
- Firebase Auth with anonymous test sign-in, email/password accounts, and phone sign-in.
- Firestore user profiles with preferences such as risk style, tax rate, subscription tier, and OpenAI enablement state.
- Firestore subcollections for broker metadata, holdings, analysis runs, actions, buy ideas, factor IC logs, strategy signals, and investment plans.
- A local `Beacon API` at `127.0.0.1:8787`.
- Portfolio analysis from connected Robinhood credentials or manual holdings.
- Dashboard fallback data so the UI still works before Firebase and backend setup are complete.
- Broker metadata storage in Firestore without saving raw broker passwords to Firestore.
- React views for dashboard, portfolio risk, strategy, ideas, research, sentiment, search, profile, and connect.
- Firebase Hosting config for the built frontend.
- Firestore rules that restrict `users/{userId}` documents and nested data to the authenticated owner.
- Legacy Streamlit and CLI workflows for the original local analysis engine.

## User Experience

The first screen presents Beacon as a portfolio signal engine. From there, a user can sign in, enter the app, and work through the dashboard. The authenticated app uses a compact sidebar and a topbar search so the user can move between portfolio review, strategy planning, and ticker research quickly.

The dashboard gives a current account summary with total portfolio value, position count, concentration state, cash proxy, review actions, trend chart, risk snapshot, and top buy ideas. When live data is missing, demo data fills the layout so the app remains usable during setup.

The portfolio view focuses on risk. It shows current holdings, action labels, position weights, unrealized gains, scenario impact, tax estimates, and action mix. This view is meant for reviewing concentration and downside exposure before adding or trimming positions.

The strategy view turns available cash and risk style into a staged plan. It shows allocation suggestions, deployment schedule, target allocation by ticker, and an exit strategy with simplified tax reserve estimates.

The research and sentiment areas show factor snapshots, strategy signals, headline context, candidate scores, and risk flags. The search view lets a user enter a ticker, ETF, or fund symbol and request a backend security lookup with price history, factor metrics, score, and reasons.

The connect view is for local broker validation and metadata. In the current local build, Robinhood credentials can be sent to the local API for validation. The app stores broker connection metadata in Firestore and keeps raw credentials out of Firestore. Production broker auth should move fully server-side with encrypted secret storage.

## Architecture

`SignalPilot/` contains the React application. It uses Vite, React 18, Firebase SDKs, Lucide icons, local CSS, and generated UI components. The app entry point is `SignalPilot/src/main.jsx`. Firebase setup lives in `SignalPilot/src/services/firebase.js`. Backend API calls and response mapping live in `SignalPilot/src/services/backend.js`. Demo portfolio data lives in `SignalPilot/src/services/demoData.js`.

`signalpilotv0/` contains the Python implementation. `api.py` exposes HTTP endpoints for the React app. `portfolio_bot.py` contains the portfolio model, market data fetchers, scoring logic, Robinhood access, OpenAI integration, backtester, and CLI. `app.py` contains the Streamlit dashboard.

Firebase Hosting serves `SignalPilot/dist` after `npm run build`. Firestore rules live at the repository root in `firestore.rules`. The Firebase project mapping is in `.firebaserc`.

## Repository Layout

- `SignalPilot/`: Beacon React + Vite frontend. The folder name is historical.
- `signalpilotv0/`: Python backend, Streamlit dashboard, CLI, and portfolio analysis engine.
- `firestore.rules`: Firestore user data access rules.
- `firebase.json`: Firebase Hosting and Firestore deployment config.
- `stitch_design_system_implementation/`: design references used while shaping the Beacon interface.
- `writingstandards.json`: writing style guide for project documentation.

## Data Flow

The frontend starts by checking Firebase Auth. If a user is signed in, it subscribes to Firestore user data and nested collections. If no Firestore data exists, the UI uses demo data.

When a user runs analysis, the frontend calls `POST /api/analyze` on the local Python API. The API loads credentials, imports Robinhood or manual holdings, builds a dynamic universe, analyzes holdings, ranks buy ideas, computes factor snapshots, builds strategy signals, and returns JSON. The frontend maps that payload into dashboard-friendly objects.

When a user searches a ticker, the frontend calls `POST /api/security`. The backend returns a market snapshot, price history points, score, signal label, and plain-English reasons. The UI renders those fields in the search workspace.

When a user connects a broker, the frontend calls `POST /api/connect-broker`. For Robinhood local testing, the backend can validate credentials and return account metadata. Firestore stores connection metadata, not raw broker passwords.

## Security And Secret Handling

Real credentials are intentionally excluded from Git. Use `signalpilotv0/credentials.example.md` as the template, then create your private local file:

```bash
cp signalpilotv0/credentials.example.md signalpilotv0/credentials.md
```

Ignored private and generated files include:

- `signalpilotv0/credentials.md`
- `.robinhood_tokens/`
- `node_modules/`
- `SignalPilot/dist/`
- `__pycache__/`
- `*.log`
- generated signal and factor CSV logs

Before pushing publicly, rotate any credential that has ever appeared in a local file you might have shared, copied, screenshotted, or committed. Firebase web config belongs in `SignalPilot/.env.local`, not in committed source. Firestore rules and enabled Auth providers still control access to user data.

## Local Setup

Install Python dependencies from the repository root:

```bash
python3 -m pip install -r signalpilotv0/requirements.txt
```

Install frontend dependencies:

```bash
cd SignalPilot
npm install
```

Create a local frontend environment file:

```bash
cp .env.example .env.local
```

Fill `SignalPilot/.env.local` with the Firebase web app config from Firebase Console. That file is ignored by Git.

## Run Beacon Locally

Start the Python API from the repository root:

```bash
python3 signalpilotv0/api.py 8787
```

Start the React app in a second terminal:

```bash
cd SignalPilot
npm run dev -- --port 5173
```

Open `http://127.0.0.1:5173/`.

The frontend calls `http://127.0.0.1:8787` by default. Override it when needed:

```bash
VITE_SIGNALPILOT_API_URL=http://127.0.0.1:8787 npm run dev -- --port 5173
```

Firebase is optional for basic demo/backend mode. If the `VITE_FIREBASE_*` values are missing, Beacon skips Firebase initialization and the app still renders local demo data.

## Python Tools

Run the Streamlit dashboard:

```bash
cd signalpilotv0
streamlit run app.py
```

Run the CLI report:

```bash
cd signalpilotv0
python3 portfolio_bot.py --use-robinhood
```

Use manual holdings instead of Robinhood by setting `MANUAL_HOLDINGS` in your private credentials file.

## Firebase Deployment

Build the frontend:

```bash
cd SignalPilot
npm run build
```

Deploy Firebase Hosting from the repository root:

```bash
firebase deploy --only hosting
```

Deploy Firestore rules:

```bash
firebase deploy --only firestore:rules
```

Enable the selected Firebase Auth providers in Firebase Console before using sign-in features.

## Development Status

Beacon is ready for local development, demo usage, and private beta hardening. It is not production-ready for broad public use yet. The main production work is broker credential architecture, CORS restrictions, server deployment, tests, CI, environment-specific Firebase config, stronger data validation, observability, and a legal review of financial and tax language.
