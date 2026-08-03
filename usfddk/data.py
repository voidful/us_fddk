from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from usfddk.models import ContractResult, MarketPanel

SNAPSHOT_SCHEMA_VERSION = 1
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _clean_frame(frame: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(frame, pd.Series):
        frame = frame.to_frame(name=tickers[0])
    frame = frame.copy()
    frame.columns = [str(x).upper() for x in frame.columns]
    frame = frame.reindex(columns=tickers)
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_convert("America/New_York").tz_localize(None)
    frame.index = index.normalize()
    return frame[~frame.index.duplicated(keep="last")].sort_index().astype(float)


def _extract(raw: pd.DataFrame, field: str, tickers: list[str]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        if field in raw.columns.get_level_values(0):
            result = raw[field]
        elif field in raw.columns.get_level_values(1):
            result = raw.xs(field, axis=1, level=1)
        else:
            result = pd.DataFrame(index=raw.index, columns=tickers, dtype=float)
    else:
        if len(tickers) != 1:
            raise ValueError("行情供應商回傳單層欄位，但請求包含多個代號")
        if field not in raw.columns:
            result = pd.DataFrame(index=raw.index, columns=tickers, dtype=float)
        else:
            result = raw[[field]].rename(columns={field: tickers[0]})
    return _clean_frame(result, tickers)


def fetch_yfinance(
    tickers: Iterable[str],
    start: str | date,
    end: str | date | None = None,
    *,
    threads: bool = True,
) -> MarketPanel:
    """Fetch raw Yahoo bars, then adjust all OHLC fields by Adj Close / Close.

    The adjustment method is recorded explicitly because silently mixing raw Open/High/Low
    with adjusted Close creates false stops, gaps, and returns around corporate actions.
    """
    import yfinance as yf

    symbols = list(dict.fromkeys(str(x).upper().strip() for x in tickers if str(x).strip()))
    if not symbols:
        raise ValueError("至少需要一個代號")
    end_exclusive = None
    if end is not None:
        end_exclusive = (pd.Timestamp(end).normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    raw = yf.download(
        symbols,
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        end=end_exclusive,
        auto_adjust=False,
        actions=True,
        repair=False,
        progress=False,
        threads=threads,
        group_by="column",
        timeout=30,
    )
    if raw is None or raw.empty:
        raise RuntimeError("Yahoo Finance 未回傳資料")

    raw_close = _extract(raw, "Close", symbols)
    adjusted_close = _extract(raw, "Adj Close", symbols)
    if adjusted_close.notna().sum().sum() == 0:
        raise RuntimeError("Yahoo Finance 未回傳 Adj Close，拒絕以未還原資料冒充總報酬")
    factor = adjusted_close.div(raw_close.replace(0.0, np.nan))

    adjusted: dict[str, pd.DataFrame] = {}
    for field in ("Open", "High", "Low", "Close"):
        base = raw_close if field == "Close" else _extract(raw, field, symbols)
        adjusted[field] = base.mul(factor)
    adjusted["Volume"] = _extract(raw, "Volume", symbols)

    # Yahoo occasionally emits rows for an auxiliary index on a US equity holiday.
    # A union calendar would then create a fake tradable day with SPY/ETF prices missing.
    # Anchor the panel to SPY when present; otherwise require at least half the requested
    # symbols to have a close on a date.
    if "SPY" in adjusted["Close"].columns:
        common_index = adjusted["Close"].index[adjusted["Close"]["SPY"].notna()]
    else:
        row_coverage = adjusted["Close"].notna().mean(axis=1)
        common_index = adjusted["Close"].index[row_coverage >= 0.50]
    for field in adjusted:
        adjusted[field] = adjusted[field].reindex(common_index)

    return MarketPanel(
        open=adjusted["Open"],
        high=adjusted["High"],
        low=adjusted["Low"],
        close=adjusted["Close"],
        volume=adjusted["Volume"],
        metadata={
            "provider": "Yahoo Finance via yfinance",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "adjustment": "adjusted_ohlc = raw_ohlc * (adj_close / raw_close)",
            "auto_adjust": False,
        },
    )


def most_recent_us_session(as_of: str | date | pd.Timestamp) -> pd.Timestamp:
    stamp = pd.Timestamp(as_of)
    try:
        import exchange_calendars as xcals

        calendar = xcals.get_calendar("XNYS")
        if stamp.tzinfo is not None:
            instant = stamp.tz_convert("UTC")
            market_day = instant.tz_convert("America/New_York").normalize().tz_localize(None)
            for offset in range(15):
                candidate = market_day - pd.Timedelta(days=offset)
                if calendar.is_session(candidate) and calendar.session_close(candidate) <= instant:
                    return candidate
            raise ValueError("找不到最近已完成的 XNYS session")
        stamp = stamp.normalize()
        for offset in range(15):
            candidate = stamp - pd.Timedelta(days=offset)
            if calendar.is_session(candidate):
                return candidate
    except Exception:
        if stamp.tzinfo is not None:
            local = stamp.tz_convert("America/New_York")
            candidate = local.normalize().tz_localize(None)
            if local.hour < 16:
                candidate -= pd.Timedelta(days=1)
            stamp = candidate
        else:
            stamp = stamp.normalize()
    for offset in range(10):
        candidate = stamp - pd.Timedelta(days=offset)
        if candidate.weekday() < 5:
            return candidate
    return stamp


def market_data_freshness_schedule(
    last_session: str | date | pd.Timestamp,
    *,
    vendor_grace_hours: float = 6.0,
) -> dict[str, str | float]:
    """Return the next XNYS session and the deadline after which a snapshot is stale.

    The grace period begins at the official session close, so exchange holidays and
    early closes are handled by the calendar rather than weekday guesses.
    """
    if vendor_grace_hours < 0:
        raise ValueError("行情供應商緩衝時間不能小於零")
    stamp = pd.Timestamp(last_session).normalize()
    try:
        import exchange_calendars as xcals

        calendar = xcals.get_calendar("XNYS")
        if not calendar.is_session(stamp):
            raise ValueError(f"{stamp.date()} 不是 XNYS 交易日")
        next_session = pd.Timestamp(calendar.next_session(stamp)).normalize()
        next_close = pd.Timestamp(calendar.session_close(next_session)).tz_convert("UTC")
    except ImportError:
        next_session = stamp + pd.Timedelta(days=1)
        while next_session.weekday() >= 5:
            next_session += pd.Timedelta(days=1)
        next_close = next_session.tz_localize("UTC") + pd.Timedelta(hours=21)
    deadline = next_close + pd.Timedelta(hours=vendor_grace_hours)
    return {
        "last_session": stamp.strftime("%Y-%m-%d"),
        "next_expected_session": next_session.strftime("%Y-%m-%d"),
        "next_session_close_utc": next_close.isoformat().replace("+00:00", "Z"),
        "refresh_due_at_utc": deadline.isoformat().replace("+00:00", "Z"),
        "vendor_grace_hours": float(vendor_grace_hours),
    }


def validate_panel(
    panel: MarketPanel,
    *,
    as_of: str | date | pd.Timestamp | None = None,
    required: Iterable[str] = ("SPY",),
    min_last_coverage: float = 0.90,
    min_history_coverage: float = 0.80,
    max_adjusted_move: float = 0.65,
    require_fresh: bool = True,
) -> ContractResult:
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, object] = {}
    close = panel.close.sort_index()
    if close.empty:
        return ContractResult(False, ("Close 面板為空",), (), {})

    if not close.index.is_monotonic_increasing or close.index.has_duplicates:
        errors.append("日期索引不是嚴格遞增且唯一")
    if close.columns.duplicated().any():
        errors.append("代號欄位重複")

    fields = panel.field_map()
    for field, frame in fields.items():
        if not frame.index.equals(close.index) or list(frame.columns) != list(close.columns):
            errors.append(f"{field} 與 Close 的索引/欄位不一致")

    last_date = pd.Timestamp(close.index[-1]).normalize()
    stats["last_session"] = last_date.strftime("%Y-%m-%d")
    if as_of is not None:
        expected = most_recent_us_session(as_of)
        stats["expected_session"] = expected.strftime("%Y-%m-%d")
        if require_fresh and last_date != expected:
            errors.append(f"最後 bar {last_date.date()} != 預期美股 session {expected.date()}")

    last_coverage = float(close.iloc[-1].notna().mean())
    stats["last_close_coverage"] = last_coverage
    if last_coverage < min_last_coverage:
        errors.append(f"最後 Close 完整率 {last_coverage:.1%} < {min_last_coverage:.0%}")

    history_coverage = close.notna().mean()
    thin = history_coverage[history_coverage < min_history_coverage]
    stats["thin_tickers"] = {str(k): round(float(v), 4) for k, v in thin.items()}
    if len(thin):
        warnings.append("歷史覆蓋不足：" + ", ".join(f"{k}={v:.0%}" for k, v in thin.items()))
    dead = history_coverage[history_coverage == 0]
    if len(dead):
        errors.append("整段無有效價格：" + ", ".join(map(str, dead.index)))

    for ticker in required:
        if ticker not in close.columns or not np.isfinite(close[ticker].iloc[-1]):
            errors.append(f"必要標的 {ticker} 缺少最新價格")

    finite_positive = close.where(close > 0).notna()
    stats["positive_price_fraction"] = float(finite_positive.mean().mean())
    observed_prices = close.stack().dropna()
    if len(observed_prices) and not bool((observed_prices > 0).all()):
        errors.append("Close 含零或負值")

    returns = close.pct_change(fill_method=None).abs()
    suspicious = returns.iloc[-1][returns.iloc[-1] > max_adjusted_move].dropna()
    stats["suspicious_last_moves"] = {str(k): round(float(v), 4) for k, v in suspicious.items()}
    if len(suspicious):
        errors.append("最新 bar 疑似未處理公司行動：" + ", ".join(suspicious.index))

    o, h, low = panel.open, panel.high, panel.low
    bad_ohlc = ((h < o) | (h < close) | (low > o) | (low > close)).stack().fillna(False)
    bad_count = int(bad_ohlc.sum())
    stats["ohlc_violations"] = bad_count
    if bad_count:
        errors.append(f"OHLC 關係違反 {bad_count} 格")

    latest_volume_ok = float((panel.volume.iloc[-1] > 0).mean())
    stats["latest_positive_volume"] = latest_volume_ok
    if latest_volume_ok < min_last_coverage:
        errors.append(f"最新有量比例 {latest_volume_ok:.1%} < {min_last_coverage:.0%}")

    return ContractResult(not errors, tuple(errors), tuple(warnings), stats)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    cleaned = frame.sort_index().reindex(sorted(frame.columns), axis=1)
    cleaned.index.name = "Date"
    return cleaned.to_csv(date_format="%Y-%m-%d", float_format="%.10g").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def panel_fingerprint(panel: MarketPanel) -> str:
    """Stable content identity independent of retrieval time and ZIP metadata."""
    file_hashes = {
        f"{name.lower()}.csv": _sha256(_csv_bytes(frame))
        for name, frame in panel.field_map().items()
    }
    payload = json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    return _sha256(payload)


def save_snapshot(
    panel: MarketPanel,
    destination: str | Path,
    *,
    contract: ContractResult | None = None,
) -> dict:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    members = {
        f"{name.lower()}.csv": _csv_bytes(frame) for name, frame in panel.field_map().items()
    }
    manifest = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "tickers": sorted(panel.tickers),
        "rows": int(len(panel.close)),
        "provider_metadata": panel.metadata,
        "files": {name: _sha256(payload) for name, payload in members.items()},
        "panel_sha256": panel_fingerprint(panel),
        "contract": None
        if contract is None
        else {
            "ok": contract.ok,
            "errors": list(contract.errors),
            "warnings": list(contract.warnings),
            "stats": contract.stats,
        },
    }
    manifest_payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode(
        "utf-8"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted({**members, "manifest.json": manifest_payload}.items()):
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
    manifest["archive_sha256"] = _sha256(path.read_bytes())
    return manifest


def load_snapshot(source: str | Path) -> tuple[MarketPanel, dict]:
    path = Path(source)
    with zipfile.ZipFile(path, "r") as archive:
        names = set(archive.namelist())
        expected = {"open.csv", "high.csv", "low.csv", "close.csv", "volume.csv", "manifest.json"}
        if names != expected:
            raise ValueError(f"快照成員不符：{sorted(names)}")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
            raise ValueError("不支援的快照 schema")
        frames: dict[str, pd.DataFrame] = {}
        for field in ("open", "high", "low", "close", "volume"):
            name = f"{field}.csv"
            payload = archive.read(name)
            if _sha256(payload) != manifest["files"][name]:
                raise ValueError(f"快照雜湊不符：{name}")
            frame = pd.read_csv(io.BytesIO(payload), index_col="Date", parse_dates=["Date"])
            frame.columns = [str(x) for x in frame.columns]
            frames[field] = frame.astype(float)
    panel = MarketPanel(
        open=frames["open"],
        high=frames["high"],
        low=frames["low"],
        close=frames["close"],
        volume=frames["volume"],
        metadata={**manifest.get("provider_metadata", {}), "snapshot": str(path.resolve())},
    )
    return panel, manifest


def default_snapshot_path(
    output_dir: str | Path, session: pd.Timestamp, panel_sha256: str | None = None
) -> Path:
    suffix = f"_{panel_sha256[:8]}" if panel_sha256 else ""
    return Path(output_dir) / f"snapshot_{session.strftime('%Y%m%d')}{suffix}.zip"


def stale_after_days(last_date: pd.Timestamp, as_of: pd.Timestamp) -> int:
    return max(0, (as_of.normalize() - last_date.normalize()).days)
