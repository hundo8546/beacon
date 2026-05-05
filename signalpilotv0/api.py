import json
import math
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from signalpilotv0.portfolio_bot import (  # noqa: E402
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
    score_candidate,
    stock_snapshot,
    strategy_monitor,
    today_actions,
)

DEFAULT_CREDENTIALS_PATH = Path(__file__).resolve().parent / "credentials.md"


def clean_json(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return clean_json(value.to_dict("records"))
    if isinstance(value, pd.Series):
        return clean_json(value.to_dict())
    if is_dataclass(value):
        return clean_json(asdict(value))
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_json(item) for item in value]
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if pd.isna(value) if value is not None and not isinstance(value, (str, bool, int)) else False:
        return None
    return value


def run_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    credentials_path = payload.get("credentialsPath") or str(DEFAULT_CREDENTIALS_PATH)
    credentials = load_credentials(credentials_path)
    broker_credentials = clean_credential_payload(payload.get("brokerCredentials") or {})
    use_robinhood = bool(payload.get("useRobinhood", True))
    if use_robinhood:
        remove_robinhood_credentials(credentials)
        credentials.update(broker_credentials)
        require_robinhood_credentials(credentials)
    else:
        credentials.update(broker_credentials)
    use_openai = bool(payload.get("useOpenAi", False))
    limit = int(payload.get("limit", 5) or 5)
    include_owned_ideas = bool(payload.get("includeOwnedIdeas", False))
    extra_tickers_text = payload.get("extraTickersText", "")
    extra_tickers = [ticker.strip().upper() for ticker in extra_tickers_text.split(",") if ticker.strip()]

    if use_robinhood:
        holdings = get_robinhood_portfolio(credentials)
        account_totals = get_robinhood_account_totals(credentials)
    else:
        holdings = get_manual_portfolio(credentials)
        account_totals = None

    dynamic_universe = build_dynamic_universe(
        holdings,
        credentials if use_openai else {key: value for key, value in credentials.items() if key != "OPENAI_API_KEY"},
        extra_tickers=extra_tickers,
        limit=max(limit * 3, 12),
    )
    watchlist = dynamic_universe.get("tickers", [])
    holdings_report = analyze_holdings(holdings, credentials, use_llm=False) if holdings else []
    owned = {holding.ticker.upper() for holding in holdings}
    ideas = rank_buy_ideas(
        watchlist,
        credentials,
        limit,
        exclude=set() if include_owned_ideas else owned,
    )
    universe = sorted(set([row["ticker"] for row in holdings_report if not row.get("error")] + watchlist))
    alpha = alpha_factor_explorer(universe)
    monitor = strategy_monitor(holdings_report)
    master = {"plain_english_summary": "", "portfolio_advice": [], "sentiment": [], "strategy_advice": ""}
    if use_openai:
        master = openai_master_analysis(
            holdings_report,
            ideas,
            credentials,
            strategy_state=monitor["strategies"].to_dict("records") if not monitor["strategies"].empty else [],
        )

    summary = portfolio_summary(holdings_report, account_totals)
    return {
        "asOf": datetime.now(timezone.utc).astimezone().isoformat(),
        "elapsedSeconds": round(time.perf_counter() - started, 2),
        "holdings": holdings,
        "holdingsReport": holdings_report,
        "accountTotals": account_totals,
        "summary": summary,
        "actions": today_actions(holdings_report, limit=4),
        "dynamicUniverse": dynamic_universe,
        "watchlist": watchlist,
        "ideas": ideas,
        "universe": universe,
        "alpha": alpha,
        "monitor": monitor,
        "master": master,
    }


def run_backtest_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    strategy = payload.get("strategy") or "Momentum long only"
    universe = payload.get("universe") or []
    years = int(payload.get("years") or 3)
    return run_backtest(strategy, universe, lookback_years=years)


def security_lookup(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = str(payload.get("ticker", "")).strip().upper()
    if not ticker:
        raise ValueError("Provide a ticker, ETF, or fund symbol.")
    credentials = load_credentials(payload.get("credentialsPath") or str(DEFAULT_CREDENTIALS_PATH))
    remove_robinhood_credentials(credentials)
    credentials.update(clean_credential_payload(payload.get("brokerCredentials") or {}))
    snapshot = stock_snapshot(ticker, credentials)
    score, reasons = score_candidate(snapshot)
    signal = "Bullish" if score >= 0.65 else "Constructive" if score >= 0.45 else "Watch" if score >= 0.25 else "Weak"
    return {
        "ticker": ticker,
        "snapshot": snapshot,
        "priceHistory": price_history_points(ticker),
        "score": score,
        "signal": signal,
        "reasons": reasons,
        "asOf": datetime.now(timezone.utc).astimezone().isoformat(),
    }


def price_history_points(ticker: str) -> list[dict[str, Any]]:
    history = get_price_history(ticker, period="1y").tail(126)
    rows = []
    for index, row in history.iterrows():
        close = row.get("Close")
        rows.append(
            {
                "date": index.date().isoformat(),
                "open": float(row.get("Open", close)) if close is not None else None,
                "high": float(row.get("High", close)) if close is not None else None,
                "low": float(row.get("Low", close)) if close is not None else None,
                "close": float(close) if close is not None else None,
            }
        )
    return rows


def clean_credential_payload(payload: dict[str, Any]) -> dict[str, str]:
    allowed = {
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "ROBINHOOD_MFA_CODE",
        "ROBINHOOD_TOTP_SECRET",
        "ROBINHOOD_SESSION_DIR",
    }
    return {key: str(value) for key, value in payload.items() if key in allowed and value}


def remove_robinhood_credentials(credentials: dict[str, Any]) -> None:
    for key in (
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "ROBINHOOD_MFA_CODE",
        "ROBINHOOD_TOTP_SECRET",
        "ROBINHOOD_SESSION_DIR",
    ):
        credentials.pop(key, None)


def require_robinhood_credentials(credentials: dict[str, Any]) -> None:
    if not credentials.get("ROBINHOOD_USERNAME") or not credentials.get("ROBINHOOD_PASSWORD"):
        raise ValueError("Enter Robinhood username and password in the Connect tab before running Robinhood analysis.")


class BeaconHandler(BaseHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.respond({"ok": True, "service": "Beacon API"})
            return
        self.respond({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        try:
            payload = self.read_payload()
            if self.path == "/api/analyze":
                self.respond(run_analysis(payload))
            elif self.path == "/api/backtest":
                self.respond(run_backtest_endpoint(payload))
            elif self.path == "/api/security":
                self.respond(security_lookup(payload))
            elif self.path == "/api/connect-broker":
                broker = payload.get("broker", "robinhood")
                status = "metadata_saved"
                account_count = 0
                last_error = None
                accounts = []
                if broker == "robinhood" and payload.get("testSavedCredentials"):
                    try:
                        credentials = load_credentials(payload.get("credentialsPath") or str(DEFAULT_CREDENTIALS_PATH))
                        remove_robinhood_credentials(credentials)
                        credentials.update(clean_credential_payload(payload.get("brokerCredentials") or {}))
                        require_robinhood_credentials(credentials)
                        totals = get_robinhood_account_totals(credentials)
                        status = "connected"
                        account_count = 1
                        accounts = [
                            {
                                "brokerAccountId": "robinhood-primary",
                                "accountName": payload.get("nickname") or "Robinhood Brokerage",
                                "accountType": "brokerage",
                                "marketValue": totals.get("market_value"),
                                "cash": totals.get("cash"),
                                "currency": "USD",
                                "lastSyncedAt": datetime.now(timezone.utc).astimezone().isoformat(),
                            }
                        ]
                    except Exception as exc:
                        status = "error"
                        last_error = str(exc)
                self.respond(
                    {
                        "broker": broker,
                        "nickname": payload.get("nickname") or f"{broker.title()} Brokerage",
                        "status": status,
                        "readOnly": True,
                        "accountCount": account_count,
                        "accounts": accounts,
                        "lastError": last_error,
                        "message": "Broker metadata saved. Credentials stay server-side; do not store passwords in Firebase.",
                    }
                )
            else:
                self.respond({"error": "Not found"}, status=404)
        except Exception as exc:
            self.respond({"error": str(exc), "type": exc.__class__.__name__}, status=500)

    def read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def respond(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(clean_json(payload), separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("Beacon API: " + format % args + "\n")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    server = ThreadingHTTPServer(("127.0.0.1", port), BeaconHandler)
    print(f"Beacon API listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
