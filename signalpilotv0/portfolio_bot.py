import argparse
import contextlib
import io
import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yfinance as yf
from urllib.parse import quote_plus

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.basicConfig(
    filename="portfolio_bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("portfolio_bot")
SERVER_USER_AGENT = "BeaconLocalDev"

try:
    import robin_stocks.robinhood as rh
except ImportError:
    rh = None


DEFAULT_RSS_FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=stock%20market%20earnings&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=technology%20stocks%20earnings&hl=en-US&gl=US&ceid=US:en",
]

NEWS_TERMS = {
    "AAPL": "Apple",
    "AMD": "AMD",
    "AMZN": "Amazon",
    "ASML": "ASML",
    "AVGO": "Broadcom",
    "BRK-B": "Berkshire",
    "COST": "Costco",
    "GLD": "Gold ETF",
    "GOOGL": "Google",
    "JPM": "JPMorgan",
    "LLY": "Eli Lilly",
    "META": "Meta",
    "MSFT": "Microsoft",
    "MU": "Micron",
    "NVDA": "Nvidia",
    "QQQ": "Nasdaq",
    "SPY": "S&P 500 ETF",
    "TSM": "TSMC",
    "V": "Visa",
}

DISCOVERY_TERMS = {
    "Apple": "AAPL",
    "Amazon": "AMZN",
    "Broadcom": "AVGO",
    "Berkshire": "BRK-B",
    "Costco": "COST",
    "Google": "GOOGL",
    "Alphabet": "GOOGL",
    "JPMorgan": "JPM",
    "Eli Lilly": "LLY",
    "Meta": "META",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Nasdaq": "QQQ",
    "S&P 500": "SPY",
    "TSMC": "TSM",
    "Taiwan Semiconductor": "TSM",
    "Visa": "V",
    "AMD": "AMD",
    "ASML": "ASML",
    "Micron": "MU",
    "Gold": "GLD",
    "Tesla": "TSLA",
    "Netflix": "NFLX",
    "Palantir": "PLTR",
    "Salesforce": "CRM",
    "Oracle": "ORCL",
    "Adobe": "ADBE",
    "Walmart": "WMT",
    "Exxon": "XOM",
    "Chevron": "CVX",
}

POSITIVE_WORDS = {
    "beat",
    "beats",
    "boost",
    "bullish",
    "growth",
    "upgrade",
    "outperform",
    "record",
    "profit",
    "surge",
    "strong",
    "raises",
}

NEGATIVE_WORDS = {
    "cut",
    "cuts",
    "downgrade",
    "miss",
    "misses",
    "lawsuit",
    "probe",
    "weak",
    "risk",
    "warning",
    "falls",
    "slump",
}


@dataclass
class Holding:
    ticker: str
    quantity: float
    avg_cost: float
    price: float | None = None
    market_value: float | None = None
    equity_change: float | None = None
    percent_change: float | None = None
    portfolio_weight: float | None = None


def load_credentials(path: str = "credentials.md") -> dict[str, str]:
    credentials_path = Path(path)
    if not credentials_path.exists():
        return {}

    credentials: dict[str, str] = {}
    pattern = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*$")
    in_code_block = False
    for line in credentials_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = pattern.match(line)
        if match and not match.group(2).startswith("replace_"):
            credentials[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return credentials


def safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def log_timing(label: str, start: float) -> None:
    LOGGER.info("%s completed in %.2fs", label, time.perf_counter() - start)


def get_robinhood_mfa_code(credentials: dict[str, str]) -> str | None:
    mfa_code = credentials.get("ROBINHOOD_MFA_CODE")
    if mfa_code:
        return mfa_code

    totp_secret = credentials.get("ROBINHOOD_TOTP_SECRET")
    if not totp_secret:
        return None

    try:
        import pyotp
    except ImportError as exc:
        raise RuntimeError("Install pyotp to use ROBINHOOD_TOTP_SECRET.") from exc
    return pyotp.TOTP(totp_secret).now()


def login_robinhood(
    credentials: dict[str, str],
    *,
    store_session: bool = True,
) -> None:
    start = time.perf_counter()
    LOGGER.info("Robinhood login started")
    if rh is None:
        raise RuntimeError("Install robin-stocks to use Robinhood portfolio import.")

    username = credentials.get("ROBINHOOD_USERNAME")
    password = credentials.get("ROBINHOOD_PASSWORD")
    mfa_code = get_robinhood_mfa_code(credentials)
    if not username or not password:
        raise RuntimeError("Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD in credentials.md.")

    login_result = rh.login(
        username=username,
        password=password,
        mfa_code=mfa_code,
        store_session=store_session,
        pickle_path=credentials.get("ROBINHOOD_SESSION_DIR", ".robinhood_tokens"),
    )
    if not isinstance(login_result, dict) or "access_token" not in login_result:
        raise RuntimeError(
            "Robinhood login failed before holdings could be read. Check that "
            "ROBINHOOD_USERNAME is your Robinhood login email/username, "
            "ROBINHOOD_PASSWORD is current, and ROBINHOOD_MFA_CODE is a fresh "
            "6-digit code if MFA is enabled."
        )

    if login_result.get("mfa_required"):
        raise RuntimeError(
            "Robinhood requires MFA. Add the current 6-digit ROBINHOOD_MFA_CODE, "
            "or add ROBINHOOD_TOTP_SECRET if you configured an authenticator app."
        )
    log_timing("Robinhood login", start)


def get_robinhood_portfolio(
    credentials: dict[str, str],
    *,
    store_session: bool = True,
) -> list[Holding]:
    start = time.perf_counter()
    login_robinhood(credentials, store_session=store_session)
    holdings = rh.account.build_holdings()
    result = [
        Holding(
            ticker=symbol,
            quantity=float(data["quantity"]),
            avg_cost=float(data["average_buy_price"]),
            price=safe_float(data.get("price")),
            market_value=safe_float(data.get("equity")),
            equity_change=safe_float(data.get("equity_change")),
            percent_change=(safe_float(data.get("percent_change")) or 0) / 100,
            portfolio_weight=(safe_float(data.get("percentage")) or 0) / 100,
        )
        for symbol, data in holdings.items()
    ]
    LOGGER.info("Robinhood holdings loaded count=%s", len(result))
    log_timing("Robinhood holdings load", start)
    return result


def get_robinhood_account_totals(
    credentials: dict[str, str],
    *,
    store_session: bool = True,
) -> dict[str, float | None]:
    start = time.perf_counter()
    login_robinhood(credentials, store_session=store_session)
    profile = rh.profiles.load_portfolio_profile() or {}
    equity = safe_float(profile.get("equity"))
    market_value = safe_float(profile.get("market_value"))
    previous_close = safe_float(profile.get("adjusted_equity_previous_close"))
    today_change = equity - previous_close if equity is not None and previous_close is not None else None
    today_change_pct = today_change / previous_close if today_change is not None and previous_close else None
    result = {
        "equity": equity,
        "market_value": market_value,
        "previous_close": previous_close,
        "today_change": today_change,
        "today_change_pct": today_change_pct,
        "extended_hours_equity": safe_float(profile.get("extended_hours_equity")),
        "cash": safe_float(profile.get("withdrawable_amount")),
    }
    LOGGER.info("Robinhood account totals loaded market_value=%s equity=%s", market_value, equity)
    log_timing("Robinhood account totals load", start)
    return result


def get_manual_portfolio(credentials: dict[str, str]) -> list[Holding]:
    raw = credentials.get("MANUAL_HOLDINGS", "")
    holdings: list[Holding] = []
    for item in raw.split(","):
        parts = [part.strip() for part in item.split(":")]
        if len(parts) == 3:
            holdings.append(Holding(parts[0].upper(), float(parts[1]), float(parts[2])))
    return holdings


HOLDINGS_FILE_FORMATS = {
    "robinhood": {
        "ticker": ["Symbol"],
        "quantity": ["Quantity"],
        "avg_cost": ["Average Cost", "Average Cost Per Share"],
        "price": ["Price", "Current Price", "Last Price"],
        "market_value": ["Equity", "Market Value"],
    },
    "fidelity": {
        "ticker": ["Symbol"],
        "quantity": ["Quantity"],
        "avg_cost": ["Cost Basis Per Share", "Average Cost Basis"],
        "price": ["Last Price", "Current Price"],
        "market_value": ["Current Value", "Market Value"],
    },
    "schwab": {
        "ticker": ["Symbol"],
        "quantity": ["Quantity"],
        "avg_cost": ["Price Paid", "Cost Per Share"],
        "price": ["Price", "Market Price"],
        "market_value": ["Market Value"],
    },
    "etrade": {
        "ticker": ["Symbol"],
        "quantity": ["Qty", "Quantity"],
        "avg_cost": ["Avg Cost/Share", "Average Cost"],
        "price": ["Last Price", "Current Price"],
        "market_value": ["Market Value"],
    },
    "webull": {
        "ticker": ["Ticker"],
        "quantity": ["Total Qty", "Quantity"],
        "avg_cost": ["Avg Cost", "Average Cost"],
        "price": ["Current Price", "Last Price"],
        "market_value": ["Market Value"],
    },
    "ibkr": {
        "ticker": ["Financial Instrument", "Symbol"],
        "quantity": ["Quantity"],
        "avg_cost": ["Average Price", "Cost Basis Price"],
        "price": ["Close Price", "Market Price"],
        "market_value": ["Value", "Market Value"],
    },
    "generic": {
        "ticker": ["Ticker", "Symbol"],
        "quantity": ["Shares", "Quantity", "Qty"],
        "avg_cost": ["Average Cost", "Avg Cost", "Cost Basis Per Share", "Avg Cost/Share"],
        "price": ["Current Price", "Price", "Last Price"],
        "market_value": ["Market Value", "Value", "Current Value"],
    },
}


def normalize_holdings_file(path: str | Path, broker_hint: str | None = None, credentials: dict[str, str] | None = None) -> dict[str, Any]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".csv":
            frame = pd.read_csv(file_path)
            result = normalize_holdings_frame(frame, broker_hint)
            result["parser"] = "column-map"
            return result
        if suffix == ".xlsx":
            frame = pd.read_excel(file_path)
            result = normalize_holdings_frame(frame, broker_hint)
            result["parser"] = "column-map"
            return result
        if suffix == ".pdf":
            text = extract_pdf_text(file_path)
            return normalize_holdings_text_with_openai(text, credentials or {}, broker_hint, source_name=file_path.name)
        raise ValueError("Upload a CSV, XLSX, or PDF holdings file.")
    except Exception as exc:
        if suffix not in {".csv", ".xlsx", ".pdf"}:
            raise
        sample = holdings_file_sample(file_path, suffix)
        if not sample.strip():
            raise ValueError(f"{exc} The file did not contain readable holdings text.") from exc
        try:
            return normalize_holdings_text_with_openai(
                sample,
                credentials or {},
                broker_hint,
                source_name=file_path.name,
                prior_error=str(exc),
            )
        except Exception as fallback_exc:
            raise ValueError(f"{exc} OpenAI fallback also failed: {fallback_exc}") from fallback_exc


def normalize_holdings_frame(frame: pd.DataFrame, broker_hint: str | None = None) -> dict[str, Any]:
    frame = frame.dropna(how="all")
    if frame.empty:
        raise ValueError("The uploaded holdings file is empty.")

    frame.columns = [str(column).strip() for column in frame.columns]
    broker = detect_holdings_broker(frame.columns, broker_hint)
    mapping = resolve_holdings_columns(frame.columns, broker)
    holdings: list[Holding] = []
    preview: list[dict[str, Any]] = []

    for _, row in frame.iterrows():
        ticker = clean_ticker(row.get(mapping["ticker"]))
        quantity = parse_money_number(row.get(mapping["quantity"]))
        avg_cost = parse_money_number(row.get(mapping["avg_cost"]))
        if not ticker or quantity is None or avg_cost is None:
            continue
        price = parse_money_number(row.get(mapping.get("price"))) if mapping.get("price") else None
        market_value = parse_money_number(row.get(mapping.get("market_value"))) if mapping.get("market_value") else None
        if market_value is None and price is not None:
            market_value = price * quantity
        holdings.append(
            Holding(
                ticker=ticker,
                quantity=quantity,
                avg_cost=avg_cost,
                price=price,
                market_value=market_value,
            )
        )
        preview.append(
            {
                "ticker": ticker,
                "shares": quantity,
                "avg_cost": avg_cost,
                "current_price": price,
                "market_value": market_value,
            }
        )

    if not holdings:
        raise ValueError("No holdings rows could be parsed. Check the file columns or choose a broker override.")

    total_value = sum(holding.market_value or 0 for holding in holdings)
    if total_value:
        for holding in holdings:
            holding.portfolio_weight = (holding.market_value or 0) / total_value

    return {
        "broker": broker,
        "holdings": holdings,
        "preview": preview,
        "row_count": len(holdings),
        "columns": list(frame.columns),
    }


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to import PDF holdings statements.") from exc

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages[:8]:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("The uploaded PDF did not contain selectable holdings text.")
    return text[:18000]


def holdings_file_sample(path: Path, suffix: str) -> str:
    if suffix == ".pdf":
        return extract_pdf_text(path)
    try:
        if suffix == ".csv":
            frame = pd.read_csv(path, dtype=str, nrows=80)
            return frame.to_csv(index=False)
        if suffix == ".xlsx":
            sheets = pd.read_excel(path, dtype=str, nrows=80, sheet_name=None)
            chunks = []
            for name, frame in list(sheets.items())[:4]:
                chunks.append(f"Sheet: {name}\n{frame.to_csv(index=False)}")
            return "\n\n".join(chunks)
    except Exception as exc:
        LOGGER.warning("Could not build holdings fallback sample path=%s error=%s", path, exc)
    return ""


def normalize_holdings_text_with_openai(
    text: str,
    credentials: dict[str, str],
    broker_hint: str | None = None,
    *,
    source_name: str = "uploaded holdings",
    prior_error: str = "",
) -> dict[str, Any]:
    api_key = credentials.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in credentials.md to use the flexible holdings parser for irregular CSV, Excel, or PDF uploads.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai to use the flexible holdings parser.") from exc

    payload = {
        "source_name": source_name,
        "broker_hint": broker_hint or "",
        "prior_parser_error": prior_error,
        "sample": text[:18000],
        "instructions": (
            "Extract current portfolio holding rows from this brokerage export or statement. "
            "Use only rows that contain a listed security ticker plus share quantity and cost basis or average cost. "
            "Ignore cash, options, crypto, pending transactions, page footers, and totals unless they are clearly stock or ETF positions. "
            "If current price or market value is missing, return null for that field. "
            "Ticker must be a US-style ticker symbol, not a company name."
        ),
    }
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=credentials.get("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {
                "role": "system",
                "content": (
                    "You are a strict data extraction engine for portfolio holdings. "
                    "Return JSON only. Do not invent missing positions or prices."
                ),
            },
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "holdings_extraction",
                "strict": True,
                "schema": HOLDINGS_EXTRACTION_SCHEMA,
            }
        },
    )
    result = json.loads(response.output_text)
    holdings: list[Holding] = []
    preview: list[dict[str, Any]] = []
    for row in result.get("holdings", []):
        ticker = clean_ticker(row.get("ticker"))
        quantity = parse_money_number(row.get("shares"))
        avg_cost = parse_money_number(row.get("avg_cost"))
        if not ticker or quantity is None or avg_cost is None:
            continue
        price = parse_money_number(row.get("current_price"))
        market_value = parse_money_number(row.get("market_value"))
        if market_value is None and price is not None:
            market_value = price * quantity
        holding = Holding(ticker=ticker, quantity=quantity, avg_cost=avg_cost, price=price, market_value=market_value)
        holdings.append(holding)
        preview.append(
            {
                "ticker": ticker,
                "shares": quantity,
                "avg_cost": avg_cost,
                "current_price": price,
                "market_value": market_value,
            }
        )
    if not holdings:
        raise ValueError("OpenAI fallback did not find valid stock or ETF holdings rows.")

    total_value = sum(holding.market_value or 0 for holding in holdings)
    if total_value:
        for holding in holdings:
            holding.portfolio_weight = (holding.market_value or 0) / total_value

    return {
        "broker": normalize_broker_name(result.get("broker")) or normalize_broker_name(broker_hint) or "openai",
        "holdings": holdings,
        "preview": preview,
        "row_count": len(holdings),
        "columns": result.get("columns_used", []),
        "parser": "openai-fallback",
        "confidence": result.get("confidence"),
        "warnings": result.get("warnings", []),
    }


def detect_holdings_broker(columns: list[str], broker_hint: str | None = None) -> str:
    normalized = {normalize_column(column) for column in columns}
    hint = normalize_broker_name(broker_hint)
    if hint and hint in HOLDINGS_FILE_FORMATS:
        return hint
    best_name = "generic"
    best_score = 0
    for broker, mapping in HOLDINGS_FILE_FORMATS.items():
        required = mapping["ticker"] + mapping["quantity"] + mapping["avg_cost"]
        score = sum(1 for column in required if normalize_column(column) in normalized)
        if score > best_score:
            best_name = broker
            best_score = score
    return best_name


def resolve_holdings_columns(columns: list[str], broker: str) -> dict[str, str]:
    normalized_lookup = {normalize_column(column): column for column in columns}
    mapping = HOLDINGS_FILE_FORMATS.get(broker, HOLDINGS_FILE_FORMATS["generic"])
    resolved: dict[str, str] = {}
    for field in ("ticker", "quantity", "avg_cost"):
        column = first_matching_column(normalized_lookup, mapping[field], HOLDINGS_FILE_FORMATS["generic"].get(field, []))
        if not column:
            raise ValueError(f"Missing required holdings column for {field.replace('_', ' ')}.")
        resolved[field] = column
    for field in ("price", "market_value"):
        column = first_matching_column(normalized_lookup, mapping.get(field, []), HOLDINGS_FILE_FORMATS["generic"].get(field, []))
        if column:
            resolved[field] = column
    return resolved


def first_matching_column(lookup: dict[str, str], *candidate_groups: list[str]) -> str | None:
    for candidates in candidate_groups:
        for candidate in candidates:
            match = lookup.get(normalize_column(candidate))
            if match:
                return match
    return None


def normalize_column(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def normalize_broker_name(value: str | None) -> str | None:
    if not value:
        return None
    clean = normalize_column(value)
    aliases = {"etrade": "etrade", "e trade": "etrade", "interactivebrokers": "ibkr", "ibkr": "ibkr"}
    return aliases.get(clean, clean)


def clean_ticker(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw or raw in {"NAN", "NONE", "--"}:
        return ""
    match = re.search(r"[A-Z][A-Z0-9.\-]{0,9}", raw)
    return match.group(0).replace("-", ".") if match else ""


def parse_money_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip()
    if not text or text in {"--", "N/A", "n/a"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[$,%+,]", "", text).strip("() ")
    number = safe_float(text)
    if number is None:
        return None
    return -number if negative else number


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    response = requests.get(
        url,
        params={"range": period, "interval": "1d", "events": "history"},
        headers={"User-Agent": SERVER_USER_AGENT},
        timeout=12,
    )
    if response.ok:
        result = response.json().get("chart", {}).get("result") or []
        if result:
            timestamps = result[0].get("timestamp") or []
            quote = (result[0].get("indicators", {}).get("quote") or [{}])[0]
            closes = quote.get("close") or []
            frame = pd.DataFrame(
                {
                    "Open": quote.get("open") or closes,
                    "High": quote.get("high") or closes,
                    "Low": quote.get("low") or closes,
                    "Close": closes,
                },
                index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None),
            )
            frame = frame.dropna(subset=["Close"])
            if not frame.empty:
                return frame

    hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if hist.empty or "Close" not in hist:
        raise RuntimeError(f"No price history returned for {ticker}.")
    return hist.dropna(subset=["Close"])


def momentum_metrics(ticker: str) -> dict[str, float | None]:
    try:
        close = get_price_history(ticker, period="1y")["Close"]
    except Exception:
        return {"return_3m": None, "return_6m": None, "drawdown": None, "volatility_30d": None}

    returns = close.pct_change().dropna()
    return {
        "return_3m": safe_float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) > 63 else None,
        "return_6m": safe_float(close.iloc[-1] / close.iloc[-126] - 1) if len(close) > 126 else None,
        "drawdown": safe_float(close.iloc[-1] / close.max() - 1),
        "volatility_30d": safe_float(returns.tail(30).std() * math.sqrt(252)) if len(returns) >= 30 else None,
    }


def parse_rss_feed(url: str, limit: int = 20) -> list[dict[str, str]]:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError("Install feedparser to use RSS news feeds.") from exc

    response = requests.get(url, headers={"User-Agent": SERVER_USER_AGENT}, timeout=12)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    rows = []
    for entry in feed.entries[:limit]:
        rows.append(
            {
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", ""),
            }
        )
    return rows


def get_rss_news_items(ticker: str, limit: int = 5) -> list[dict[str, str]]:
    term = NEWS_TERMS.get(ticker.upper(), ticker)
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{term} stock OR earnings OR shares")
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        entries = parse_rss_feed(url, limit=max(limit * 2, 10))
    except Exception as exc:
        LOGGER.warning("RSS news unavailable ticker=%s error=%s", ticker, exc)
        return []

    items = []
    for entry in entries:
        title = entry.get("title", "")
        if title and (term.lower() in title.lower() or ticker.lower() in title.lower()):
            items.append(entry)
        if len(items) == limit:
            break
    return items


def get_rss_news_titles(ticker: str, limit: int = 5) -> list[str]:
    return [item["title"] for item in get_rss_news_items(ticker, limit)]


def get_news_items(ticker: str, credentials: dict[str, str], limit: int = 5) -> list[dict[str, str]]:
    api_key = credentials.get("NEWS_API_KEY")
    if not api_key:
        return get_rss_news_items(ticker, limit)

    term = NEWS_TERMS.get(ticker.upper(), ticker)
    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": f'"{term}" AND (stock OR shares OR earnings OR market)',
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max(limit * 3, 10),
                "apiKey": api_key,
            },
            headers={"User-Agent": SERVER_USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("NewsAPI unavailable ticker=%s error=%s", ticker, exc)
        return get_rss_news_items(ticker, limit)
    articles = response.json().get("articles", [])
    items = []
    for article in articles:
        title = article.get("title", "")
        source = (article.get("source") or {}).get("name", "")
        text = f"{title} {source}".lower()
        if title and (term.lower() in text or ticker.lower() in text):
            items.append(
                {
                    "title": title,
                    "link": article.get("url", ""),
                    "published": article.get("publishedAt", ""),
                    "source": source,
                }
            )
        if len(items) == limit:
            break
    return items or get_rss_news_items(ticker, limit)


def get_news_titles(ticker: str, credentials: dict[str, str], limit: int = 5) -> list[str]:
    return [item["title"] for item in get_news_items(ticker, credentials, limit)]


def get_earnings_proximity(ticker: str) -> dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
    except Exception:
        return {"earnings_date": None, "days_to_earnings": None}

    raw_date = None
    if isinstance(calendar, dict):
        raw_date = calendar.get("Earnings Date") or calendar.get("EarningsDate")
    elif hasattr(calendar, "loc"):
        for key in ["Earnings Date", "EarningsDate"]:
            if key in calendar.index:
                raw_date = calendar.loc[key][0] if hasattr(calendar.loc[key], "__len__") else calendar.loc[key]
                break

    if isinstance(raw_date, (list, tuple)) and raw_date:
        raw_date = raw_date[0]
    if raw_date is None:
        try:
            earnings_dates = stock.get_earnings_dates(limit=4)
            if earnings_dates is not None and not earnings_dates.empty:
                future_dates = [idx.date() for idx in earnings_dates.index if idx.date() >= date.today()]
                if future_dates:
                    earnings_date = min(future_dates)
                    return {"earnings_date": earnings_date.isoformat(), "days_to_earnings": (earnings_date - date.today()).days}
        except Exception:
            pass
        return {"earnings_date": None, "days_to_earnings": None}

    try:
        earnings_date = pd.to_datetime(raw_date).date()
    except Exception:
        return {"earnings_date": None, "days_to_earnings": None}
    return {"earnings_date": earnings_date.isoformat(), "days_to_earnings": (earnings_date - date.today()).days}


LLM_SENTIMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_sentiment": {"type": "number"},
        "confidence": {"type": "number"},
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["overall_sentiment", "confidence", "key_risks", "summary"],
    "additionalProperties": False,
}

MASTER_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "plain_english_summary": {"type": "string"},
        "portfolio_advice": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "priority": {"type": "string"},
                    "action": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["ticker", "priority", "action", "rationale"],
                "additionalProperties": False,
            },
        },
        "sentiment": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "label": {"type": "string"},
                    "score": {"type": "number"},
                    "confidence": {"type": "number"},
                    "key_signals": {"type": "array", "items": {"type": "string"}},
                    "alpha_implication": {"type": "string"},
                    "risk_flags": {"type": "array", "items": {"type": "string"}},
                    "source_note": {"type": "string"},
                },
                "required": [
                    "ticker",
                    "label",
                    "score",
                    "confidence",
                    "key_signals",
                    "alpha_implication",
                    "risk_flags",
                    "source_note",
                ],
                "additionalProperties": False,
            },
        },
        "strategy_advice": {"type": "string"},
    },
    "required": ["plain_english_summary", "portfolio_advice", "sentiment", "strategy_advice"],
    "additionalProperties": False,
}

DYNAMIC_UNIVERSE_SCHEMA = {
    "type": "object",
    "properties": {
        "tickers": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["tickers", "rationale"],
    "additionalProperties": False,
}

HOLDINGS_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "broker": {"type": "string"},
        "confidence": {"type": "number"},
        "columns_used": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "holdings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "shares": {"type": "number"},
                    "avg_cost": {"type": "number"},
                    "current_price": {"type": ["number", "null"]},
                    "market_value": {"type": ["number", "null"]},
                },
                "required": ["ticker", "shares", "avg_cost", "current_price", "market_value"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["broker", "confidence", "columns_used", "warnings", "holdings"],
    "additionalProperties": False,
}


def llm_sentiment(ticker: str, headlines: list[str], credentials: dict[str, str]) -> dict[str, Any]:
    api_key = credentials.get("OPENAI_API_KEY")
    if not api_key or not headlines:
        return {"overall_sentiment": None, "confidence": None, "key_risks": [], "summary": ""}

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai to use OPENAI_API_KEY LLM sentiment.") from exc

    client = OpenAI(api_key=api_key)
    model = credentials.get("OPENAI_MODEL", "gpt-4o-mini")
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are analyzing public financial headlines for educational portfolio "
                    "decision support. Return conservative JSON only. Do not give personalized "
                    "financial advice or trade instructions."
                ),
            },
            {
                "role": "user",
                "content": f"Ticker: {ticker}\nHeadlines:\n" + "\n".join(f"- {h}" for h in headlines[:5]),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "headline_sentiment",
                "strict": True,
                "schema": LLM_SENTIMENT_SCHEMA,
            }
        },
    )
    return json.loads(response.output_text)


def openai_master_analysis(
    holdings_report: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    credentials: dict[str, str],
    *,
    strategy_state: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    api_key = credentials.get("OPENAI_API_KEY")
    if not api_key:
        return {"plain_english_summary": "", "portfolio_advice": [], "sentiment": [], "strategy_advice": ""}

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai to use OPENAI_API_KEY master analysis.") from exc

    compact_holdings = [
        {
            "ticker": row.get("ticker"),
            "weight": row.get("portfolio_weight"),
            "gain": row.get("unrealized_gain"),
            "signal": row.get("signal"),
            "final_score": row.get("final_score"),
            "action": row.get("action"),
            "return_3m": row.get("return_3m"),
            "drawdown": row.get("drawdown"),
            "headlines": row.get("news", [])[:5],
        }
        for row in holdings_report
        if not row.get("error")
    ]
    compact_ideas = [
        {
            "ticker": idea.get("ticker"),
            "score": idea.get("score"),
            "reasons": idea.get("reasons", [])[:4],
            "headlines": idea.get("news", [])[:5],
        }
        for idea in ideas
        if "error" not in idea
    ]

    client = OpenAI(api_key=api_key)
    model = credentials.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = {
        "holdings": compact_holdings,
        "buy_candidates": compact_ideas,
        "strategy_state": strategy_state or [],
        "instructions": (
            "Use supplied portfolio, quant, and headline data only. If headlines are missing, "
            "do not invent current news; provide model-generated context from the supplied "
            "quant data and clearly mark source_note as 'OpenAI fallback: no live headlines supplied'. "
            "Write for a normal investor, not a quant researcher. Use short, direct sentences. "
            "Avoid jargon unless the supplied data requires it. Avoid em dashes, rhetorical questions, "
            "and formal filler words. Keep output concise and educational, not personalized trading advice."
        ),
    }
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a conservative quant portfolio analyst. Return JSON only. "
                    "Do not claim access to live news unless headlines are provided."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, default=str)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "portfolio_master_analysis",
                "strict": True,
                "schema": MASTER_ANALYSIS_SCHEMA,
            }
        },
    )
    return json.loads(response.output_text)


def discover_rss_tickers(limit: int = 12) -> dict[str, Any]:
    headlines = []
    for feed_url in DEFAULT_RSS_FEEDS:
        try:
            headlines.extend(parse_rss_feed(feed_url, limit=50))
        except Exception as exc:
            LOGGER.warning("RSS discovery feed failed url=%s error=%s", feed_url, exc)

    scores: dict[str, int] = {}
    matched_headlines: dict[str, list[str]] = {}
    for item in headlines:
        title = item.get("title", "")
        for term, ticker in DISCOVERY_TERMS.items():
            if term.lower() in title.lower():
                scores[ticker] = scores.get(ticker, 0) + 1
                matched_headlines.setdefault(ticker, []).append(title)
    ranked = sorted(scores, key=scores.get, reverse=True)[:limit]
    return {"tickers": ranked, "headlines": matched_headlines, "source": "Google News RSS"}


def openai_dynamic_universe(
    holdings: list[Holding],
    rss_discovery: dict[str, Any],
    credentials: dict[str, str],
    limit: int = 12,
) -> dict[str, Any]:
    api_key = credentials.get("OPENAI_API_KEY")
    if not api_key:
        return {"tickers": [], "rationale": ""}

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai to use dynamic universe generation.") from exc

    payload = {
        "current_holdings": [holding.ticker for holding in holdings],
        "rss_candidate_tickers": rss_discovery.get("tickers", []),
        "rss_headlines_by_ticker": rss_discovery.get("headlines", {}),
        "max_tickers": limit,
        "instructions": (
            "Return liquid US-listed tickers suitable for monitoring as buy candidates. "
            "Prefer tickers connected to supplied headlines or natural peers/hedges for current holdings. "
            "Do not include current holdings unless they are broad ETFs useful as benchmarks."
        ),
    }
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=credentials.get("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {"role": "system", "content": "Return JSON only. Use ticker symbols, not company names."},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "dynamic_universe",
                "strict": True,
                "schema": DYNAMIC_UNIVERSE_SCHEMA,
            }
        },
    )
    result = json.loads(response.output_text)
    result["tickers"] = [ticker.upper().strip() for ticker in result.get("tickers", []) if ticker.strip()][:limit]
    return result


def build_dynamic_universe(
    holdings: list[Holding],
    credentials: dict[str, str],
    *,
    holdings_report: list[dict[str, Any]] | None = None,
    extra_tickers: list[str] | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    extra_tickers = [ticker.upper().strip() for ticker in (extra_tickers or []) if ticker.strip()]
    rss = discover_rss_tickers(limit=limit)
    owned = {holding.ticker.upper() for holding in holdings}
    portfolio_candidates = portfolio_peer_candidates(holdings_report or [], limit=limit)
    ai = openai_dynamic_universe(holdings, rss, credentials, limit=limit)
    tickers = []
    for source in [ai.get("tickers", []), portfolio_candidates, extra_tickers, rss.get("tickers", [])]:
        for ticker in source:
            ticker = ticker.upper().strip()
            if ticker and ticker not in tickers and ticker not in owned:
                tickers.append(ticker)
    if "SPY" not in tickers:
        tickers.append("SPY")
    return {
        "tickers": tickers[:limit],
        "portfolio_candidates": portfolio_candidates,
        "rss": rss,
        "llm_rationale": ai.get("rationale", ""),
        "source": "portfolio peers + optional OpenAI + Google News RSS",
    }


def portfolio_peer_candidates(holdings_report: list[dict[str, Any]], limit: int = 12) -> list[str]:
    sector_peers = {
        "Technology": ["MSFT", "AAPL", "NVDA", "AVGO", "AMD", "CRM"],
        "Communication Services": ["GOOGL", "META", "NFLX", "TMUS"],
        "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
        "Consumer Defensive": ["COST", "WMT", "PG", "KO"],
        "Financial Services": ["JPM", "V", "MA", "BRK.B"],
        "Healthcare": ["LLY", "UNH", "JNJ", "ABBV"],
        "Industrials": ["CAT", "GE", "HON", "UNP"],
        "Energy": ["XOM", "CVX", "COP"],
        "Utilities": ["NEE", "SO", "DUK"],
        "Real Estate": ["PLD", "AMT", "O"],
        "Basic Materials": ["LIN", "SHW", "FCX"],
        "Unknown": ["SPY", "VTI", "QQQ", "VEA", "BND"],
    }
    owned = {str(row.get("ticker", "")).upper() for row in holdings_report}
    sector_weights: dict[str, float] = {}
    for row in holdings_report:
        sector = str(row.get("sector") or "Unknown")
        sector_weights[sector] = sector_weights.get(sector, 0) + float(row.get("portfolio_weight") or 0)
    ranked_sectors = sorted(sector_weights, key=sector_weights.get, reverse=True) or ["Unknown"]
    candidates: list[str] = []
    for sector in ranked_sectors:
        for ticker in sector_peers.get(sector, sector_peers["Unknown"]):
            normalized = ticker.replace(".", "-")
            if normalized not in owned and normalized not in candidates:
                candidates.append(normalized)
            if len(candidates) >= limit:
                return candidates
    for ticker in ["SPY", "VTI", "QQQ", "VEA", "BND"]:
        if ticker not in owned and ticker not in candidates:
            candidates.append(ticker)
    return candidates[:limit]


def simple_news_sentiment(titles: list[str]) -> float:
    if not titles:
        return 0.0

    score = 0
    words_seen = 0
    for title in titles:
        words = re.findall(r"[A-Za-z']+", title.lower())
        words_seen += len(words)
        score += sum(1 for word in words if word in POSITIVE_WORDS)
        score -= sum(1 for word in words if word in NEGATIVE_WORDS)
    return max(-1.0, min(1.0, score / max(5, words_seen / 8)))


def stock_snapshot(ticker: str, credentials: dict[str, str]) -> dict[str, Any]:
    start = time.perf_counter()
    LOGGER.info("Stock snapshot started ticker=%s", ticker)
    hist = get_price_history(ticker)
    close = hist["Close"]
    returns = close.pct_change().dropna()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = yf.Ticker(ticker).get_info()
    except Exception:
        info = {}
    news_items = get_news_items(ticker, credentials)
    titles = [item["title"] for item in news_items]

    price = safe_float(close.iloc[-1])
    high_52w = safe_float(close.tail(252).max())
    low_52w = safe_float(close.tail(252).min())
    sma_50 = safe_float(close.tail(50).mean()) if len(close) >= 50 else None
    sma_200 = safe_float(close.tail(200).mean()) if len(close) >= 200 else None
    momentum_6m = safe_float(close.iloc[-1] / close.iloc[-126] - 1) if len(close) > 126 else None
    momentum_12_1 = safe_float(close.iloc[-22] / close.iloc[-252] - 1) if len(close) > 252 else momentum_6m
    volatility = safe_float(returns.tail(63).std() * math.sqrt(252)) if len(returns) >= 63 else None
    downside = returns.tail(126)
    downside_vol = safe_float(downside[downside < 0].std() * math.sqrt(252)) if len(downside) else None
    max_drawdown = safe_float((close / close.cummax() - 1).tail(252).min())
    near_high = safe_float(price / high_52w) if price and high_52w else None
    roe = safe_float(info.get("returnOnEquity"))
    margin = safe_float(info.get("profitMargins"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    forward_pe = safe_float(info.get("forwardPE"))
    target = safe_float(info.get("targetMeanPrice"))
    target_gap = safe_float(target / price - 1) if target and price else None

    result = {
        "ticker": ticker,
        "name": info.get("shortName") or ticker,
        "price": price,
        "momentum_6m": momentum_6m,
        "momentum_12_1": momentum_12_1,
        "volatility": volatility,
        "downside_volatility": downside_vol,
        "max_drawdown": max_drawdown,
        "near_52w_high": near_high,
        "trend_ok": bool(price and sma_50 and sma_200 and price > sma_50 > sma_200),
        "roe": roe,
        "profit_margin": margin,
        "revenue_growth": revenue_growth,
        "forward_pe": forward_pe,
        "target_gap": target_gap,
        "recommendation": info.get("recommendationKey"),
        "sector": info.get("sector") or "Unknown",
        "news_sentiment": simple_news_sentiment(titles),
        "news": titles,
        "news_items": news_items,
        **momentum_metrics(ticker),
        **get_earnings_proximity(ticker),
    }
    LOGGER.info("Stock snapshot completed ticker=%s price=%s", ticker, price)
    log_timing(f"Stock snapshot {ticker}", start)
    return result


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_candidate(snapshot: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    momentum = snapshot["momentum_12_1"]
    if momentum is not None:
        score += clamp(momentum / 0.35, -1.2, 1.5) * 1.4
        reasons.append(f"12-1 momentum {pct(momentum)}")

    if snapshot["trend_ok"]:
        score += 0.8
        reasons.append("price above rising 50/200 day trend")

    near_high = snapshot["near_52w_high"]
    if near_high is not None:
        score += clamp((near_high - 0.85) / 0.15, -0.8, 0.8)
        reasons.append(f"{pct(near_high)} of 52w high")

    volatility = snapshot["volatility"]
    if volatility is not None:
        score -= clamp((volatility - 0.28) / 0.25, -0.3, 1.0)
        reasons.append(f"annualized vol {pct(volatility)}")

    drawdown = snapshot["max_drawdown"]
    if drawdown is not None and drawdown < -0.25:
        score -= 0.8
        reasons.append(f"large 1y drawdown {pct(drawdown)}")

    for key, label, weight in [
        ("roe", "ROE", 0.7),
        ("profit_margin", "margin", 0.5),
        ("revenue_growth", "revenue growth", 0.5),
    ]:
        value = snapshot[key]
        if value is not None:
            score += clamp(value / 0.25, -0.5, 1.0) * weight
            reasons.append(f"{label} {pct(value)}")

    forward_pe = snapshot["forward_pe"]
    if forward_pe is not None:
        if forward_pe <= 35:
            score += 0.4
        elif forward_pe > 55:
            score -= 0.5
        reasons.append(f"forward P/E {forward_pe:.1f}")

    target_gap = snapshot["target_gap"]
    if target_gap is not None:
        score += clamp(target_gap / 0.25, -1.0, 1.0) * 0.7
        reasons.append(f"analyst target gap {pct(target_gap)}")

    recommendation = snapshot["recommendation"]
    if recommendation in {"buy", "strong_buy"}:
        score += 0.4
        reasons.append(f"analyst consensus {recommendation}")
    elif recommendation in {"sell", "strong_sell"}:
        score -= 0.6
        reasons.append(f"analyst consensus {recommendation}")

    news_sentiment = snapshot["news_sentiment"]
    if news_sentiment:
        score += news_sentiment * 0.4
        reasons.append(f"news sentiment {news_sentiment:+.2f}")

    return round(score, 2), reasons[:8]


def build_signal(snapshot: dict[str, Any]) -> int:
    score, _ = score_candidate(snapshot)
    if score >= 4.0:
        return 3
    if score >= 2.5:
        return 2
    if score >= 1.0:
        return 1
    if score <= -1.0:
        return -1
    return 0


def final_score(quant_signal: int, sentiment: float | None, days_to_earnings: int | None) -> float:
    normalized_quant = quant_signal / 3
    score = 0.7 * normalized_quant + 0.3 * (sentiment or 0)
    if days_to_earnings is not None and 0 <= days_to_earnings < 10:
        score -= 0.25
    return round(score, 2)


def decide_action(
    ticker: str,
    signal: int,
    unrealized_gain: float | None = None,
    portfolio_weight: float | None = None,
    days_to_earnings: int | None = None,
) -> str:
    ticker = ticker.upper()
    if days_to_earnings is not None and 0 <= days_to_earnings < 10 and portfolio_weight and portfolio_weight >= 0.10:
        return "REVIEW EVENT RISK BEFORE EARNINGS"
    if portfolio_weight is not None and portfolio_weight >= 0.25:
        if signal <= 1 and unrealized_gain is not None and unrealized_gain > 0.10:
            return "TRIM 5-10% / REDUCE CONCENTRATION"
        return "HOLD / DO NOT ADD, POSITION IS CONCENTRATED"
    if portfolio_weight is not None and portfolio_weight >= 0.15 and signal <= 0:
        return "HOLD / DO NOT ADD, WATCH CONCENTRATION"
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


def rank_buy_ideas(
    watchlist: list[str],
    credentials: dict[str, str],
    limit: int,
    exclude: set[str] | None = None,
    progress_callback: Any = None,
) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    exclude = exclude or set()
    candidates = [ticker for ticker in watchlist if ticker.upper() not in exclude]
    total = len(candidates)
    for index, ticker in enumerate(candidates, start=1):
        if progress_callback:
            progress_callback(index, total, f"Ranking buy candidate {ticker}")
        if ticker.upper() in exclude:
            continue
        try:
            snapshot = stock_snapshot(ticker, credentials)
            score, reasons = score_candidate(snapshot)
            snapshot["score"] = score
            snapshot["reasons"] = reasons
            ideas.append(snapshot)
        except Exception as exc:
            LOGGER.exception("Buy candidate failed ticker=%s", ticker)
            ideas.append({"ticker": ticker, "score": -999, "error": str(exc), "reasons": []})
    return sorted(ideas, key=lambda item: item["score"], reverse=True)[:limit]


def analyze_holdings(
    holdings: list[Holding],
    credentials: dict[str, str],
    *,
    use_llm: bool = False,
    progress_callback: Any = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(holdings)
    for index, holding in enumerate(holdings, start=1):
        if progress_callback:
            progress_callback(index, total, f"Analyzing holding {holding.ticker}")
        try:
            snapshot = stock_snapshot(holding.ticker, credentials)
            signal = build_signal(snapshot)
            display_price = holding.price or snapshot["price"]
            gain = holding.percent_change
            if gain is None and display_price and holding.avg_cost:
                gain = display_price / holding.avg_cost - 1
            market_value = holding.market_value
            if market_value is None and display_price:
                market_value = display_price * holding.quantity
            llm = llm_sentiment(holding.ticker, snapshot["news"], credentials) if use_llm else {}
            rows.append(
                {
                    "ticker": holding.ticker,
                    "quantity": holding.quantity,
                    "avg_cost": holding.avg_cost,
                    "price": display_price,
                    "market_value": market_value,
                    "portfolio_weight": holding.portfolio_weight,
                    "equity_change": holding.equity_change,
                    "unrealized_gain": gain,
                    "signal": signal,
                    "llm_sentiment": llm.get("overall_sentiment"),
                    "llm_confidence": llm.get("confidence"),
                    "llm_summary": llm.get("summary", ""),
                    "llm_risks": llm.get("key_risks", []),
                    "news": snapshot.get("news", []),
                    "news_items": snapshot.get("news_items", []),
                    "sector": snapshot.get("sector", "Unknown"),
                    "earnings_date": snapshot.get("earnings_date"),
                    "days_to_earnings": snapshot.get("days_to_earnings"),
                    "return_3m": snapshot.get("return_3m"),
                    "return_6m": snapshot.get("return_6m"),
                    "drawdown": snapshot.get("drawdown"),
                    "volatility_30d": snapshot.get("volatility_30d"),
                    "final_score": final_score(signal, llm.get("overall_sentiment"), snapshot.get("days_to_earnings")),
                    "action": "",
                    "error": "",
                }
            )
        except Exception as exc:
            LOGGER.exception("Holding analysis failed ticker=%s", holding.ticker)
            rows.append(
                {
                    "ticker": holding.ticker,
                    "quantity": holding.quantity,
                    "avg_cost": holding.avg_cost,
                    "price": None,
                    "market_value": None,
                    "portfolio_weight": None,
                    "unrealized_gain": None,
                    "signal": None,
                    "action": "DATA UNAVAILABLE",
                    "error": str(exc),
                }
            )
    total_value = sum(row["market_value"] or 0 for row in rows)
    for row in rows:
        if row.get("error"):
            continue
        if row["portfolio_weight"] is None:
            row["portfolio_weight"] = (row["market_value"] or 0) / total_value if total_value else None
        row["action"] = decide_action(
            row["ticker"],
            row["signal"],
            row["unrealized_gain"],
            row["portfolio_weight"],
            row["days_to_earnings"],
        )
    return rows


def portfolio_summary(
    holdings: list[dict[str, Any]],
    account_totals: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    valid = [row for row in holdings if not row.get("error") and row.get("market_value")]
    account_totals = account_totals or {}
    total_value = account_totals.get("market_value") or sum(row["market_value"] for row in valid)
    concentrated = [
        row for row in valid if row.get("portfolio_weight") is not None and row["portfolio_weight"] >= 0.15
    ]
    weak = [row for row in valid if row.get("signal") is not None and row["signal"] <= 0]
    return {
        "total_value": total_value,
        "account_equity": account_totals.get("equity"),
        "previous_close": account_totals.get("previous_close"),
        "today_change": account_totals.get("today_change"),
        "today_change_pct": account_totals.get("today_change_pct"),
        "cash": account_totals.get("cash"),
        "positions": len(valid),
        "concentrated": sorted(concentrated, key=lambda row: row["portfolio_weight"], reverse=True),
        "weak": sorted(weak, key=lambda row: row["portfolio_weight"] or 0, reverse=True),
    }


def scenario_impact(holdings: list[dict[str, Any]], shock_ticker: str, drop_pct: float) -> float | None:
    before = sum(row.get("market_value") or 0 for row in holdings if not row.get("error"))
    if not before:
        return None
    after = 0.0
    for row in holdings:
        value = row.get("market_value") or 0
        if row.get("ticker") == shock_ticker:
            value *= 1 - drop_pct
        after += value
    return (after - before) / before


def tax_estimate(row: dict[str, Any], trim_pct: float, tax_rate: float) -> dict[str, float]:
    market_value = row.get("market_value") or 0
    gain = row.get("unrealized_gain") or 0
    proceeds = market_value * trim_pct
    cost_basis_sold = proceeds / (1 + gain) if gain > -0.99 else proceeds
    taxable_gain = max(0.0, proceeds - cost_basis_sold)
    estimated_tax = taxable_gain * tax_rate
    return {
        "proceeds": proceeds,
        "cost_basis_sold": cost_basis_sold,
        "taxable_gain": taxable_gain,
        "estimated_tax": estimated_tax,
        "net_reinvestable": proceeds - estimated_tax,
    }


def today_actions(holdings: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    actionable = []
    for row in holdings:
        if row.get("error"):
            continue
        weight = row.get("portfolio_weight") or 0
        gain = max(row.get("unrealized_gain") or 0, 0)
        urgency = weight * (1 + gain) * (1 - (row.get("final_score") or 0))
        if "TRIM" in row.get("action", "") or "DO NOT ADD" in row.get("action", "") or weight >= 0.15:
            actionable.append({**row, "urgency": urgency})
    return sorted(actionable, key=lambda row: row["urgency"], reverse=True)[:limit]


def rsi(close: pd.Series, window: int = 14) -> float | None:
    delta = close.diff().dropna()
    if len(delta) < window:
        return None
    gains = delta.clip(lower=0).tail(window).mean()
    losses = (-delta.clip(upper=0)).tail(window).mean()
    if losses == 0:
        return 100.0
    return 100 - (100 / (1 + gains / losses))


def factor_snapshot(ticker: str) -> dict[str, float | None]:
    try:
        close = get_price_history(ticker, period="18mo")["Close"]
    except Exception:
        return {"ticker": ticker}
    returns = close.pct_change().dropna()
    factor = {"ticker": ticker}
    factor["momentum_12_1"] = safe_float(close.iloc[-22] / close.iloc[-252] - 1) if len(close) > 252 else None
    factor["momentum_6_1"] = safe_float(close.iloc[-22] / close.iloc[-126] - 1) if len(close) > 126 else None
    ret_20 = close.pct_change(20)
    factor["price_acceleration"] = safe_float(ret_20.iloc[-1] - ret_20.iloc[-21]) if len(ret_20.dropna()) > 21 else None
    factor["mean_reversion_5d"] = safe_float(-close.pct_change(5).iloc[-1]) if len(close) > 5 else None
    current_rsi = rsi(close)
    factor["rsi_reversal"] = safe_float((50 - current_rsi) / 50) if current_rsi is not None else None
    vol = returns.tail(20).std()
    ret_10 = close.pct_change(10).iloc[-1] if len(close) > 10 else None
    factor["vol_adj_mean_reversion"] = safe_float(-ret_10 / (vol * math.sqrt(10))) if vol and ret_10 is not None else None
    factor["idiosyncratic_vol"] = safe_float(returns.tail(63).std() * math.sqrt(252)) if len(returns) >= 63 else None
    factor["forward_21d_return_proxy"] = safe_float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) > 22 else None
    return factor


def compute_ic(factor_series: pd.Series, forward_returns: pd.Series) -> float | None:
    frame = pd.concat([factor_series, forward_returns], axis=1).dropna()
    if len(frame) < 4:
        return None
    return safe_float(frame.iloc[:, 0].corr(frame.iloc[:, 1], method="spearman"))


def alpha_factor_explorer(universe: list[str]) -> dict[str, Any]:
    rows = [factor_snapshot(ticker) for ticker in sorted(set(universe))]
    frame = pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()
    if frame.empty or "forward_21d_return_proxy" not in frame:
        return {"factor_table": pd.DataFrame(), "ic_table": pd.DataFrame(), "history": pd.DataFrame()}

    factors = [column for column in frame.columns if column != "forward_21d_return_proxy"]
    ic_rows = []
    for factor in factors:
        ic_value = compute_ic(frame[factor], frame["forward_21d_return_proxy"])
        if ic_value is None:
            continue
        ic_rows.append(
            {
                "date": date.today().isoformat(),
                "factor_name": factor,
                "ic_value": ic_value,
                "universe_size": int(frame[[factor, "forward_21d_return_proxy"]].dropna().shape[0]),
                "status": "Decayed" if abs(ic_value) < 0.02 else "Active",
            }
        )
    ic_table = pd.DataFrame(ic_rows)
    if not ic_table.empty:
        log_path = Path("factor_ic_log.csv")
        header = not log_path.exists()
        ic_table.to_csv(log_path, mode="a", header=header, index=False)
        history = pd.read_csv(log_path)
    else:
        history = pd.DataFrame()
    return {"factor_table": frame.reset_index(), "ic_table": ic_table, "history": history}


def run_backtest(
    strategy: str,
    universe: list[str],
    lookback_years: int = 3,
    benchmark: str = "SPY",
) -> dict[str, Any]:
    tickers = sorted(set([ticker for ticker in universe if ticker] + [benchmark]))
    period = f"{lookback_years}y"
    prices = {}
    for ticker in tickers:
        try:
            prices[ticker] = get_price_history(ticker, period=period)["Close"]
        except Exception:
            LOGGER.exception("Backtest price fetch failed ticker=%s", ticker)
    close = pd.DataFrame(prices).dropna(how="all").ffill().dropna(axis=1, how="all")
    if close.empty or benchmark not in close:
        return {"metrics": {}, "curve": pd.DataFrame(), "monthly": pd.DataFrame()}

    asset_cols = [col for col in close.columns if col != benchmark]
    returns = close[asset_cols].pct_change()
    benchmark_returns = close[benchmark].pct_change().fillna(0)
    rebalance_dates = close.resample("ME").last().index
    daily_strategy_returns = pd.Series(0.0, index=close.index)
    current_weights = pd.Series(0.0, index=asset_cols)
    for current_date in close.index:
        if current_date in rebalance_dates or current_weights.abs().sum() == 0:
            lookback = close.loc[:current_date, asset_cols].tail(252)
            if len(lookback) > 126:
                if strategy == "Short-term mean reversion":
                    signal = -lookback.pct_change(5).iloc[-1]
                elif strategy == "Multi-factor composite":
                    mom = lookback.iloc[-22] / lookback.iloc[0] - 1
                    rev = -lookback.pct_change(5).iloc[-1]
                    signal = mom.rank(pct=True) + rev.rank(pct=True)
                else:
                    signal = lookback.iloc[-22] / lookback.iloc[0] - 1
                longs = signal.dropna().sort_values(ascending=False).head(max(1, len(signal.dropna()) // 3)).index
                current_weights = pd.Series(0.0, index=asset_cols)
                current_weights.loc[longs] = 1 / len(longs)
        if current_date in returns.index:
            daily_strategy_returns.loc[current_date] = (returns.loc[current_date].fillna(0) * current_weights).sum()

    curve = pd.DataFrame(
        {
            "strategy": (1 + daily_strategy_returns.fillna(0)).cumprod(),
            "benchmark": (1 + benchmark_returns).cumprod(),
        }
    )
    total_return = curve["strategy"].iloc[-1] - 1
    vol = daily_strategy_returns.std() * math.sqrt(252)
    sharpe = safe_float((daily_strategy_returns.mean() * 252) / vol) if vol else None
    drawdown = safe_float((curve["strategy"] / curve["strategy"].cummax() - 1).min())
    monthly = daily_strategy_returns.resample("ME").apply(lambda x: (1 + x).prod() - 1).to_frame("return")
    monthly["month"] = monthly.index.strftime("%Y-%m")
    metrics = {
        "total_return": safe_float(total_return),
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "monthly_win_rate": safe_float((monthly["return"] > 0).mean()) if not monthly.empty else None,
    }
    return {"metrics": metrics, "curve": curve.reset_index(names="date"), "monthly": monthly.reset_index(drop=True)}


def log_signal(ticker: str, strategy: str, action: str, score: float, status: str = "Active") -> None:
    path = Path("signals_log.csv")
    row = pd.DataFrame(
        [
            {
                "date": datetime.now(timezone.utc).astimezone().isoformat(),
                "ticker": ticker,
                "strategy": strategy,
                "action": action,
                "score": score,
                "status": status,
            }
        ]
    )
    row.to_csv(path, mode="a", header=not path.exists(), index=False)


def strategy_monitor(holdings_report: list[dict[str, Any]]) -> dict[str, Any]:
    strategies = [
        {"name": "Momentum L/S", "signal_key": "return_6m"},
        {"name": "Mean reversion", "signal_key": "drawdown"},
        {"name": "LLM sentiment overlay", "signal_key": "llm_sentiment"},
        {"name": "Multi-factor composite", "signal_key": "final_score"},
    ]
    rows = []
    for strategy in strategies:
        values = [row.get(strategy["signal_key"]) for row in holdings_report if row.get(strategy["signal_key"]) is not None]
        avg_signal = sum(values) / len(values) if values else 0
        status = "Active" if avg_signal > 0.05 else "Watch" if avg_signal > -0.05 else "Defensive"
        rows.append(
            {
                "strategy": strategy["name"],
                "avg_signal": avg_signal,
                "status": status,
                "risk_weight": abs(avg_signal) + 0.1,
                "ytd_return_proxy": avg_signal,
            }
        )
    total_risk = sum(row["risk_weight"] for row in rows) or 1
    for row in rows:
        row["risk_attribution"] = row["risk_weight"] / total_risk
    signal_rows = []
    now = datetime.now(timezone.utc).astimezone().isoformat()
    for row in holdings_report:
        if row.get("action") and not row.get("error"):
            log_signal(row["ticker"], "Portfolio action engine", row["action"], row.get("final_score") or 0)
            signal_rows.append(
                {
                    "date": now,
                    "ticker": row["ticker"],
                    "strategy": "Portfolio action engine",
                    "action": row["action"],
                    "score": row.get("final_score") or 0,
                    "status": "Active",
                }
            )
    signals = pd.DataFrame(signal_rows)
    blended_sharpe_proxy = sum(row["avg_signal"] for row in rows) / max(len(rows), 1)
    return {"strategies": pd.DataFrame(rows), "signals": signals, "blended_sharpe_proxy": blended_sharpe_proxy}


def render_cli(
    holdings: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    account_totals: dict[str, float | None] | None = None,
) -> None:
    as_of = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"\nBeacon output as of {as_of}")
    print("Educational research output only; verify independently before trading.\n")

    if holdings:
        summary = portfolio_summary(holdings, account_totals)
        print(f"Robinhood market value: ${summary['total_value']:,.2f} across {summary['positions']} positions")
        if summary["account_equity"] is not None:
            print(
                f"Robinhood account equity: ${summary['account_equity']:,.2f}; "
                f"today {summary['today_change']:+,.2f} ({pct(summary['today_change_pct'])})"
            )
        if summary["concentrated"]:
            print(
                "Concentration watch: "
                + ", ".join(
                    f"{row['ticker']} {pct(row['portfolio_weight'])}" for row in summary["concentrated"][:5]
                )
            )
        if summary["weak"]:
            print(
                "Weak/neutral watch: "
                + ", ".join(f"{row['ticker']} signal {row['signal']}" for row in summary["weak"][:5])
            )
        print()
        actions = today_actions(holdings)
        if actions:
            print("What should I review today")
            for row in actions:
                print(f"- {row['ticker']}: {row['action']} ({pct(row['portfolio_weight'])} weight, gain {pct(row['unrealized_gain'])})")
            print()
        print("Current holdings")
        for row in holdings:
            if row.get("error"):
                print(f"- {row['ticker']}: DATA UNAVAILABLE ({row['error']})")
                continue
            print(
                f"- {row['ticker']}: signal {row['signal']}, {row['action']}, "
                f"weight {pct(row['portfolio_weight'])}, value ${row['market_value']:,.2f}, "
                f"price ${row['price']:.2f}, gain {pct(row['unrealized_gain'])}, "
                f"3m {pct(row.get('return_3m'))}, dd {pct(row.get('drawdown'))}"
            )
        print()

    print("Buy candidates ranked from live data")
    for idea in ideas:
        if "error" in idea:
            print(f"- {idea['ticker']}: skipped ({idea['error']})")
            continue
        print(f"- {idea['ticker']} ({idea['name']}): score {idea['score']:.2f}, price ${idea['price']:.2f}")
        print(f"  Reasons: {'; '.join(idea['reasons'])}")
        if idea["news"]:
            print(f"  Latest headline: {idea['news'][0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live portfolio decision and buy-idea ranker.")
    parser.add_argument("--credentials", default="credentials.md")
    parser.add_argument("--use-robinhood", action="store_true")
    parser.add_argument("--test-robinhood-login", action="store_true")
    parser.add_argument("--no-robinhood-session", action="store_true")
    parser.add_argument("--extra-tickers", default="")
    parser.add_argument("--include-owned-ideas", action="store_true")
    parser.add_argument("--use-openai", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    credentials = load_credentials(args.credentials)
    if args.test_robinhood_login:
        holdings = get_robinhood_portfolio(credentials, store_session=not args.no_robinhood_session)
        print(f"Robinhood login OK. Retrieved {len(holdings)} stock holdings.")
        return

    if args.use_robinhood:
        holdings = get_robinhood_portfolio(credentials, store_session=not args.no_robinhood_session)
        account_totals = get_robinhood_account_totals(credentials, store_session=not args.no_robinhood_session)
    else:
        holdings = get_manual_portfolio(credentials)
        account_totals = None

    extra_tickers = [ticker.strip().upper() for ticker in args.extra_tickers.split(",") if ticker.strip()]
    dynamic_universe = build_dynamic_universe(holdings, credentials, extra_tickers=extra_tickers, limit=max(args.limit, 8))
    watchlist = dynamic_universe["tickers"]
    holdings_report = analyze_holdings(holdings, credentials, use_llm=args.use_openai) if holdings else []
    owned = {holding.ticker.upper() for holding in holdings}
    exclude = set() if args.include_owned_ideas else owned
    ideas = rank_buy_ideas(watchlist, credentials, args.limit, exclude=exclude)
    render_cli(holdings_report, ideas, account_totals)


if __name__ == "__main__":
    main()
