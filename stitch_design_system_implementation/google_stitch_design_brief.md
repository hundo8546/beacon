# SignalPilot Google Stitch Design Brief

Use this prompt in Google Stitch to design a production-quality frontend for SignalPilot.

## Product Name

SignalPilot

## One-Line Description

SignalPilot helps investors turn connected brokerage data into clear portfolio actions, risk insights, and staged investment plans.

## Current Tech Stack

- Prototype frontend: Streamlit
- Backend logic: Python
- Charts: Plotly
- Broker integrations: Robinhood via `robin_stocks`; Fidelity planned via `fidelity-api`
- Market data: Yahoo Finance through `yfinance`
- News: NewsAPI plus Google News RSS fallback
- AI: OpenAI Responses API
- Planned production backend: Firebase Auth, Firestore, Cloud Functions or Cloud Run, Secret Manager

## Target Users

Retail investors who hold concentrated positions, want better portfolio discipline, and need a simple view of what to review, what to avoid adding to, and how to deploy new cash over time.

## Design Style

Clean, modern, calm, and financial. Avoid a flashy trading-app feel. The product should feel like a private wealth dashboard, not a casino or social trading feed.

Use:

- navy, slate, blue, and soft green accents
- high-contrast cards
- compact but readable layouts
- clear status badges
- simple explanations under charts
- responsive design for desktop and tablet

Avoid:

- white cards on white backgrounds
- crypto-style neon palettes
- oversized marketing hero sections inside the app
- dense raw tables as the main UI
- confusing quant jargon on first view

## App Structure

### Top Navigation

- SignalPilot logo
- Dashboard
- Portfolio
- Strategy
- Ideas
- Research
- Profile avatar in top right

### Home / Dashboard

Purpose: give the user immediate clarity.

Sections:

- Hero summary card with portfolio value, today change, concentration warning, and last sync time
- “What to review today” action cards
- Plain-English AI summary
- New cash deployment plan preview
- Risk snapshot
- Top buy ideas

### Portfolio Page

Purpose: show holdings and risk without overwhelming the user.

Sections:

- Position-size pie chart
- Sector exposure chart
- Correlation heatmap
- Unrealized gain chart
- Action mix chart
- Clean holdings table as secondary detail
- Tax impact estimator in a panel

### Investment Strategy Page

Purpose: answer “I have $X to invest. What should I do?”

Inputs:

- Cash available
- Risk style: Conservative, Balanced, Aggressive
- Time horizon
- Include existing holdings toggle

Outputs:

- Staged deployment schedule: Today, next week, later intervals
- Allocation cards by ticker
- Why each pick made the list
- News articles with links
- Expert/analyst context panel
- Risks before investing

### Alpha Explorer Page

Purpose: show which signals are currently useful.

Sections:

- Factor IC bar chart
- Active versus decayed factor badges
- Rolling IC line chart
- Short explanation of what IC means
- Factor details in expandable drill-down

### Backtester Page

Purpose: let users sanity-check a strategy.

Controls:

- Strategy dropdown
- Universe dropdown
- Lookback dropdown

Outputs:

- Total return
- Sharpe ratio
- Max drawdown
- Monthly win rate
- Cumulative return line chart
- Monthly heatmap with plain-English analysis

Important UX requirement: changing backtester controls should not rerun the whole portfolio sync.

### LLM Sentiment Page

Purpose: explain current news context in a human-readable way.

Sections:

- Sentiment cards by ticker
- Confidence score
- Key signals
- Risk flags
- Source note showing whether live headlines or fallback context were used
- Raw table hidden in an expandable details area

### Strategy Monitor Page

Purpose: show what type of strategy is driving the portfolio.

Sections:

- Strategy cards
- Active strategy count
- Net long exposure proxy
- Risk attribution pie chart
- Average signal bar chart
- Recent signals hidden in expandable details
- Plain-English explanation of what the numbers mean

### Profile Page

Purpose: manage account and broker connections.

Sections:

- User profile card
- Connected broker cards
- Add broker button
- Robinhood connection status
- Fidelity connection status
- Security status
- Last sync timestamps

Broker connection flow:

- User signs into SignalPilot
- User chooses broker
- User enters broker credentials in secure flow
- App handles MFA
- App stores encrypted secret references server-side
- App imports holdings read-only

## Component Guidance

Use cards for:

- action recommendations
- buy ideas
- strategy summary
- broker connections
- investment schedule

Use tables only for:

- holdings drill-down
- factor details
- recent signal log
- raw sentiment details

Use charts for:

- allocation
- sector exposure
- correlation
- returns
- risk attribution
- factor strength

Every chart should have a one-sentence interpretation below it.

## Copy Style

Use short, direct, plain-English copy. Avoid formal filler and quant jargon. Explain terms simply.

Examples:

- “This position is large enough to drive your whole portfolio.”
- “A higher score means the idea has stronger trend, quality, and valuation support.”
- “This backtest is weak because returns were low and drawdowns were high.”
- “Split buys reduce the risk of investing everything on one bad day.”

## Required Screens

Create designs for:

1. Logged-out landing page
2. Dashboard home
3. Portfolio risk page
4. Investment strategy page
5. Buy ideas page
6. LLM sentiment page
7. Profile and broker connections page
8. Add broker flow with MFA state

## Responsive Behavior

Desktop:

- top nav
- 3 to 4 cards per row
- charts in two-column layouts

Tablet:

- 2 cards per row
- charts stacked when needed

Mobile:

- single-column cards
- hide dense tables behind expanders
- keep primary action visible

## Accessibility

- high contrast text
- no color-only status communication
- clear labels
- keyboard-friendly forms
- readable chart labels

## Final Output Request

Generate a clean fintech dashboard UI concept for SignalPilot with reusable components, page layouts, color palette, typography, spacing, and interaction states.
