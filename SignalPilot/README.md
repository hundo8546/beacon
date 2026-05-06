# Beacon React UI

This directory contains the Beacon frontend. The folder is still named `SignalPilot/` from an earlier project name, but the app shown to users is Beacon.

## Role In The App

The frontend is the main Beacon experience. It handles public pages, authentication, dashboard navigation, data subscriptions, holdings import, local API calls, and chart-like visualizations built in React and CSS.

The app can run in several states. It can show demo data when Firebase has no portfolio data. It can subscribe to Firestore after sign-in. It can call the local Python API for live analysis and ticker search. This makes the interface useful during setup instead of failing into an empty screen.

## Main Screens

The public area includes the Beacon home page, login page, pricing page, privacy page, and security page. These screens explain the local build, read-only posture, and account model.

The authenticated app has these sections:

- `Dashboard`: upload-first holdings import, portfolio value, position count, concentration state, cash proxy, review actions, portfolio trend, risk snapshot, buy ideas, and PDF save action.
- `Portfolio`: holdings, action labels, position weights, unrealized gain, scenario impact, tax estimate, and action mix.
- `Strategy`: cash deployment controls, risk style, include-owned toggle, allocation schedule, target allocation, and exit/tax plan.
- `Ideas`: ranked buy candidates with score, price, reasons, and model decision text.
- `Research`: factor IC snapshot, strategy monitor, market sentiment summary, and ranked research context.
- `Sentiment`: Beacon intelligence summary, candidate context, and risk signals.
- `Search`: ticker, ETF, or fund lookup through the Python backend.
- `Profile`: Firebase profile, risk preference, tax rate, and saved import history.
- `Import`: CSV/XLSX holdings upload as the primary workflow.

## Data Sources

`src/services/demoData.js` provides the fallback data used when the app has no live portfolio yet.

`src/services/firebase.js` initializes Firebase, handles auth, creates user profiles, subscribes to Firestore data, seeds demo data, saves plans, saves settings, and writes imported analysis history.

`src/services/backend.js` calls the local Python API and maps backend response fields into frontend objects. It uses `VITE_SIGNALPILOT_API_URL` when set and falls back to `http://127.0.0.1:8787`.

The upload workflow posts multipart form data to `/api/import-holdings`. The backend returns the same analysis shape used by the rest of the dashboard, so the UI refreshes as soon as parsing and analysis finish.

## Local Development

Run the Python backend API from the repository root:

```bash
python3 -m pip install -r signalpilotv0/requirements.txt
python3 signalpilotv0/api.py 8787
```

Run the React app from this folder in a second terminal:

```bash
npm install
cp .env.example .env.local
npm run dev -- --port 5173
```

Open `http://127.0.0.1:5173/`.

Fill `.env.local` with the Firebase web app config from Firebase Console when you want Firebase Auth and Firestore persistence. Without those values, Beacon skips Firebase setup and still runs in demo/backend mode.

Override the backend URL when needed:

```bash
VITE_SIGNALPILOT_API_URL=http://127.0.0.1:8787 npm run dev -- --port 5173
```

Upload a CSV or XLSX holdings export from the Dashboard or Connect screen. Beacon runs analysis immediately after upload. No separate dashboard "Run analysis" button is used for portfolio files.

## Build

```bash
npm run build
```

The generated `dist/` directory is ignored by Git. Rebuild it before Firebase Hosting deployment.

## Firebase

Firebase persistence uses Cloud Firestore. The app expects authenticated users to read and write under their own `users/{userId}` document tree.

Required local environment variables:

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MEASUREMENT_ID`

Deploy rules from the repository root:

```bash
firebase deploy --only firestore:rules
```

If Firebase Auth returns a 400 in the browser console, enable the selected sign-in provider in Firebase Console. The local backend analysis flow can still run without Firebase account data.

## Security Note

Do not put brokerage credentials, API keys, or private Firebase service credentials in this frontend. The current Robinhood validation flow is for local development only. Production broker auth should be handled server-side with encrypted secret storage, limited retention, audit logs, and provider-specific consent flows.
