from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from usfddk.sec_insider_forward import (
    compute_forward_event_diagnostic,
    load_long_total_return_prices,
)


def _prices() -> pd.DataFrame:
    days = [date(2026, 6, 2) + timedelta(days=offset) for offset in range(8)]
    sessions = [day for day in days if day.weekday() < 5]
    rows = []
    for symbol, base in (("EXMP", 100.0), ("QQQ", 200.0)):
        for index, day in enumerate(sessions):
            rows.append(
                {
                    "symbol": symbol,
                    "date": day,
                    "adj_open": base + index,
                    "adj_close": base + index + (4.0 if symbol == "EXMP" else 2.0),
                }
            )
    return pd.DataFrame(rows)


def test_forward_diagnostic_uses_same_clock_and_fixed_cost() -> None:
    candidates = [
        {"ticker": "EXMP", "available_session": "2026-06-02"},
    ]
    result = compute_forward_event_diagnostic(
        candidates,
        _prices(),
        as_of=date(2026, 6, 2),
    )

    primary = result["horizons"]["20"]
    assert primary["complete_rows"] == 0
    short = result["horizons"]["5"]
    assert short["complete_rows"] == 1
    assert short["missing_candidate_rows"] == 0
    assert short["missing_baseline_rows"] == 0
    assert short["mean_excess_vs_baseline"] > 0.0


def test_price_loader_rejects_duplicate_rows(tmp_path) -> None:
    path = tmp_path / "prices.csv"
    _prices().to_csv(path, index=False)
    frame = pd.read_csv(path)
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="重複"):
        load_long_total_return_prices(path)


def test_price_loader_rejects_missing_required_column(tmp_path) -> None:
    path = tmp_path / "prices.csv"
    _prices().drop(columns=["adj_close"]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="欄位不完整"):
        load_long_total_return_prices(path)


def test_saved_forward_receipt_remains_research_only() -> None:
    receipt = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "artifacts/short_term_sec_insider_forward_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["status"] == "post_hoc_forward_event_diagnostic"
    assert receipt["decision"]["paper_authorized"] is False
    assert receipt["decision"]["public_strategy_allowed"] is False
    assert len(receipt["protocol"]["sha256"]) == 64
    assert receipt["diagnostic"]["horizons"]["20"]["complete_rows"] == 569
    assert receipt["diagnostic"]["horizons"]["20"]["mean_excess_vs_baseline"] > 0.0
