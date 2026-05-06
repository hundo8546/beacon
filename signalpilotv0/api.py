import json
import logging
import math
import os
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_default_policy
from functools import wraps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd
import requests

import firebase_admin
from firebase_admin import auth as firebase_auth

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Initialize Firebase Admin SDK
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

# Environment and config
BEACON_ENV = os.getenv('BEACON_ENV', 'development')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
ALLOWED_MIME_TYPES = {
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/octet-stream',
}

ALLOWED_ORIGINS = (
    ['https://your-project-id.web.app', 'https://your-custom-domain.com']
    if BEACON_ENV == 'production'
    else ['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:3000']
)

# Structured logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            'severity': record.levelname,
            'message': record.getMessage(),
            'timestamp': self.formatTime(record),
            'module': record.module,
        }
        if record.exc_info:
            log['exception'] = self.formatException(record.exc_info)
        return json.dumps(log)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(handlers=[handler], level=logging.INFO)
logger = logging.getLogger('beacon')

# Rate limiting
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, identifier):
        now = time.time()
        with self.lock:
            window_start = now - self.window
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > window_start
            ]
            if len(self.requests[identifier]) >= self.max_requests:
                return False
            self.requests[identifier].append(now)
            return True

rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Firebase token verification
def verify_firebase_token(request_handler):
    """Extracts and verifies Firebase ID token from Authorization header."""
    auth_header = request_handler.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    id_token = auth_header[7:]
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.error('Token verification failed', extra={'error': str(e)})
        return None

def require_auth(handler_method):
    """Decorator for endpoint handler methods. Returns 401 if token is missing or invalid."""
    @wraps(handler_method)
    def wrapper(self, *args, **kwargs):
        token = verify_firebase_token(self)
        if token is None:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
            return
        self.firebase_user = token
        return handler_method(self, *args, **kwargs)
    return wrapper

# File validation
def validate_upload(filename, file_bytes, content_type):
    """Returns (is_valid, error_message)"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, 'File type not supported. Upload a CSV or XLSX file.'
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, 'File too large. Maximum size is 10MB.'
    return True, None

from signalpilotv0.portfolio_bot import (  # noqa: E402
    alpha_factor_explorer,
    analyze_holdings,
    build_dynamic_universe,
    get_manual_portfolio,
    get_price_history,
    get_robinhood_account_totals,
    get_robinhood_portfolio,
    load_credentials,
    normalize_holdings_file,
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


def run_analysis(
    payload: dict[str, Any],
    *,
    imported_holdings: list[Any] | None = None,
    import_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    if imported_holdings is not None:
        holdings = imported_holdings
        account_totals = None
    elif use_robinhood:
        holdings = get_robinhood_portfolio(credentials)
        account_totals = get_robinhood_account_totals(credentials)
    else:
        holdings = get_manual_portfolio(credentials)
        account_totals = None

    holdings_report = analyze_holdings(holdings, credentials, use_llm=False) if holdings else []
    dynamic_universe = build_dynamic_universe(
        holdings,
        credentials if use_openai else {key: value for key, value in credentials.items() if key != "OPENAI_API_KEY"},
        holdings_report=holdings_report,
        extra_tickers=extra_tickers,
        limit=max(limit * 3, 12),
    )
    watchlist = dynamic_universe.get("tickers", [])
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
        "importSource": import_meta,
    }


def run_import_holdings(file_path: Path, filename: str, broker_hint: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    credentials = load_credentials(payload.get("credentialsPath") or str(DEFAULT_CREDENTIALS_PATH))
    imported = normalize_holdings_file(file_path, broker_hint, credentials=credentials)
    analysis_payload = {
        "useRobinhood": False,
        "useOpenAi": parse_bool(payload.get("useOpenAi", False)),
        "limit": int(payload.get("limit", 5) or 5),
        "includeOwnedIdeas": parse_bool(payload.get("includeOwnedIdeas", False)),
        "extraTickersText": payload.get("extraTickersText", ""),
    }
    meta = {
        "filename": filename,
        "detectedBroker": imported["broker"],
        "rowCount": imported["row_count"],
        "preview": imported["preview"][:12],
        "columns": imported["columns"],
        "parser": imported.get("parser", "column-map"),
        "confidence": imported.get("confidence"),
        "warnings": imported.get("warnings", []),
    }
    return run_analysis(analysis_payload, imported_holdings=imported["holdings"], import_meta=meta)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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


def symbol_search(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        return {"query": "", "results": []}
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    response = requests.get(
        url,
        params={"q": query, "quotesCount": 10, "newsCount": 0, "enableFuzzyQuery": "true"},
        headers={"User-Agent": "BeaconLocalDev"},
        timeout=8,
    )
    response.raise_for_status()
    rows = []
    for item in response.json().get("quotes", []):
        symbol = str(item.get("symbol") or "").upper().strip()
        quote_type = str(item.get("quoteType") or "")
        if not symbol or quote_type not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
            continue
        rows.append(
            {
                "ticker": symbol,
                "name": item.get("shortname") or item.get("longname") or symbol,
                "exchange": item.get("exchange") or item.get("exchDisp") or "",
                "type": quote_type,
            }
        )
    return {"query": query, "results": rows[:10]}


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
    def set_cors_headers(self):
        """Set CORS headers based on environment and origin."""
        origin = self.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        elif BEACON_ENV == 'development':
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')

    def end_headers(self) -> None:
        self.set_cors_headers()
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
            if self.path == "/api/import-holdings":
                self.handle_import_holdings()
                return

            payload = self.read_payload()
            if self.path == "/api/analyze":
                self.handle_analyze(payload)
            elif self.path == "/api/backtest":
                self.handle_backtest(payload)
            elif self.path == "/api/security":
                self.handle_security(payload)
            elif self.path == "/api/search-symbols":
                self.handle_search_symbols(payload)
            else:
                self.respond({"error": "Not found"}, status=404)
        except Exception as exc:
            logger.error('Request failed', extra={'path': self.path, 'error': str(exc)})
            self.respond({"error": str(exc), "type": exc.__class__.__name__}, status=500)

    @require_auth
    def handle_analyze(self, payload):
        """POST /api/analyze - requires Firebase auth"""
        user_id = self.firebase_user.get('uid')
        if not rate_limiter.is_allowed(user_id):
            self.respond({'error': 'Rate limit exceeded. Try again in a minute.'}, status=429)
            return
        logger.info('Analysis started', extra={'user_id': user_id})
        self.respond(run_analysis(payload))

    @require_auth
    def handle_import_holdings(self):
        """POST /api/import-holdings - requires Firebase auth"""
        user_id = self.firebase_user.get('uid')
        if not rate_limiter.is_allowed(user_id):
            self.respond({'error': 'Rate limit exceeded. Try again in a minute.'}, status=429)
            return
        try:
            fields, file_path, filename = self.read_multipart_payload()
            try:
                is_valid, error_msg = validate_upload(filename, file_path.read_bytes(), '')
                if not is_valid:
                    self.respond({'error': error_msg}, status=400)
                    return
                logger.info('Holdings imported', extra={'user_id': user_id, 'filename': filename})
                self.respond(run_import_holdings(file_path, filename, fields.get("brokerHint"), fields))
            finally:
                file_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.error('Import failed', extra={'user_id': user_id, 'error': str(exc)})
            self.respond({"error": str(exc)}, status=400)

    @require_auth
    def handle_backtest(self, payload):
        """POST /api/backtest - requires Firebase auth"""
        user_id = self.firebase_user.get('uid')
        if not rate_limiter.is_allowed(user_id):
            self.respond({'error': 'Rate limit exceeded. Try again in a minute.'}, status=429)
            return
        logger.info('Backtest started', extra={'user_id': user_id})
        self.respond(run_backtest_endpoint(payload))

    @require_auth
    def handle_security(self, payload):
        """POST /api/security - requires Firebase auth"""
        user_id = self.firebase_user.get('uid')
        ticker = payload.get('ticker', '')
        logger.info('Security lookup', extra={'user_id': user_id, 'ticker': ticker})
        self.respond(security_lookup(payload))

    @require_auth
    def handle_search_symbols(self, payload):
        """POST /api/search-symbols - requires Firebase auth"""
        user_id = self.firebase_user.get('uid')
        logger.info('Symbol search', extra={'user_id': user_id})
        self.respond(symbol_search(payload))

    def read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def read_multipart_payload(self) -> tuple[dict[str, Any], Path, str]:
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or 0)
        if "multipart/form-data" not in content_type or not length:
            raise ValueError("Expected a multipart file upload.")
        raw = self.rfile.read(length)
        message = BytesParser(policy=email_default_policy).parsebytes(
            f"Content-Type: {content_type}\nMIME-Version: 1.0\n\n".encode("utf-8") + raw
        )
        fields: dict[str, Any] = {}
        upload_path: Path | None = None
        filename = "holdings.csv"
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            part_filename = part.get_filename()
            data = part.get_payload(decode=True) or b""
            if part_filename:
                suffix = Path(part_filename).suffix.lower() or ".csv"
                if suffix not in {".csv", ".xlsx", ".pdf"}:
                    raise ValueError("Upload a CSV, XLSX, or PDF holdings file.")
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    handle.write(data)
                    upload_path = Path(handle.name)
                filename = part_filename
            elif name:
                fields[name] = data.decode("utf-8").strip()
        if upload_path is None:
            raise ValueError("Upload a CSV, XLSX, or PDF holdings file.")
        return fields, upload_path, filename

    def respond(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(clean_json(payload), separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(format % args)


def main() -> None:
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', sys.argv[1] if len(sys.argv) > 1 else '8787'))
    server = ThreadingHTTPServer((host, port), BeaconHandler)
    print(f"Beacon API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
