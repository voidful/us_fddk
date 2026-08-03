from __future__ import annotations

import pandas as pd
import pytest

from usfddk.models import MarketPanel
from usfddk.paper import (
    PASSIVE_BENCHMARK_KEY,
    build_paper_report,
    forward_paper_evidence,
    load_paper_state,
    update_paper_state,
    write_paper_state,
)
from usfddk.strategies import buy_and_hold_targets


def _slice_panel(panel: MarketPanel, stop: int) -> MarketPanel:
    return MarketPanel(
        panel.open.iloc[:stop],
        panel.high.iloc[:stop],
        panel.low.iloc[:stop],
        panel.close.iloc[:stop],
        panel.volume.iloc[:stop],
        panel.metadata,
    )


def _constant_panel(prices: list[float]) -> MarketPanel:
    index = pd.bdate_range("2026-01-05", periods=len(prices))
    close = pd.DataFrame({"QQQ": prices}, index=index, dtype=float)
    volume = pd.DataFrame(1_000_000.0, index=index, columns=["QQQ"])
    return MarketPanel(close.copy(), close.copy(), close.copy(), close, volume, {})


def test_live_paper_never_backfills_first_trade(synthetic_panel, tmp_path):
    symbols = ["SPY", "SHY"]
    base = _slice_panel(synthetic_panel, 10)
    extended = _slice_panel(synthetic_panel, 11)
    targets = pd.DataFrame(float("nan"), index=extended.close.index, columns=symbols)
    targets.loc[base.end] = [1.0, 0.0]

    state = update_paper_state(
        base,
        targets.loc[base.close.index],
        initial_cash=100_000,
        cost_bps=0,
    )
    assert state["mode"] == "live"
    assert state["transactions"] == []
    assert state["pending_order"]["signal_date"] == base.end.strftime("%Y-%m-%d")

    advanced = update_paper_state(
        extended,
        targets,
        state=state,
        initial_cash=100_000,
        cost_bps=0,
    )
    assert advanced["as_of"] == extended.end.strftime("%Y-%m-%d")
    assert advanced["transactions"][0]["date"] == extended.end.strftime("%Y-%m-%d")
    assert advanced["holdings"]["SPY"]["shares"] > 0

    path = write_paper_state(tmp_path / "paper.json", advanced)
    assert load_paper_state(path)["holdings"] == advanced["holdings"]
    report = build_paper_report(tmp_path / "paper.html", state=advanced, panel=extended)
    report_html = report.read_text(encoding="utf-8")
    assert "LIVE 前瞻帳戶" in report_html
    assert "總報酬單位" in report_html
    assert "調整後價格重基準收據" in report_html


def test_replay_is_labeled_and_executes_next_open(synthetic_panel):
    panel = _slice_panel(synthetic_panel, 8)
    targets = pd.DataFrame(float("nan"), index=panel.close.index, columns=["SPY"])
    targets.loc[panel.close.index[0], "SPY"] = 1.0
    state = update_paper_state(
        panel,
        targets,
        replay_from=panel.close.index[0].strftime("%Y-%m-%d"),
        initial_cash=50_000,
        cost_bps=0,
    )
    assert state["mode"] == "replay"
    assert state["transactions"][0]["date"] == panel.close.index[1].strftime("%Y-%m-%d")


def test_paper_rejects_time_travel(synthetic_panel):
    full = _slice_panel(synthetic_panel, 10)
    targets = pd.DataFrame(float("nan"), index=full.close.index, columns=["SPY"])
    state = update_paper_state(full, targets, cost_bps=0)
    older = _slice_panel(synthetic_panel, 9)
    with pytest.raises(ValueError, match="時間倒退"):
        update_paper_state(
            older,
            targets.loc[older.close.index],
            state=state,
            cost_bps=0,
        )


def test_paper_rejects_strategy_change(synthetic_panel):
    targets = pd.DataFrame(float("nan"), index=synthetic_panel.close.index, columns=["SPY"])
    state = update_paper_state(
        synthetic_panel,
        targets,
        strategy_name="策略 A",
        cost_bps=0,
    )
    with pytest.raises(ValueError, match="策略與既有"):
        update_paper_state(
            synthetic_panel,
            targets,
            state=state,
            strategy_name="策略 B",
            cost_bps=0,
        )


def _forward_state(name: str, ending_equity: float) -> dict:
    dates = pd.bdate_range("2026-01-02", periods=253)
    values = pd.Series(
        [100_000 + (ending_equity - 100_000) * i / 252 for i in range(253)],
        index=dates,
    )
    return {
        "mode": "live",
        "strategy": name,
        "started_at": dates[0].strftime("%Y-%m-%d"),
        "as_of": dates[-1].strftime("%Y-%m-%d"),
        "snapshot_sha256": "same-snapshot",
        "initial_cash": 100_000.0,
        "cash": 0.0,
        "cost_bps": 10.0,
        "holdings": {},
        "pending_order": None,
        "order_history": [{"status": "filled"} for _ in range(6)],
        "transactions": [],
        "equity_curve": [
            {
                "date": day.strftime("%Y-%m-%d"),
                "equity": float(equity),
                "cash": 0.0,
                "turnover": 0.0,
                "cost": 0.0,
                "drawdown": 0.0,
            }
            for day, equity in values.items()
        ],
    }


def test_forward_evidence_requires_one_year_and_beats_exposure_control():
    strategy = _forward_state("strategy", 120_000)
    benchmarks = {
        "SPY": _forward_state("SPY", 110_000),
        "QQQ": _forward_state("QQQ", 130_000),
        PASSIVE_BENCHMARK_KEY: _forward_state(PASSIVE_BENCHMARK_KEY, 115_000),
    }
    result = forward_paper_evidence(strategy, benchmarks)
    assert result["forward_sessions"] == 252
    assert result["filled_rebalances"] == 6
    assert result["remaining_sessions"] == 0
    assert result["remaining_filled_rebalances"] == 0
    assert result["gates"]["beats_spy_total_return"]
    assert result["gates"]["beats_passive_90_10_total_return"]
    assert result["live_confirmed"]


def test_forward_evidence_rejects_unsynchronized_benchmark():
    strategy = _forward_state("strategy", 120_000)
    benchmarks = {
        "SPY": _forward_state("SPY", 110_000),
        "QQQ": _forward_state("QQQ", 130_000),
        PASSIVE_BENCHMARK_KEY: _forward_state(PASSIVE_BENCHMARK_KEY, 115_000),
    }
    benchmarks["SPY"]["as_of"] = "2027-01-01"
    with pytest.raises(ValueError, match="不同步"):
        forward_paper_evidence(strategy, benchmarks)


def test_forward_evidence_rejects_missing_exposure_control():
    strategy = _forward_state("strategy", 120_000)
    benchmarks = {
        "SPY": _forward_state("SPY", 110_000),
        "QQQ": _forward_state("QQQ", 130_000),
    }
    with pytest.raises(ValueError, match=PASSIVE_BENCHMARK_KEY):
        forward_paper_evidence(strategy, benchmarks)


def test_strategy_and_etf_benchmarks_advance_on_same_unseen_open(synthetic_panel):
    base = _slice_panel(synthetic_panel, 10)
    extended = _slice_panel(synthetic_panel, 11)
    strategy_targets = pd.DataFrame(
        float("nan"), index=extended.close.index, columns=["QQQ", "SHY"]
    )
    strategy_targets.loc[base.end] = [0.75, 0.25]

    strategy = update_paper_state(
        base,
        strategy_targets.loc[base.close.index],
        cost_bps=10,
        snapshot_sha256="base",
        strategy_name="strategy",
    )
    benchmarks = {}
    for ticker in ("SPY", "QQQ"):
        benchmarks[ticker] = update_paper_state(
            base,
            buy_and_hold_targets(
                base.close, ticker, signal_on=base.end.strftime("%Y-%m-%d")
            ),
            cost_bps=10,
            snapshot_sha256="base",
            strategy_name=ticker,
        )
    passive_targets = pd.DataFrame(
        float("nan"), index=extended.close.index, columns=["QQQ", "SHY"]
    )
    passive_targets.loc[base.end] = [0.9, 0.1]
    benchmarks[PASSIVE_BENCHMARK_KEY] = update_paper_state(
        base,
        passive_targets.loc[base.close.index],
        cost_bps=10,
        snapshot_sha256="base",
        strategy_name=PASSIVE_BENCHMARK_KEY,
    )

    strategy = update_paper_state(
        extended,
        strategy_targets,
        state=strategy,
        cost_bps=10,
        snapshot_sha256="extended",
        strategy_name="strategy",
    )
    for ticker in ("SPY", "QQQ"):
        benchmarks[ticker] = update_paper_state(
            extended,
            buy_and_hold_targets(
                extended.close,
                ticker,
                signal_on=base.end.strftime("%Y-%m-%d"),
            ),
            state=benchmarks[ticker],
            cost_bps=10,
            snapshot_sha256="extended",
            strategy_name=ticker,
        )
    benchmarks[PASSIVE_BENCHMARK_KEY] = update_paper_state(
        extended,
        passive_targets,
        state=benchmarks[PASSIVE_BENCHMARK_KEY],
        cost_bps=10,
        snapshot_sha256="extended",
        strategy_name=PASSIVE_BENCHMARK_KEY,
    )

    evidence = forward_paper_evidence(strategy, benchmarks)
    assert all(state["as_of"] == strategy["as_of"] for state in benchmarks.values())
    assert all(len(state["transactions"]) >= 1 for state in [strategy, *benchmarks.values()])
    assert evidence["forward_sessions"] == 1
    assert evidence["filled_rebalances"] == 1
    assert evidence["remaining_sessions"] == 251
    assert evidence["remaining_filled_rebalances"] == 5
    assert not evidence["gates"]["max_drawdown_no_worse_than_spy"]
    assert not evidence["gates"]["max_drawdown_no_worse_than_passive_90_10"]
    assert not evidence["live_confirmed"]


def test_v2_v3_and_all_etf_controls_share_first_forward_open_and_are_idempotent(
    synthetic_panel,
):
    """Mirror the first automated LIVE refresh without using future history."""
    base = _slice_panel(synthetic_panel, 10)
    extended = _slice_panel(synthetic_panel, 11)
    signal_date = base.end.strftime("%Y-%m-%d")
    execution_date = extended.end.strftime("%Y-%m-%d")

    target_specs = {
        "v2": {"QQQ": 0.75, "SHY": 0.25},
        "v3": {"QQQ": 1.0, "SHY": 0.0},
        "SPY": {"SPY": 1.0},
        "QQQ": {"QQQ": 1.0},
        PASSIVE_BENCHMARK_KEY: {"QQQ": 0.9, "SHY": 0.1},
    }
    targets: dict[str, pd.DataFrame] = {}
    states: dict[str, dict] = {}
    for name, weights in target_specs.items():
        target = pd.DataFrame(
            float("nan"), index=extended.close.index, columns=list(weights)
        )
        target.loc[base.end] = pd.Series(weights)
        targets[name] = target
        states[name] = update_paper_state(
            base,
            target.loc[base.close.index],
            cost_bps=10,
            snapshot_sha256="base-snapshot",
            strategy_name=name,
        )
        assert states[name]["started_at"] == signal_date
        assert states[name]["as_of"] == signal_date
        assert states[name]["transactions"] == []
        assert states[name]["pending_order"]["signal_date"] == signal_date

    for name in target_specs:
        states[name] = update_paper_state(
            extended,
            targets[name],
            state=states[name],
            cost_bps=10,
            snapshot_sha256="first-forward-snapshot",
            strategy_name=name,
        )

    for state in states.values():
        assert state["as_of"] == execution_date
        assert state["pending_order"] is None
        assert state["equity_curve"][-1]["date"] == execution_date
        assert state["equity_curve"][-1]["cost"] > 0.0
        assert state["order_history"][-1]["status"] == "filled"
        assert {row["date"] for row in state["transactions"]} == {execution_date}

    benchmarks = {
        "SPY": states["SPY"],
        "QQQ": states["QQQ"],
        PASSIVE_BENCHMARK_KEY: states[PASSIVE_BENCHMARK_KEY],
    }
    for strategy_name in ("v2", "v3"):
        evidence = forward_paper_evidence(states[strategy_name], benchmarks)
        assert evidence["forward_sessions"] == 1
        assert evidence["filled_rebalances"] == 1
        assert not evidence["live_confirmed"]

    # Re-running the exact same completed session must not duplicate fills,
    # equity observations, costs, or order-history entries.
    before = {
        name: {
            "transactions": len(state["transactions"]),
            "equity_curve": len(state["equity_curve"]),
            "order_history": len(state["order_history"]),
            "total_costs": state["total_costs"],
        }
        for name, state in states.items()
    }
    for name in target_specs:
        states[name] = update_paper_state(
            extended,
            targets[name],
            state=states[name],
            cost_bps=10,
            snapshot_sha256="first-forward-snapshot",
            strategy_name=name,
        )
        assert len(states[name]["transactions"]) == before[name]["transactions"]
        assert len(states[name]["equity_curve"]) == before[name]["equity_curve"]
        assert len(states[name]["order_history"]) == before[name]["order_history"]
        assert states[name]["total_costs"] == pytest.approx(before[name]["total_costs"])


def test_adjusted_price_revision_rebases_units_without_fake_pnl(tmp_path):
    base = _constant_panel([100.0, 100.0])
    targets = pd.DataFrame(float("nan"), index=base.close.index, columns=["QQQ"])
    targets.iloc[-1] = 1.0
    state = update_paper_state(
        base,
        targets,
        cost_bps=0,
        snapshot_sha256="initial",
        strategy_name="test",
    )
    extended = _constant_panel([100.0, 100.0, 100.0])
    state = update_paper_state(
        extended,
        targets.reindex(extended.close.index),
        state=state,
        cost_bps=0,
        snapshot_sha256="before-revision",
        strategy_name="test",
    )
    assert state["equity_curve"][-1]["equity"] == pytest.approx(100_000.0)
    assert state["holdings"]["QQQ"]["shares"] == pytest.approx(1_000.0)

    revised_same_day = _constant_panel([50.0, 50.0, 50.0])
    state = update_paper_state(
        revised_same_day,
        targets.reindex(revised_same_day.close.index),
        state=state,
        cost_bps=0,
        snapshot_sha256="revised",
        strategy_name="test",
    )
    assert state["holdings"]["QQQ"]["shares"] == pytest.approx(2_000.0)
    assert state["holdings"]["QQQ"]["market_value"] == pytest.approx(100_000.0)
    assert len(state["equity_curve"]) == 2
    assert len(state["adjustment_rebases"]) == 1
    event = state["adjustment_rebases"][0]
    assert event["unit_factor"] == pytest.approx(2.0)
    assert event["market_value_before"] == pytest.approx(event["market_value_after"])
    assert event["snapshot_before"] == "before-revision"
    assert event["snapshot_after"] == "revised"

    # Re-reading the same revision is idempotent; a new flat bar does not create a loss.
    state = update_paper_state(
        revised_same_day,
        targets.reindex(revised_same_day.close.index),
        state=state,
        cost_bps=0,
        snapshot_sha256="revised",
        strategy_name="test",
    )
    assert len(state["adjustment_rebases"]) == 1
    revised_with_new_bar = _constant_panel([50.0, 50.0, 50.0, 50.0])
    state = update_paper_state(
        revised_with_new_bar,
        targets.reindex(revised_with_new_bar.close.index),
        state=state,
        cost_bps=0,
        snapshot_sha256="next-day",
        strategy_name="test",
    )
    assert state["equity_curve"][-1]["equity"] == pytest.approx(100_000.0)
    report = build_paper_report(
        tmp_path / "revised-paper.html", state=state, panel=revised_with_new_bar
    )
    report_html = report.read_text(encoding="utf-8")
    assert "單位倍數" in report_html
    assert "2.000000" in report_html
    assert "重基準前市值" in report_html
