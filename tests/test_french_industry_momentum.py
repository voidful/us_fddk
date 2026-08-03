from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from usfddk.french_industry_momentum import ReturnPath, _simulate

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "artifacts/short_term_french_30_industry_validation.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_return_only_engine_applies_close_signal_to_next_session() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="B")
    returns = pd.DataFrame({"A": [0.10, 0.20, 0.30]}, index=index)
    targets = pd.DataFrame(np.nan, index=index, columns=["A"])
    targets.loc[index[0], "A"] = 1.0
    result: ReturnPath = _simulate(returns, targets, cost_bps=10.0)
    assert result.returns.iloc[0] == 0.0
    assert np.isclose(result.returns.iloc[1], (1.0 - 0.001) * 1.20 - 1.0)
    assert np.isclose(result.returns.iloc[2], 0.30)
    assert result.turnover.iloc[1] == 1.0


def test_frozen_french_30_result_keeps_paper_and_real_money_closed() -> None:
    result = _result()
    assert result["status"] == "academic_industry_mechanism_failed"
    assert result["academic_mechanism_passed"] is False
    assert result["paper_eligible"] is False
    assert result["paper_state_created"] is False
    assert result["trade_ready"] is False
    assert result["real_money_action_usd"] == 0


def test_frozen_french_30_result_has_exact_gate_accounting() -> None:
    result = _result()
    assert result["gate_breakdown"] == {
        "data": "7/7",
        "primary": "8/13",
        "recent": "2/13",
    }
    assert result["passed_gate_count"] == 17
    assert result["required_gate_count"] == 33


def test_primary_evidence_does_not_hide_recent_failure() -> None:
    result = _result()
    primary = result["primary_external_period"]
    recent = result["recent_confirmation_period"]
    assert primary["candidate_metrics"]["cagr"] > 0.14
    assert primary["fixed_20_day_event"]["all_gates_pass"] is True
    assert recent["candidate_metrics"]["cagr"] > 0.12
    assert recent["fixed_20_day_event"]["all_gates_pass"] is False
    assert recent["comparisons"]["market"]["newey_west"]["t_stat"] < 1.0
    assert recent["gates"]["active_global_dsr_vs_market_and_equal_at_least_95pct"] is False


def test_cost_and_top_k_diagnostics_are_not_promoted() -> None:
    result = _result()
    cost = result["frozen_candidate"]["cost_sensitivity_full_history"]
    assert cost["50_bps"]["cagr"] < cost["10_bps"]["cagr"] - 0.04
    assert result["pbo"]["primary"]["pbo"] > 0.90
    assert result["pbo"]["recent"]["pbo"] > 0.80
    assert result["frozen_candidate"]["latest_selected_industries_not_trade_instruction"]
