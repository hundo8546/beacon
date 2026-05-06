---
name: SignalPilot Design System
colors:
  surface: '#fcf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fcf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f5'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e4'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45464d'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fd'
  on-secondary-container: '#57657b'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#271901'
  on-tertiary-container: '#98805d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#fcf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e4'
  accent-blue: '#2563EB'
  accent-green: '#10B981'
  accent-slate: '#64748B'
  background-main: '#F8FAFC'
  surface-card: '#FFFFFF'
  status-positive: '#059669'
  status-warning: '#D97706'
  status-danger: '#DC2626'
  border-subtle: '#E2E8F0'
typography:
  h1:
    fontFamily: manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  h3:
    fontFamily: manrope
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  data-mono:
    fontFamily: monospace
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1280px
  gutter: 20px
---

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
