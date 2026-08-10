from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .form4_full_coverage import (
    MANIFEST_PATH as FULL_COVERAGE_MANIFEST_PATH,
)
from .form4_full_coverage import (
    VALIDATION_PATH as FULL_COVERAGE_VALIDATION_PATH,
)
from .form4_full_coverage import (
    WATCHLIST_COUNT,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
    _load_manifest,
    _load_sec_mapping,
    _normalize_symbol,
    _parse_purchase_aggregates,
    _sha256_file,
    _validate_sources,
)
from .form4_historical_feasibility import _load_protocol_binding
from .metrics import newey_west_mean_test
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_form4_event_diagnostic.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_EVENT_DIAGNOSTIC_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_event_diagnostic_protocol_receipt.json"
)
VALIDATION_PATH = Path("artifacts/short_term_form4_event_diagnostic_validation.json")
EXPECTED_PROTOCOL_SHA256 = (
    "692d0d32036ae2f5a42fdae54bf3f825df0c761cdadb29bc6133bebaeb235b74"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "576e93d969c0d53b3b7067f1afbf7e9ef3794c60a8585be3f5e566ef70750c6d"
)
FULL_COVERAGE_SOURCE_MANIFEST_SHA256 = (
    "b7e1b42923cee0ef2079494f2004c56f41976899e98d1f4352b990517bb9af85"
)
FULL_COVERAGE_VALIDATION_SHA256 = (
    "36768ac8cd6f5b4435d9b2a90c9c2c6761bb4c3498e6eb58a6dead54977e23f0"
)
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = (
    "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
)
SNAPSHOT_PANEL_SHA256 = (
    "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
)
SEC_MAPPING_BYTES = 795627
SEC_MAPPING_SHA256 = (
    "6dd9c4363c5a95d43f4d8e8f8279f9ae6538d10d295bbdeebe5a433ec954bf6d"
)
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6290
GLOBAL_TRIAL_INCREMENT = 3
HORIZONS = (5, 10, 20)
PRIMARY_HORIZON = 10
ROUND_TRIP_COST = 20 / 10_000
BOOTSTRAP_SAMPLES = 2_000
BOOTSTRAP_BLOCK = 8
BOOTSTRAP_SEED = 20_260_810
CLUSTER_MIN_ACCESSIONS = 2
CLUSTER_MIN_NOTIONAL = 100_000.0
_FORBIDDEN_KEYS = {
    "accession",
    "accession_number",
    "cik",
    "filing_date",
    "issuer",
    "issuer_cik",
    "notional",
    "owner",
    "owner_cik",
    "owner_name",
    "symbol",
    "ticker",
}


class Form4EventDiagnosticError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4EventDiagnosticError(code, detail)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_protocol(root: Path) -> dict[str, Any]:
    protocol_path = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if _sha256_file(protocol_path) != EXPECTED_PROTOCOL_SHA256:
        _fail("form4_event_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("form4_event_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("form4_event_protocol_drift", "receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("form4_event_protocol_drift", "receipt hash drifted")
    expected = {
        "schema_version": 1,
        "research_round": 53,
        "status": "preregistered_form4_event_diagnostic_only",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "quarter_source_manifest": {
            "path": str(FULL_COVERAGE_MANIFEST_PATH),
            "sha256": FULL_COVERAGE_SOURCE_MANIFEST_SHA256,
        },
        "source_validation_sha256": FULL_COVERAGE_VALIDATION_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "paper_authorized": False,
        "performance_authorized": False,
        "real_money_authorized": False,
        "today_action": "今天不下單",
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        _fail("form4_event_protocol_drift", "fixed receipt field drifted")
    if receipt.get("event_contract", {}).get("exit_horizons_sessions") != list(HORIZONS):
        _fail("form4_event_protocol_drift", "horizon set drifted")
    return receipt


def _privacy_scan(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _FORBIDDEN_KEYS:
                _fail("form4_event_privacy_boundary", f"forbidden key at {path}")
            _privacy_scan(item, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            _privacy_scan(item, path=f"{path}[{index}]")


def _moving_block_bootstrap(
    series: pd.Series,
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    block_size: int = BOOTSTRAP_BLOCK,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    values = series.dropna().to_numpy(dtype=float)
    if len(values) < block_size * 2:
        return {"low": float("nan"), "median": float("nan"), "high": float("nan"), "p_below_or_equal_zero": float("nan")}
    rng = np.random.default_rng(seed)
    starts = len(values) - block_size + 1
    blocks = int(math.ceil(len(values) / block_size))
    means = np.empty(samples, dtype=float)
    for sample in range(samples):
        picks = rng.integers(0, starts, size=blocks)
        resampled = np.concatenate(
            [values[start : start + block_size] for start in picks]
        )[: len(values)]
        means[sample] = float(resampled.mean())
    low, median, high = np.quantile(means, [0.025, 0.5, 0.975])
    return {
        "low": float(low),
        "median": float(median),
        "high": float(high),
        "p_below_or_equal_zero": float((means <= 0.0).mean()),
    }


def _first_session_after(index: pd.DatetimeIndex, day: pd.Timestamp) -> int | None:
    position = int(index.searchsorted(day.normalize(), side="right"))
    return position if position < len(index) else None


def _event_mapping(
    purchase: Mapping[str, Any],
    *,
    watchlist_symbols: set[str],
    cik_to_symbols: Mapping[str, frozenset[str]],
) -> tuple[str, str] | tuple[None, str]:
    filed = purchase.get("issuer_symbol")
    if isinstance(filed, str) and filed in watchlist_symbols:
        return filed, "as_filed_symbol_exact"
    current = cik_to_symbols.get(str(purchase.get("issuer_cik")), frozenset()) & watchlist_symbols
    if len(current) == 1:
        return next(iter(current)), "current_cik_exact"
    if len(current) > 1:
        return None, "ambiguous_current_cik"
    return None, "unmapped"


def _collect_cluster_events(
    *,
    repository_root: Path,
    staging_dir: Path,
    manifest_path: Path,
    mapping_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, int], str]:
    manifest = _load_manifest(repository_root, manifest_path.resolve())
    _validate_sources(staging_dir=staging_dir.resolve(), manifest=manifest)
    mapping = _load_sec_mapping(mapping_path.resolve())
    records = load_stock_watchlist()
    symbols = {_normalize_symbol(record.symbol) for record in records}
    if len(records) != WATCHLIST_COUNT or None in symbols:
        _fail("form4_event_universe_invalid", "watchlist is not fixed")
    watchlist_symbols = {str(symbol) for symbol in symbols}
    binding = _load_protocol_binding(repository_root)
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    coverage = Counter()
    for row in manifest["quarters"]:
        quarter = str(row["quarter"])
        parsed = _parse_purchase_aggregates(
            (staging_dir / str(row["filename"])).read_bytes(),
            quarter=quarter,
            amendment_receipt=binding["amendment_receipt"],
        )
        for purchase in parsed["purchases"]:
            symbol, mapping_mode = _event_mapping(
                purchase,
                watchlist_symbols=watchlist_symbols,
                cik_to_symbols=mapping,
            )
            coverage[mapping_mode] += 1
            if symbol is None:
                continue
            date_text = str(purchase.get("filing_date", ""))
            key = (str(purchase["issuer_cik"]), date_text)
            event = grouped.setdefault(
                key,
                {"accession_count": 0, "notional": 0.0, "symbols": set(), "filing_date": date_text},
            )
            event["accession_count"] += 1
            event["notional"] += float(purchase["notional"])
            event["symbols"].add(symbol)
    events: list[dict[str, Any]] = []
    for event in grouped.values():
        if (
            event["accession_count"] >= CLUSTER_MIN_ACCESSIONS
            and event["notional"] >= CLUSTER_MIN_NOTIONAL
            and len(event["symbols"]) == 1
        ):
            events.append(
                {
                    "filing_date": pd.Timestamp(event["filing_date"]),
                    "symbol": next(iter(event["symbols"])),
                    "accession_count": int(event["accession_count"]),
                }
            )
    events.sort(key=lambda item: (item["filing_date"], item["symbol"]))
    coverage["cluster_events"] = len(events)
    return events, dict(sorted(coverage.items())), manifest["manifest_sha256"]


def _return_row(
    panel: Any,
    *,
    event: Mapping[str, Any],
    complete_symbols: list[str],
    horizon: int,
) -> dict[str, float] | None:
    index = pd.DatetimeIndex(panel.close.index).normalize()
    entry_position = _first_session_after(index, pd.Timestamp(event["filing_date"]))
    if entry_position is None or entry_position + horizon >= len(index):
        return None
    entry_date = index[entry_position]
    exit_date = index[entry_position + horizon]
    symbol = str(event["symbol"])
    if symbol not in panel.open.columns:
        return None
    event_open = panel.open.loc[entry_date, symbol]
    event_close = panel.close.loc[exit_date, symbol]
    if not np.isfinite(event_open) or not np.isfinite(event_close) or event_open <= 0:
        return None
    event_return = float(event_close / event_open - 1.0 - ROUND_TRIP_COST)
    pool_symbols = [
        item
        for item in complete_symbols
        if item in panel.open.columns
        and np.isfinite(panel.open.loc[entry_date, item])
        and np.isfinite(panel.close.loc[exit_date, item])
        and panel.open.loc[entry_date, item] > 0
    ]
    if len(pool_symbols) < 5:
        return None
    pool_return = float(
        (panel.close.loc[exit_date, pool_symbols] / panel.open.loc[entry_date, pool_symbols] - 1.0).mean()
        - ROUND_TRIP_COST
    )
    complete = [item for item in complete_symbols if item in pool_symbols]
    complete_return = pool_return if len(complete) == len(pool_symbols) else float(
        (panel.close.loc[exit_date, complete] / panel.open.loc[entry_date, complete] - 1.0).mean()
        - ROUND_TRIP_COST
    )
    benchmark: dict[str, float] = {}
    for name in ("SPY", "QQQ"):
        if name not in panel.open.columns:
            benchmark[name] = float("nan")
            continue
        open_value = panel.open.loc[entry_date, name]
        close_value = panel.close.loc[exit_date, name]
        benchmark[name] = float(close_value / open_value - 1.0 - ROUND_TRIP_COST) if open_value > 0 else float("nan")
    return {
        "event_return": event_return,
        "eligible_pool_return": pool_return,
        "complete_cohort_return": complete_return,
        "SPY_return": benchmark["SPY"],
        "QQQ_return": benchmark["QQQ"],
        "year": int(pd.Timestamp(event["filing_date"]).year),
    }


def _summarize_horizon(rows: list[dict[str, float]], horizon: int) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    selected = frame["event_return"]
    pool = frame["eligible_pool_return"]
    complete = frame["complete_cohort_return"]
    difference = selected - pool
    lag = int(math.ceil(horizon / 5))
    halves = {}
    for label, mask in (
        ("first", frame["year"] <= 2016),
        ("second", frame["year"] >= 2017),
    ):
        sample = difference.loc[mask]
        halves[label] = {
            "events": int(len(sample)),
            "mean_difference": float(sample.mean()) if len(sample) else float("nan"),
        }
    return {
        "holding_sessions": horizon,
        "events": int(len(frame)),
        "event_mean": float(selected.mean()),
        "eligible_pool_mean": float(pool.mean()),
        "complete_cohort_mean": float(complete.mean()),
        "SPY_mean": float(frame["SPY_return"].mean()),
        "QQQ_mean": float(frame["QQQ_return"].mean()),
        "mean_difference_vs_eligible_pool": float(difference.mean()),
        "mean_difference_vs_complete_cohort": float((selected - complete).mean()),
        "median_difference_vs_eligible_pool": float(difference.median()),
        "win_fraction_vs_eligible_pool": float((difference > 0.0).mean()),
        "newey_west_vs_eligible_pool": newey_west_mean_test(
            difference, max_lag=lag, periods_per_year=252 / horizon
        ),
        "moving_block_bootstrap_vs_eligible_pool": _moving_block_bootstrap(difference),
        "fixed_halves_vs_eligible_pool": halves,
    }


def audit_form4_event_diagnostic(
    *,
    repository_root: Path,
    snapshot_path: Path,
    staging_dir: Path,
    manifest_path: Path,
    sec_mapping_path: Path,
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("form4_event_snapshot_invalid", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("form4_event_snapshot_invalid", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256 or panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256:
        _fail("form4_event_snapshot_invalid", "snapshot panel hash drifted")
    if _sha256_file(root / WATCHLIST_PATH) != WATCHLIST_SHA256:
        _fail("form4_event_source_invalid", "watchlist hash drifted")
    mapping_path = sec_mapping_path.resolve()
    try:
        mapping_path.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("form4_event_mapping_boundary", "SEC mapping must remain outside repository")
    if _sha256_file(mapping_path) != SEC_MAPPING_SHA256 or mapping_path.stat().st_size != SEC_MAPPING_BYTES:
        _fail("form4_event_source_invalid", "SEC mapping hash drifted")
    validation_path = root / FULL_COVERAGE_VALIDATION_PATH
    if _sha256_file(validation_path) != FULL_COVERAGE_VALIDATION_SHA256:
        _fail("form4_event_source_invalid", "Round52 validation hash drifted")
    events, coverage, manifest_sha = _collect_cluster_events(
        repository_root=root,
        staging_dir=staging_dir,
        manifest_path=manifest_path,
        mapping_path=mapping_path,
    )
    if manifest_sha != FULL_COVERAGE_SOURCE_MANIFEST_SHA256:
        _fail("form4_event_source_invalid", "Round52 manifest hash drifted")
    records = load_stock_watchlist()
    complete_symbols = [
        record.symbol
        for record in records
        if record.symbol in panel.close.columns and panel.close[record.symbol].notna().all()
    ]
    horizon_results: dict[str, Any] = {}
    complete_counts: dict[str, int] = {}
    for horizon in HORIZONS:
        rows: list[dict[str, float]] = []
        for event in events:
            row = _return_row(
                panel,
                event=event,
                complete_symbols=complete_symbols,
                horizon=horizon,
            )
            if row is not None:
                rows.append(row)
        horizon_results[str(horizon)] = _summarize_horizon(rows, horizon) if rows else {
            "holding_sessions": horizon,
            "events": 0,
            "mean_difference_vs_eligible_pool": float("nan"),
            "newey_west_vs_eligible_pool": {"t_stat": 0.0},
            "moving_block_bootstrap_vs_eligible_pool": {"low": float("nan")},
            "win_fraction_vs_eligible_pool": float("nan"),
            "fixed_halves_vs_eligible_pool": {"first": {"events": 0}, "second": {"events": 0}},
        }
        complete_counts[str(horizon)] = int(len(rows))
    primary = horizon_results[str(PRIMARY_HORIZON)]
    primary_halves = primary["fixed_halves_vs_eligible_pool"]
    gates = {
        "at_least_30_complete_events": primary["events"] >= 30,
        "mean_difference_positive": primary["mean_difference_vs_eligible_pool"] > 0.0,
        "newey_west_t_at_least_1_96": primary["newey_west_vs_eligible_pool"].get("t_stat", 0.0) >= 1.96,
        "bootstrap_low_positive": primary["moving_block_bootstrap_vs_eligible_pool"].get("low", float("nan")) > 0.0,
        "win_fraction_over_50_percent": primary["win_fraction_vs_eligible_pool"] > 0.50,
        "both_fixed_halves_positive": (
            primary_halves["first"].get("mean_difference", float("nan")) > 0.0
            and primary_halves["second"].get("mean_difference", float("nan")) > 0.0
        ),
    }
    gates_passed = int(sum(bool(value) for value in gates.values()))
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 53,
        "status": (
            "form4_event_diagnostic_positive_survivorship_biased"
            if all(gates.values())
            else "form4_event_diagnostic_negative_survivorship_biased"
        ),
        "source": {
            "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
            "round52_manifest_sha256": manifest_sha,
            "round52_validation_sha256": FULL_COVERAGE_VALIDATION_SHA256,
            "snapshot_filename": SNAPSHOT_FILENAME,
            "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
            "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
            "mapping_sha256": SEC_MAPPING_SHA256,
            "mapping_bytes": SEC_MAPPING_BYTES,
            "watchlist_count": WATCHLIST_COUNT,
            "watchlist_sha256": WATCHLIST_SHA256,
        },
        "event_definition": {
            "cluster_min_accessions": CLUSTER_MIN_ACCESSIONS,
            "cluster_min_notional_usd": CLUSTER_MIN_NOTIONAL,
            "mapped_purchase_accession_count": int(sum(coverage.get(key, 0) for key in ("as_filed_symbol_exact", "current_cik_exact"))),
            "cluster_event_count": int(len(events)),
            "coverage_counts": coverage,
        },
        "horizons": horizon_results,
        "complete_event_counts": complete_counts,
        "gate_summary": {
            "primary_horizon_sessions": PRIMARY_HORIZON,
            "gates": gates,
            "passed": gates_passed,
            "required": len(gates),
        },
        "multiplicity": {
            "prior_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
            "increment": GLOBAL_TRIAL_INCREMENT,
            "current_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND + GLOBAL_TRIAL_INCREMENT,
        },
        "state_boundary": {
            "performance_present": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "real_money_authorized": False,
            "real_money_action_usd": 0,
            "today_action": "今天不下單",
        },
        "limitations": [
            "current_watchlist_is_survivorship_biased",
            "current_cik_mapping_is_not_historical_security_master",
            "filing_date_is_not_intraday_public_timestamp",
            "adjusted_ohlcv_is_not_raw_execution_or_complete_total_return_ledger",
            "event_study_is_not_a_portfolio_backtest",
            "no_strategy_or_paper_authorization",
        ],
    }
    _privacy_scan(result)
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(result: Mapping[str, Any], *, repository_root: Path) -> Path:
    path = repository_root / VALIDATION_PATH
    path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path
