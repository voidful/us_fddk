from __future__ import annotations

import pandas as pd
import pytest

from usfddk.formal_signal_engine import (
    FORMAL_SIGNAL_COLUMNS,
    SignalInputs,
    build_baseline_target_weights,
    build_monthly_target_weights,
)


def _inputs(*, future_membership_announcement: bool = False) -> SignalInputs:
    dates = pd.bdate_range("2018-01-01", periods=430)
    ids = ["SEC-A", "SEC-B", "SEC-C"]
    master = pd.DataFrame(
        [
            {"security_id": "SEC-A", "company_id": "CO-A", "security_type": "common_stock", "share_class": "A", "currency": "USD"},
            {"security_id": "SEC-B", "company_id": "CO-B", "security_type": "common_stock", "share_class": "A", "currency": "USD"},
            {"security_id": "SEC-C", "company_id": "CO-A", "security_type": "common_stock", "share_class": "B", "currency": "USD"},
        ]
    )
    membership = pd.DataFrame(
        [
            {
                "index_id": "SP500",
                "security_id": security_id,
                "effective_from": str(dates[0].date()),
                "effective_to": "",
                "announced_at": (
                    "2025-01-01T12:00:00Z"
                    if future_membership_announcement
                    else "2017-12-01T12:00:00Z"
                ),
                "source_record_id": f"membership-{security_id}",
            }
            for security_id in ids
        ]
    )
    classifications = pd.DataFrame(
        [
            {
                "security_id": security_id,
                "scheme": "GICS",
                "sector_code": "TECH" if security_id != "SEC-B" else "FIN",
                "effective_from": str(dates[0].date()),
                "effective_to": "",
                "known_at": "2017-12-01T12:00:00Z",
                "source_record_id": f"classification-{security_id}",
            }
            for security_id in ids
        ]
    )
    price_rows: list[dict[str, object]] = []
    for position, day in enumerate(dates):
        # SEC-A is the strongest signal; SEC-C is a same-company share class
        # with a smaller dollar-volume tie-break and must be removed before rank.
        values = {
            "SEC-A": 20.0 + position * 0.40,
            "SEC-B": 20.0 + position * 0.05,
            "SEC-C": 20.0 + position * 0.20,
        }
        volumes = {"SEC-A": 2_000_000, "SEC-B": 2_000_000, "SEC-C": 100_000}
        for security_id in ids:
            close = values[security_id]
            price_rows.append(
                {
                    "security_id": security_id,
                    "session": str(day.date()),
                    "open_raw": close,
                    "high_raw": close,
                    "low_raw": close,
                    "close_raw": close,
                    "volume": volumes[security_id],
                    "cash_distribution": 0.0,
                    "split_factor": 1.0,
                    "total_return_factor": 1.0 + (0.40 / close if security_id == "SEC-A" else 0.05 / close if security_id == "SEC-B" else 0.20 / close),
                    "source_status": "observed",
                }
            )
    prices = pd.DataFrame(price_rows)
    calendar = pd.DataFrame(
        {
            "session": [str(day.date()) for day in dates],
            "exchange": "XNYS",
            "open_at": [f"{day.date()}T13:30:00Z" for day in dates],
            "close_at": [f"{day.date()}T20:00:00Z" for day in dates],
        }
    )
    return SignalInputs(
        security_master=master,
        membership_history=membership,
        daily_prices=prices,
        classification_history=classifications,
        trading_calendar=calendar,
    )


def test_formal_signal_engine_uses_point_in_time_features_and_share_class_tie_break() -> None:
    inputs = _inputs()
    targets, audit = build_monthly_target_weights(
        inputs,
        start=str(pd.bdate_range("2018-01-01", periods=260)[-1].date()),
        end="2019-08-23",
    )

    assert not targets.empty
    assert (targets.sum(axis=1) - 1.0).abs().max() < 1e-12
    assert set(audit.columns) == set(FORMAL_SIGNAL_COLUMNS)
    assert "SEC-C" not in set(audit["security_id"])
    first = targets.iloc[0]
    assert first["SEC-A"] == pytest.approx(0.1)
    assert first["SEC-B"] == pytest.approx(0.1)
    assert first["QQQ"] == pytest.approx(0.8)

    baselines = build_baseline_target_weights(targets, audit)
    assert set(baselines) == {
        "pit_eligible_equal_weight_monthly",
        "first_top10_equal_then_drift",
    }
    assert baselines["pit_eligible_equal_weight_monthly"].iloc[0]["QQQ"] == pytest.approx(0.8)
    assert baselines["first_top10_equal_then_drift"].iloc[0]["SEC-A"] == pytest.approx(0.1)
    assert baselines["first_top10_equal_then_drift"].iloc[-1].isna().all()


def test_formal_signal_engine_rejects_membership_known_after_signal() -> None:
    targets, audit = build_monthly_target_weights(
        _inputs(future_membership_announcement=True),
        start="2018-12-31",
        end="2019-08-23",
    )
    assert audit.empty
    assert (targets.drop(columns="QQQ") == 0).all().all()
    assert (targets["QQQ"] == 1.0).all()


def test_formal_signal_engine_excludes_same_day_post_close_membership() -> None:
    inputs = _inputs()
    inputs.membership_history.loc[:, "announced_at"] = "2018-12-31T20:01:00Z"
    targets, audit = build_monthly_target_weights(
        inputs,
        start="2018-12-31",
        end="2018-12-31",
    )
    assert audit.empty
    assert targets.iloc[0]["QQQ"] == pytest.approx(1.0)
