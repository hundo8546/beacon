import logging
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from signalpilotv0.portfolio_bot import (
    alpha_factor_explorer,
    analyze_holdings,
    build_dynamic_universe,
    get_manual_portfolio,
    get_price_history,
    get_robinhood_account_totals,
    get_robinhood_portfolio,
    load_credentials,
    openai_master_analysis,
    portfolio_summary,
    rank_buy_ideas,
    run_backtest,
    scenario_impact,
    strategy_monitor,
    tax_estimate,
    today_actions,
)


APP_NAME = "SignalPilot"
TAGLINE = "Portfolio decisions without the spreadsheet haze."
CREDENTIALS_PATH = "credentials.md"

st.set_page_config(page_title=APP_NAME, layout="wide")
LOGGER = logging.getLogger("portfolio_bot.ui")

st.markdown(
    """
    <style>
    .sp-hero {
        padding: 1.25rem 1.5rem;
        border: 1px solid #1e3a8a;
        border-radius: 8px;
        background: #172554;
        margin-bottom: 1rem;
        color: #f8fafc;
    }
    .sp-card {
        padding: 1rem;
        border: 1px solid #1d4ed8;
        border-radius: 8px;
        background: #dbeafe;
        min-height: 132px;
        color: #0f172a;
        box-shadow: 0 1px 2px rgba(15, 23, 42, .06);
    }
    .sp-card h4 {
        margin: 0 0 .35rem 0;
        font-size: 1rem;
        color: #0f172a;
    }
    .sp-card p {
        margin: .2rem 0;
        color: #1e293b;
        font-size: .92rem;
    }
    .sp-pill {
        display: inline-block;
        padding: .15rem .45rem;
        border-radius: 999px;
        background: #eef2ff;
        color: #3730a3;
        font-size: .78rem;
        margin-bottom: .45rem;
    }
    .sp-note {
        padding: .85rem 1rem;
        border-left: 4px solid #2563eb;
        background: #eff6ff;
        color: #172554;
        border-radius: 6px;
        margin: .5rem 0 1rem 0;
    }
    .sp-muted {
        color: #dbeafe;
        font-size: .9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(APP_NAME)
st.caption(TAGLINE)

if "analysis" not in st.session_state:
    st.session_state.analysis = None


def dataframe_or_note(frame: pd.DataFrame, note: str) -> None:
    if frame.empty:
        st.write(note)
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)


def fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value * 100:.1f}%"


def fmt_money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"${value:,.0f}"


def tab_intro(title: str, body: str) -> None:
    st.subheader(title)
    st.caption(body)


def pie_chart(frame: pd.DataFrame, names: str, values: str, title: str) -> None:
    if frame.empty or names not in frame or values not in frame:
        st.write("No chart data available.")
        return
    st.plotly_chart(px.pie(frame, names=names, values=values, title=title, hole=0.35), use_container_width=True)


def render_home(summary: dict | None = None, master: dict | None = None) -> None:
    st.markdown(
        f"""
        <div class="sp-hero">
          <div class="sp-pill">Read-only portfolio decision platform</div>
          <h2>{APP_NAME}</h2>
          <p>{TAGLINE}</p>
          <p class="sp-muted">Connect Robinhood, pull current holdings, scan risk, rank new ideas from live market data and RSS news, then get a plain-English decision summary when OpenAI is enabled.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    items = [
        ("Portfolio health", "See value, gains, concentration, and today’s account move in one place."),
        ("Action review", "Find the holdings that deserve attention before you look at every row."),
        ("Idea discovery", "Builds candidates from RSS market headlines instead of a fixed watchlist."),
        ("Quant context", "Adds factor checks, backtests, strategy signals, and news context."),
    ]
    for col, (title, body) in zip(cols, items):
        with col:
            st.markdown(f'<div class="sp-card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)

    if summary:
        st.subheader("Current Snapshot")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Market value", fmt_money(summary.get("total_value")))
        metric_cols[1].metric("Positions", summary.get("positions", 0))
        metric_cols[2].metric("Concentrated", len(summary.get("concentrated", [])))
        metric_cols[3].metric("Today", fmt_money(summary.get("today_change")), fmt_pct(summary.get("today_change_pct")))
    if master and master.get("plain_english_summary"):
        st.info(master["plain_english_summary"])


def render_analysis_form(expanded: bool = True) -> tuple[bool, dict]:
    with st.expander("Analysis setup", expanded=expanded):
        st.caption("Connect your account, choose how much AI context to use, and run a fresh analysis.")
        with st.form("analysis_form"):
            row1 = st.columns([1, 1])
            use_robinhood = row1[0].checkbox(
                "Use Robinhood",
                value=True,
                help="Use your saved credentials.md file to import live Robinhood holdings. The app reads data only and does not trade.",
            )
            use_openai = row1[1].checkbox(
                "Use OpenAI summary",
                help="Uses one master prompt to summarize portfolio actions, sentiment, and strategy context.",
            )
            row2 = st.columns([2, 1, 1])
            extra_tickers_text = row2[0].text_input(
                "Optional extra tickers",
                "",
                help="Comma-separated tickers to add to the automatically discovered RSS candidate universe.",
            )
            limit = row2[1].slider("Buy ideas", 3, 15, 5, help="How many discovered candidates to rank and show.")
            include_owned_ideas = row2[2].checkbox(
                "Include owned tickers",
                help="Include current holdings in the buy-idea ranking. Leave this off if you only want new ideas.",
            )
            submitted = st.form_submit_button("Analyze portfolio", type="primary")
    return submitted, {
        "credentials_path": CREDENTIALS_PATH,
        "use_robinhood": use_robinhood,
        "use_openai": use_openai,
        "extra_tickers_text": extra_tickers_text,
        "limit": limit,
        "include_owned_ideas": include_owned_ideas,
    }


def explain_note(text: str) -> None:
    st.markdown(f'<div class="sp-note">{text}</div>', unsafe_allow_html=True)


def concentration_comment(summary: dict) -> str:
    concentrated = summary.get("concentrated", [])
    if not concentrated:
        return "Good: no single position is above the concentration threshold. That usually means one bad move is less likely to dominate the whole account."
    top = concentrated[0]
    return f"Watch this: {top['ticker']} is {fmt_pct(top.get('portfolio_weight'))} of the portfolio. A large drop in that one holding can move the whole account, so avoid adding more until the weight comes down."


def action_mix_comment(action_counts: pd.DataFrame) -> str:
    if action_counts.empty:
        return "No actions were generated yet."
    top = action_counts.sort_values("count", ascending=False).iloc[0]
    return f"Most holdings are marked '{top['action']}'. If the action mix is mostly hold, the main job is risk control, not constant trading."


def alpha_comment(ic_table: pd.DataFrame) -> str:
    if ic_table.empty:
        return "There is not enough factor data to judge which signals are working. Add more tickers or run this over time."
    best = ic_table.iloc[ic_table["ic_value"].abs().argmax()]
    if abs(best["ic_value"]) < 0.02:
        return "Most factors look weak right now. That means the model should lean less on factor ranking and more on risk controls."
    direction = "positive" if best["ic_value"] > 0 else "negative"
    return f"{best['factor_name']} has the strongest {direction} IC proxy. Treat it as useful context, but confirm it persists over multiple runs."


def backtest_comment(metrics: dict) -> str:
    total = metrics.get("total_return")
    drawdown = metrics.get("max_drawdown")
    sharpe = metrics.get("sharpe")
    if total is None:
        return "The backtest did not return enough data. Try a broader universe or shorter lookback."
    verdict = "encouraging" if total > 0 and (sharpe or 0) > 0.5 else "weak"
    return f"This backtest looks {verdict}: total return is {fmt_pct(total)}, Sharpe is {(sharpe or 0):.2f}, and max drawdown is {fmt_pct(drawdown)}. Prefer strategies with positive return, tolerable drawdown, and stable monthly results."


def strategy_comment(strategies: pd.DataFrame) -> str:
    if strategies.empty:
        return "No strategy signals are available yet."
    active = int((strategies["status"] == "Active").sum())
    strongest = strategies.sort_values("avg_signal", ascending=False).iloc[0]
    return f"{active} strategies are active. The strongest current signal is {strongest['strategy']}. If one strategy dominates risk attribution, diversify the decision process before acting."


def allocation_plan(cash: float, ideas: list[dict], holdings_report: list[dict], risk_profile: str) -> list[dict]:
    if cash <= 0:
        return []
    owned_weights = {row["ticker"]: row.get("portfolio_weight") or 0 for row in holdings_report if not row.get("error")}
    clean = [
        idea for idea in ideas
        if "error" not in idea and idea.get("score", -999) > 0 and owned_weights.get(idea.get("ticker"), 0) < 0.15
    ]
    if risk_profile == "Conservative":
        clean = sorted(clean, key=lambda item: (item.get("volatility") or 9, -(item.get("score") or 0)))
    else:
        clean = sorted(clean, key=lambda item: item.get("score") or 0, reverse=True)
    picks = clean[:3]
    if not picks:
        return []
    weights = [max(item.get("score") or 0.1, 0.1) for item in picks]
    total = sum(weights)
    return [
        {
            "ticker": item["ticker"],
            "name": item.get("name", item["ticker"]),
            "amount": cash * weight / total,
            "score": item.get("score"),
            "why": "; ".join(item.get("reasons", [])[:3]),
            "news_items": item.get("news_items", []),
            "action": "Research / consider staged buy",
        }
        for item, weight in zip(picks, weights)
    ]


def deployment_plan(cash: float, risk_profile: str, summary: dict, plan: list[dict]) -> dict:
    if cash <= 0 or not plan:
        return {"mode": "Wait", "schedule": [], "summary": "No cash deployment plan was created."}
    concentrated = bool(summary.get("concentrated"))
    if risk_profile == "Conservative" or concentrated:
        chunks = [0.25, 0.25, 0.25, 0.25]
        labels = ["Today", "In 1 week", "In 2 weeks", "In 3 weeks"]
        mode = "Split over four buys"
        reason = "This slows down timing risk and is better when the account already has concentration risk."
    elif risk_profile == "Aggressive":
        chunks = [0.50, 0.25, 0.25]
        labels = ["Today", "In 3 trading days", "In 2 weeks"]
        mode = "Front-loaded staged buy"
        reason = "This puts more cash to work now while still leaving room if prices pull back."
    else:
        chunks = [0.34, 0.33, 0.33]
        labels = ["Today", "In 1 week", "In 2 weeks"]
        mode = "Balanced three-step buy"
        reason = "This avoids making the entire decision on one market day."
    schedule = [{"interval": label, "amount": cash * chunk} for label, chunk in zip(labels, chunks)]
    return {"mode": mode, "schedule": schedule, "summary": reason}


def integrated_strategy_summary(
    summary: dict,
    alpha: dict,
    backtest_metrics: dict | None,
    monitor: dict,
    master: dict,
    plan: list[dict],
) -> str:
    concentrated = summary.get("concentrated", [])
    concentration_text = "No single position is above the concentration threshold."
    if concentrated:
        top = concentrated[0]
        concentration_text = f"{top['ticker']} is the main risk because it is {fmt_pct(top.get('portfolio_weight'))} of the portfolio."
    ic_table = alpha.get("ic_table", pd.DataFrame())
    alpha_text = alpha_comment(ic_table)
    bt_text = backtest_comment(backtest_metrics or {}) if backtest_metrics else "The backtester has not been run for this view yet."
    strategies = monitor.get("strategies", pd.DataFrame())
    strategy_text = strategy_comment(strategies)
    picks = ", ".join(row["ticker"] for row in plan) if plan else "no new picks"
    llm_text = master.get("plain_english_summary") or "OpenAI summary is off, so this summary uses the local model outputs only."
    return (
        f"{concentration_text} {alpha_text} {bt_text} {strategy_text} "
        f"For new money, the current research list points to {picks}. {llm_text}"
    )


def heatmap_comment(monthly: pd.DataFrame) -> str:
    if monthly.empty:
        return "There is no monthly data to analyze yet."
    best = monthly.sort_values("return", ascending=False).iloc[0]
    worst = monthly.sort_values("return").iloc[0]
    positive_rate = (monthly["return"] > 0).mean()
    return f"The strategy had positive months {positive_rate:.0%} of the time. Best month was {best['month']} at {fmt_pct(best['return'])}; worst month was {worst['month']} at {fmt_pct(worst['return'])}. Look for smoother results, not just one strong month."


def sector_comment(frame: pd.DataFrame) -> str:
    if frame.empty or "sector" not in frame:
        return "Sector data is not available yet."
    sector_values = frame.groupby("sector")["market_value"].sum().sort_values(ascending=False)
    top_sector = sector_values.index[0]
    top_weight = sector_values.iloc[0] / sector_values.sum()
    return f"Largest sector exposure is {top_sector} at {fmt_pct(top_weight)}. High sector concentration can make different tickers behave like one large position."


def sentiment_cards(sentiment_rows: pd.DataFrame) -> None:
    if sentiment_rows.empty:
        st.write("Enable OpenAI summary to populate sentiment cards.")
        return
    for start in range(0, len(sentiment_rows), 3):
        cols = st.columns(min(3, len(sentiment_rows) - start))
        for col, (_, row) in zip(cols, sentiment_rows.iloc[start:start + 3].iterrows()):
            with col:
                signals = row.get("key_signals", [])
                signal_text = "; ".join(signals[:2]) if isinstance(signals, list) else str(signals)
                st.markdown(
                    f"""
                    <div class="sp-card">
                      <div class="sp-pill">{row.get("label", "Neutral")} · {row.get("score", 0):.0f}</div>
                      <h4>{row.get("ticker")}</h4>
                      <p>{row.get("alpha_implication", "")}</p>
                      <p>{signal_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_strategy_cards(strategies: pd.DataFrame) -> None:
    if strategies.empty:
        st.write("No strategy monitor data available.")
        return
    for start in range(0, len(strategies), 4):
        cols = st.columns(min(4, len(strategies) - start))
        for col, (_, row) in zip(cols, strategies.iloc[start:start + 4].iterrows()):
            with col:
                st.markdown(
                    f"""
                    <div class="sp-card">
                      <div class="sp-pill">{row.get("status")}</div>
                      <h4>{row.get("strategy")}</h4>
                      <p>Signal: {row.get("avg_signal", 0):.2f}</p>
                      <p>Risk share: {fmt_pct(row.get("risk_attribution"))}</p>
                      <p>Return proxy: {fmt_pct(row.get("ytd_return_proxy"))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_action_cards(rows: list[dict]) -> None:
    if not rows:
        st.write("No urgent review items were flagged.")
        return
    cols = st.columns(min(3, len(rows)))
    for col, row in zip(cols, rows):
        with col:
            st.markdown(
                f"""
                <div class="sp-card">
                  <div class="sp-pill">{row.get("ticker")}</div>
                  <h4>{row.get("action")}</h4>
                  <p>Weight: {fmt_pct(row.get("portfolio_weight"))}</p>
                  <p>Gain: {fmt_pct(row.get("unrealized_gain"))}</p>
                  <p>Final score: {row.get("final_score", "n/a")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_idea_cards(ideas: list[dict]) -> None:
    clean = [idea for idea in ideas if "error" not in idea][:6]
    if not clean:
        st.write("No scored buy ideas available.")
        return
    for start in range(0, len(clean), 3):
        cols = st.columns(min(3, len(clean) - start))
        for col, idea in zip(cols, clean[start:start + 3]):
            with col:
                reasons = "; ".join(idea.get("reasons", [])[:2]) or "No rationale available."
                st.markdown(
                    f"""
                    <div class="sp-card">
                      <div class="sp-pill">Score {idea.get("score", 0):.2f}</div>
                      <h4>{idea.get("ticker")} · {idea.get("name", "")}</h4>
                      <p>Price: {fmt_money(idea.get("price"))}</p>
                      <p>{reasons}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_clean_holdings_table(rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.write("No holdings loaded.")
        return
    for source, target in [
        ("portfolio_weight", "weight_pct"),
        ("unrealized_gain", "gain_pct"),
        ("return_3m", "return_3m_pct"),
        ("drawdown", "drawdown_pct"),
    ]:
        if source in frame:
            frame[target] = frame[source] * 100
    columns = ["ticker", "action", "weight_pct", "market_value", "gain_pct", "return_3m_pct", "drawdown_pct", "final_score"]
    frame = frame[[column for column in columns if column in frame]]
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "weight_pct": st.column_config.ProgressColumn("Weight", format="%.1f%%", min_value=0, max_value=100),
            "market_value": st.column_config.NumberColumn("Value", format="$%.0f"),
            "gain_pct": st.column_config.NumberColumn("Gain", format="%.1f%%"),
            "return_3m_pct": st.column_config.NumberColumn("3M return", format="%.1f%%"),
            "drawdown_pct": st.column_config.NumberColumn("Drawdown", format="%.1f%%"),
            "final_score": st.column_config.NumberColumn("Score", format="%.2f"),
        },
    )


@st.cache_data(ttl=900, show_spinner=False)
def cached_backtest(strategy: str, universe_tuple: tuple[str, ...], years: int) -> dict:
    return run_backtest(strategy, list(universe_tuple), lookback_years=years)


run, config = render_analysis_form(expanded=st.session_state.analysis is None)

if run:
    run_start = time.perf_counter()
    progress = st.progress(0)
    status = st.empty()
    timings: list[dict[str, str]] = []

    def step(label: str, value: int) -> None:
        elapsed = time.perf_counter() - run_start
        progress.progress(min(value, 100))
        status.write(f"{label} ({elapsed:.1f}s elapsed)")
        LOGGER.info("UI progress %s pct=%s elapsed=%.2fs", label, value, elapsed)

    def ticker_progress(base: int, span: int):
        def update(index: int, total: int, label: str) -> None:
            step(label, base + int(span * index / max(total, 1)))

        return update

    credentials = load_credentials(config["credentials_path"])
    extra_tickers = [ticker.strip().upper() for ticker in config["extra_tickers_text"].split(",") if ticker.strip()]
    as_of = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    st.write(f"As of {as_of}")

    step("Loading portfolio", 5)
    portfolio_start = time.perf_counter()
    if config["use_robinhood"]:
        holdings = get_robinhood_portfolio(credentials)
        step("Loading Robinhood account totals", 12)
        account_totals = get_robinhood_account_totals(credentials)
    else:
        holdings = get_manual_portfolio(credentials)
        account_totals = None
    timings.append({"stage": "portfolio_load", "seconds": f"{time.perf_counter() - portfolio_start:.2f}"})

    step("Building dynamic buy universe", 14)
    universe_start = time.perf_counter()
    dynamic_universe = build_dynamic_universe(
        holdings,
        credentials if config["use_openai"] else {k: v for k, v in credentials.items() if k != "OPENAI_API_KEY"},
        extra_tickers=extra_tickers,
        limit=max(config["limit"] * 3, 12),
    )
    watchlist = dynamic_universe["tickers"]
    timings.append({"stage": "dynamic_universe", "seconds": f"{time.perf_counter() - universe_start:.2f}"})

    step("Analyzing holdings", 16)
    analysis_start = time.perf_counter()
    holdings_report = analyze_holdings(
        holdings,
        credentials,
        use_llm=False,
        progress_callback=ticker_progress(18, 32),
    ) if holdings else []
    timings.append({"stage": "holdings_analysis", "seconds": f"{time.perf_counter() - analysis_start:.2f}"})

    step("Ranking buy candidates", 52)
    ideas_start = time.perf_counter()
    owned = {holding.ticker.upper() for holding in holdings}
    exclude = set() if config["include_owned_ideas"] else owned
    ideas = rank_buy_ideas(
        watchlist,
        credentials,
        config["limit"],
        exclude=exclude,
        progress_callback=ticker_progress(54, 18),
    )
    timings.append({"stage": "buy_ideas", "seconds": f"{time.perf_counter() - ideas_start:.2f}"})

    universe = sorted(set([row["ticker"] for row in holdings_report if not row.get("error")] + watchlist))

    step("Preparing quant modules", 74)
    quant_start = time.perf_counter()
    alpha = alpha_factor_explorer(universe)
    monitor = strategy_monitor(holdings_report)
    timings.append({"stage": "quant_modules", "seconds": f"{time.perf_counter() - quant_start:.2f}"})

    master = {"plain_english_summary": "", "portfolio_advice": [], "sentiment": [], "strategy_advice": ""}
    if config["use_openai"]:
        step("Running one OpenAI master analysis", 84)
        master_start = time.perf_counter()
        master = openai_master_analysis(
            holdings_report,
            ideas,
            credentials,
            strategy_state=monitor["strategies"].to_dict("records") if not monitor["strategies"].empty else [],
        )
        timings.append({"stage": "openai_master_analysis", "seconds": f"{time.perf_counter() - master_start:.2f}"})

    step("Rendering dashboard", 93)
    timings.append({"stage": "total", "seconds": f"{time.perf_counter() - run_start:.2f}"})
    st.session_state.analysis = {
        "as_of": as_of,
        "holdings": holdings,
        "holdings_report": holdings_report,
        "account_totals": account_totals,
        "dynamic_universe": dynamic_universe,
        "watchlist": watchlist,
        "ideas": ideas,
        "universe": universe,
        "alpha": alpha,
        "monitor": monitor,
        "master": master,
        "timings": timings,
    }
    step("Analysis complete", 100)

data = st.session_state.analysis

if data is None:
    render_home()
    st.info("Set your connection options above and click Analyze portfolio.")
else:
    as_of = data["as_of"]
    holdings = data["holdings"]
    holdings_report = data["holdings_report"]
    account_totals = data["account_totals"]
    dynamic_universe = data["dynamic_universe"]
    watchlist = data["watchlist"]
    ideas = data["ideas"]
    universe = data["universe"]
    alpha = data["alpha"]
    monitor = data["monitor"]
    master = data["master"]
    timings = data["timings"]

    st.write(f"As of {as_of}")
    tabs = st.tabs(
        [
            "Home",
            "Portfolio",
            "Alpha Explorer",
            "Backtester",
            "LLM Sentiment",
            "Strategy Monitor",
            "Investment Strategy",
            "Profile",
            "Buy Ideas",
            "Logs",
        ]
    )

    with tabs[0]:
        summary = portfolio_summary(holdings_report, account_totals)
        render_home(summary, master)

    with tabs[1]:
        tab_intro(
            "Portfolio overview",
            "This tab answers the basic question: what do I own, where is risk concentrated, and what deserves attention today?",
        )
        if master.get("plain_english_summary"):
            st.info(master["plain_english_summary"])
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Robinhood market value", f"${summary['total_value']:,.2f}")
        col2.metric("Positions", summary["positions"])
        col3.metric("Concentrated positions", len(summary["concentrated"]))
        col4.metric(
            "Today",
            f"${summary['today_change']:,.2f}" if summary["today_change"] is not None else "n/a",
            f"{summary['today_change_pct'] * 100:.2f}%" if summary["today_change_pct"] is not None else None,
        )

        st.subheader("What Should I Review Today")
        action_rows = today_actions(holdings_report)
        render_action_cards(action_rows)
        if master.get("portfolio_advice"):
            st.subheader("OpenAI Decision Summary")
            dataframe_or_note(pd.DataFrame(master["portfolio_advice"]), "No OpenAI advice rows returned.")

        st.subheader("Risk Panel")
        chart_left, chart_right = st.columns(2)
        holdings_frame = pd.DataFrame([row for row in holdings_report if not row.get("error")])
        with chart_left:
            pie_chart(holdings_frame, "ticker", "market_value", "Position size by market value")
            explain_note(concentration_comment(summary))
        with chart_right:
            gain_frame = holdings_frame.assign(gain_dollars=holdings_frame["market_value"] - (holdings_frame["market_value"] / (1 + holdings_frame["unrealized_gain"].fillna(0))))
            st.plotly_chart(
                px.bar(gain_frame.sort_values("gain_dollars", ascending=False), x="ticker", y="gain_dollars", title="Estimated unrealized gain by ticker"),
                use_container_width=True,
            )
            explain_note("This shows where paper gains are sitting. Large gains are good, but they also create tax and giveback risk. Review whether the position size still fits your plan.")
        st.subheader("Sector and correlation risk")
        sector_left, sector_right = st.columns(2)
        with sector_left:
            if "sector" in holdings_frame:
                sector_frame = holdings_frame.groupby("sector", as_index=False)["market_value"].sum()
                pie_chart(sector_frame, "sector", "market_value", "Sector exposure")
                explain_note(sector_comment(holdings_frame))
        with sector_right:
            corr_cols = [row["ticker"] for row in holdings_report if not row.get("error")][:8]
            corr_data = {}
            for ticker in corr_cols:
                try:
                    corr_data[ticker] = get_price_history(ticker, period="6mo")["Close"].pct_change()
                except Exception:
                    pass
            corr_frame = pd.DataFrame(corr_data).dropna()
            if not corr_frame.empty and corr_frame.shape[1] > 1:
                st.plotly_chart(px.imshow(corr_frame.corr(), text_auto=".2f", aspect="auto", title="6-month return correlation"), use_container_width=True)
                explain_note("High correlations mean positions may fall together. If several holdings are above 0.70 correlation, position count may overstate your real diversification.")
        if summary["concentrated"]:
            top = summary["concentrated"][0]
            scenarios = pd.DataFrame(
                [
                    {
                        "ticker": top["ticker"],
                        "shock": f"-{int(drop * 100)}%",
                        "portfolio_impact": scenario_impact(holdings_report, top["ticker"], drop),
                    }
                    for drop in [0.20, 0.30, 0.40]
                ]
            )
            st.dataframe(scenarios, use_container_width=True, hide_index=True)

        st.subheader("Tax Impact Panel")
        tickers = [row["ticker"] for row in holdings_report if not row.get("error")]
        if tickers:
            selected = st.selectbox("Ticker", tickers)
            trim_pct = st.slider("Trim percent", 1, 50, 10) / 100
            tax_rate = st.slider("Estimated combined tax rate", 0, 50, 25) / 100
            row = next(row for row in holdings_report if row["ticker"] == selected)
            tax = tax_estimate(row, trim_pct, tax_rate)
            tax_cols = st.columns(5)
            tax_cols[0].metric("Proceeds", f"${tax['proceeds']:,.2f}")
            tax_cols[1].metric("Cost basis sold", f"${tax['cost_basis_sold']:,.2f}")
            tax_cols[2].metric("Taxable gain", f"${tax['taxable_gain']:,.2f}")
            tax_cols[3].metric("Estimated tax", f"${tax['estimated_tax']:,.2f}")
            tax_cols[4].metric("Net reinvestable", f"${tax['net_reinvestable']:,.2f}")
            explain_note("Tax-lot detail is estimated from average cost. Robinhood's basic holdings endpoint does not provide complete lot age here, so long-term versus short-term tax treatment still needs broker tax-lot review before selling.")

        st.subheader("Decision Table")
        if "action" in holdings_frame:
            action_counts = holdings_frame["action"].value_counts().reset_index()
            action_counts.columns = ["action", "count"]
            if not action_counts.empty:
                pie_chart(action_counts, "action", "count", "Action mix")
                explain_note(action_mix_comment(action_counts))
        render_clean_holdings_table(holdings_report)

    with tabs[2]:
        tab_intro(
            "Alpha factor explorer",
            "This tab checks which simple quant signals are working across your current universe. IC near zero means a factor is not separating recent winners from losers.",
        )
        ic_table = alpha["ic_table"]
        factor_table = alpha["factor_table"]
        history = alpha["history"]
        if not ic_table.empty:
            metric_cols = st.columns(4)
            metric_cols[0].metric("Factors tracked", len(ic_table))
            metric_cols[1].metric("Average IC", f"{ic_table['ic_value'].mean():.3f}")
            metric_cols[2].metric("Active factors", int((ic_table["status"] == "Active").sum()))
            metric_cols[3].metric("Universe size", int(ic_table["universe_size"].max()))
            st.plotly_chart(
                px.bar(
                    ic_table,
                    x="factor_name",
                    y="ic_value",
                    color="status",
                    title="Factor information coefficient proxy",
                ),
                use_container_width=True,
            )
            explain_note(alpha_comment(ic_table))
        with st.expander("Factor details"):
            dataframe_or_note(ic_table, "Not enough data to compute cross-sectional IC proxy.")
        if not history.empty:
            top_factors = ic_table.sort_values("ic_value", key=lambda s: s.abs(), ascending=False)["factor_name"].head(3)
            hist = history[history["factor_name"].isin(top_factors)]
            if not hist.empty:
                st.line_chart(hist.pivot_table(index="date", columns="factor_name", values="ic_value", aggfunc="mean"))
        st.subheader("Latest Factor Snapshot")
        with st.expander("Latest factor snapshot"):
            dataframe_or_note(factor_table, "No factor table available.")

    with tabs[3]:
        tab_intro(
            "Strategy backtester",
            "This tab compares simple rule-based strategies against SPY. It is a quick sanity check, not a production-grade backtest.",
        )
        strategy = st.selectbox(
            "Strategy",
            ["Momentum long only", "Short-term mean reversion", "Multi-factor composite", "LLM sentiment overlay"],
            help="Select the rule set to test against historical prices. This recalculates only the backtest, not the full portfolio analysis.",
        )
        universe_choice = st.selectbox(
            "Universe",
            ["Holdings", "Discovered candidates", "Combined"],
            help="Choose whether the backtest uses your current holdings, discovered candidates, or both.",
        )
        lookback = st.selectbox("Lookback", ["1Y", "3Y", "5Y"], index=1, help="Historical period used for the backtest.")
        if universe_choice == "Holdings":
            bt_universe = [row["ticker"] for row in holdings_report if not row.get("error")]
        elif universe_choice == "Discovered candidates":
            bt_universe = watchlist
        else:
            bt_universe = universe
        years = int(lookback[0])
        backtest = cached_backtest(strategy, tuple(sorted(set(bt_universe))), years)
        metrics = backtest["metrics"]
        bt_cols = st.columns(4)
        bt_cols[0].metric("Total return", f"{metrics.get('total_return', 0) * 100:.1f}%")
        bt_cols[1].metric("Sharpe", f"{metrics.get('sharpe', 0):.2f}")
        bt_cols[2].metric("Max drawdown", f"{metrics.get('max_drawdown', 0) * 100:.1f}%")
        bt_cols[3].metric("Monthly win rate", f"{metrics.get('monthly_win_rate', 0) * 100:.1f}%")
        curve = backtest["curve"]
        if not curve.empty:
            curve_long = curve.melt(id_vars="date", value_vars=["strategy", "benchmark"], var_name="series", value_name="value")
            st.plotly_chart(px.line(curve_long, x="date", y="value", color="series", title="Cumulative return"), use_container_width=True)
            explain_note(backtest_comment(metrics))
        if not backtest["monthly"].empty:
            monthly = backtest["monthly"].copy()
            monthly["year"] = monthly["month"].str.slice(0, 4)
            monthly["month_num"] = monthly["month"].str.slice(5, 7)
            heat = monthly.pivot(index="year", columns="month_num", values="return")
            st.plotly_chart(px.imshow(heat, text_auto=".1%", aspect="auto", title="Monthly strategy returns"), use_container_width=True)
            explain_note(heatmap_comment(backtest["monthly"]))
        with st.expander("Monthly return data"):
            dataframe_or_note(backtest["monthly"], "No monthly returns available.")

    with tabs[4]:
        tab_intro(
            "LLM sentiment",
            "This tab turns headlines and portfolio metrics into plain-English context. If live news is missing, the model labels its output as fallback context.",
        )
        sentiment_rows = pd.DataFrame(master.get("sentiment", []))
        sentiment_cards(sentiment_rows)
        explain_note("Sentiment is context, not a trade by itself. Strong positive sentiment can confirm a good setup, while weak confidence or risk flags mean you should lean more on price action and position sizing.")
        with st.expander("Sentiment details"):
            dataframe_or_note(sentiment_rows, "Enable OpenAI summary in the setup panel to populate this tab.")
        topic = st.text_input("Ticker or macro topic for next run", "")
        st.caption(f"Topic entered: {topic or 'none'}")

    with tabs[5]:
        tab_intro(
            "Strategy monitor",
            "This tab watches the active signals side by side so you can see whether the portfolio is being driven by momentum, mean reversion, sentiment, or the composite score.",
        )
        strategies = monitor["strategies"]
        if not strategies.empty:
            cols = st.columns(4)
            cols[0].metric("Active strategies", int((strategies["status"] == "Active").sum()))
            cols[1].metric("Blended Sharpe proxy", f"{monitor['blended_sharpe_proxy']:.2f}")
            cols[2].metric("Net long exposure proxy", f"{strategies['avg_signal'].clip(lower=0).sum():.2f}")
            cols[3].metric("Strategies tracked", len(strategies))
            strat_left, strat_right = st.columns(2)
            with strat_left:
                st.plotly_chart(px.bar(strategies, x="strategy", y="avg_signal", color="status", title="Average signal by strategy"), use_container_width=True)
                explain_note(strategy_comment(strategies))
            with strat_right:
                pie_chart(strategies, "strategy", "risk_attribution", "Risk attribution proxy")
        render_strategy_cards(strategies)
        with st.expander("Recent signals"):
            dataframe_or_note(monitor["signals"], "No signals logged yet.")
        if master.get("strategy_advice"):
            st.subheader("OpenAI Portfolio Advice")
            st.write(master["strategy_advice"])
            dataframe_or_note(pd.DataFrame(master.get("portfolio_advice", [])), "No portfolio advice rows returned.")

    with tabs[6]:
        tab_intro(
            "Investment strategy",
            "Use this page when you have new cash and want a clean plan for where to research putting it. It combines your current concentration, buy-candidate scores, risk, and news links.",
        )
        cash = st.number_input(
            "Cash available to invest",
            min_value=0.0,
            value=1000.0,
            step=100.0,
            help="Enter new money you could invest now. This does not include current holdings unless you choose to sell separately.",
        )
        risk_profile = st.selectbox(
            "Risk style",
            ["Balanced", "Conservative", "Aggressive"],
            help="Conservative favors lower volatility candidates. Aggressive gives more weight to high-scoring momentum ideas.",
        )
        plan = allocation_plan(cash, ideas, holdings_report, risk_profile)
        deploy = deployment_plan(cash, risk_profile, summary, plan)
        if plan:
            st.subheader("When to invest")
            sched_cols = st.columns(len(deploy["schedule"]))
            for col, item in zip(sched_cols, deploy["schedule"]):
                with col:
                    st.markdown(
                        f"""
                        <div class="sp-card">
                          <div class="sp-pill">{deploy['mode']}</div>
                          <h4>{item['interval']}</h4>
                          <p>{fmt_money(item['amount'])}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            explain_note(deploy["summary"])

            st.subheader("Suggested research allocation")
            total_plan = sum(row["amount"] for row in plan)
            cols = st.columns(len(plan))
            for col, row in zip(cols, plan):
                with col:
                    st.markdown(
                        f"""
                        <div class="sp-card">
                          <div class="sp-pill">{fmt_money(row['amount'])}</div>
                          <h4>{row['ticker']} · {row['name']}</h4>
                          <p>Score: {row.get('score', 0):.2f}</p>
                          <p>{row.get('why') or 'Ranked by the candidate model.'}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            explain_note(
                f"This plan allocates {fmt_money(total_plan)} across the highest-ranked candidates that are not already oversized. A staged buy can reduce timing risk, especially when the market is moving quickly."
            )
            st.subheader("News articles to review")
            for row in plan:
                with st.expander(f"{row['ticker']} news and context"):
                    if row.get("news_items"):
                        for item in row["news_items"][:5]:
                            title = item.get("title", "")
                            link = item.get("link", "")
                            if link:
                                st.markdown(f"- [{title}]({link})")
                            else:
                                st.write(f"- {title}")
                    else:
                        st.write("No linked news articles were returned for this ticker.")
                    st.write(f"Why it made the list: {row.get('why')}")
        else:
            st.write("No allocation plan was generated. Try increasing cash, enabling discovered candidates, or adding extra tickers.")

        st.subheader("What experts are saying")
        expert_rows = []
        for idea in ideas:
            if "error" in idea:
                continue
            expert_rows.append(
                {
                    "ticker": idea.get("ticker"),
                    "analyst_view": idea.get("recommendation", "n/a"),
                    "target_gap": idea.get("target_gap"),
                    "model_score": idea.get("score"),
                    "context": "; ".join(idea.get("reasons", [])[:2]),
                }
            )
        expert_frame = pd.DataFrame(expert_rows)
        dataframe_or_note(expert_frame, "No analyst context available.")
        explain_note("This panel blends analyst fields from Yahoo Finance with the app's factor score. If analyst target gap is positive, analysts expect upside from the current price, but targets can lag fast-moving markets.")
        st.subheader("Plain-English strategy summary")
        st.write(integrated_strategy_summary(summary, alpha, None, monitor, master, plan))

    with tabs[7]:
        tab_intro(
            "Profile",
            "This page sketches the production account model: one SignalPilot login, then connected broker accounts under that profile.",
        )
        top = st.columns([3, 1])
        with top[0]:
            st.markdown(
                """
                <div class="sp-card">
                  <div class="sp-pill">Signed in profile</div>
                  <h4>Local development user</h4>
                  <p>Production version should use Firebase Auth for email, Google, or Apple sign-in.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top[1]:
            st.button("Profile", help="In production this opens account settings, broker connections, billing, and security.")
        broker_cols = st.columns(2)
        with broker_cols[0]:
            st.markdown(
                """
                <div class="sp-card">
                  <div class="sp-pill">Connected</div>
                  <h4>Robinhood</h4>
                  <p>Read-only holdings import is active in this local build.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with broker_cols[1]:
            st.markdown(
                """
                <div class="sp-card">
                  <div class="sp-pill">Planned</div>
                  <h4>Fidelity</h4>
                  <p>Planned connector uses fidelity-api with Playwright and 2FA support. Keep it read-only by default.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        explain_note("Broker credentials should not be stored as plain text. Use Firebase Auth for identity, Firestore for metadata, and a server-side encrypted secret store for broker tokens or session references.")

    with tabs[8]:
        tab_intro(
            "Buy ideas",
            "This tab ranks candidates the app discovered from RSS headlines, OpenAI suggestions when enabled, and any extra tickers you typed in.",
        )
        st.write(f"Universe source: {dynamic_universe['source']}")
        st.write(f"Candidate universe: {', '.join(watchlist) if watchlist else 'none'}")
        if dynamic_universe.get("llm_rationale"):
            st.caption(dynamic_universe["llm_rationale"])
        rows = []
        for idea in ideas:
            rows.append(
                {
                    "ticker": idea["ticker"],
                    "name": idea.get("name", ""),
                    "score": idea.get("score"),
                    "price": idea.get("price"),
                    "momentum_12_1": idea.get("momentum_12_1"),
                    "volatility": idea.get("volatility"),
                    "target_gap": idea.get("target_gap"),
                    "top_reasons": "; ".join(idea.get("reasons", [])[:4]),
                    "error": idea.get("error", ""),
                }
            )
        render_idea_cards(ideas)
        idea_frame = pd.DataFrame(rows)
        if not idea_frame.empty and "score" in idea_frame:
            st.plotly_chart(px.bar(idea_frame, x="ticker", y="score", color="score", title="Buy candidate scores"), use_container_width=True)
            explain_note("Higher scores mean the candidate has a better mix of momentum, trend, quality, valuation, and news context. Treat these as a research queue, not a shopping list.")
        for idea in ideas:
            if "error" in idea:
                continue
            with st.expander(f"{idea['ticker']} rationale"):
                st.write("; ".join(idea.get("reasons", [])))
                if idea.get("news"):
                    st.write("Latest headlines")
                    for headline in idea["news"]:
                        st.write(f"- {headline}")

    with tabs[9]:
        st.subheader("Run Log")
        st.dataframe(pd.DataFrame(timings), use_container_width=True, hide_index=True)
        st.write("Detailed logs are written to `portfolio_bot.log`.")
        actions_csv = pd.DataFrame(
            [
                {
                    "timestamp": as_of,
                    "ticker": row.get("ticker"),
                    "action": row.get("action"),
                    "weight": row.get("portfolio_weight"),
                    "gain": row.get("unrealized_gain"),
                    "score": row.get("final_score"),
                }
                for row in holdings_report
                if not row.get("error")
            ]
        ).to_csv(index=False)
        st.download_button("Download action log CSV", actions_csv, file_name="signalpilot_action_log.csv", mime="text/csv")
