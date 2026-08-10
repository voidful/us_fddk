"""Render an internal report from one immutable formal-run receipt.

This module is deliberately separate from :mod:`usfddk.site_export`.  A formal
run summary is descriptive research evidence, not a public decision payload;
failure receipts are rendered as internal logs and can never become a Paper or
real-money instruction through this renderer.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

FORMAL_REPORT_VERSION = "round50-formal-research-report-v1"
FORMAL_COSTS_BPS = (10, 25, 50)
FORMAL_BASELINES = (
    "QQQ_buy_hold",
    "SPY_buy_hold",
    "pit_eligible_equal_weight_monthly",
    "first_top10_equal_then_drift",
)

_BASELINE_LABELS = {
    "QQQ_buy_hold": "QQQ 買入並持有",
    "SPY_buy_hold": "SPY 買入並持有",
    "pit_eligible_equal_weight_monthly": "PIT 合資格等權（月度）",
    "first_top10_equal_then_drift": "首輪 Top-10 等權後漂移",
}
_METRIC_FIELDS = (
    "cagr",
    "max_drawdown",
    "volatility",
    "excess_sharpe",
    "annual_turnover",
    "total_costs",
    "transactions",
    "terminal_usd",
)
_FAILURE_STATUS = "formal_backtest_failed_no_promotion"


class FormalReportError(ValueError):
    """Fail-closed report input error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalReportError(code, detail)


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("formal_report_schema_invalid", f"{label} 必須是 JSON object")
    return value


def _as_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        _fail("formal_report_value_invalid", f"{label} 不可為 boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        _fail("formal_report_value_invalid", f"{label} 必須是數字：{type(exc).__name__}")
    if not math.isfinite(number):
        _fail("formal_report_value_invalid", f"{label} 必須是有限數字")
    return number


def _as_sequence(value: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        _fail("formal_report_schema_invalid", f"{label} 必須是 array")
    return tuple(value)


def _as_integer(value: Any, label: str) -> int:
    number = _as_finite_number(value, label)
    if not number.is_integer():
        _fail("formal_report_value_invalid", f"{label} 必須是整數")
    return int(number)


def _require_policy_boundary(receipt: Mapping[str, Any]) -> None:
    if receipt.get("paper_authorized") is not False:
        _fail("formal_report_promotion_boundary_invalid", "Paper 必須保持未授權")
    if "real_money_action_usd" not in receipt or _as_finite_number(
        receipt["real_money_action_usd"], "real_money_action_usd"
    ) != 0.0:
        _fail("formal_report_promotion_boundary_invalid", "實金動作必須是 US$0")
    if receipt.get("public_promotion_allowed") is not False:
        _fail("formal_report_promotion_boundary_invalid", "公開升格必須保持 false")


def _receipt_kind(receipt: Mapping[str, Any]) -> str:
    _require_policy_boundary(receipt)
    status = receipt.get("status")
    if status == _FAILURE_STATUS:
        if receipt.get("formal_stock_backtest_completed") is not False:
            _fail("formal_report_schema_invalid", "失敗收據必須 completed=false")
        for key in ("failure_code", "failure_detail"):
            if not isinstance(receipt.get(key), str) or not receipt[key].strip():
                _fail("formal_report_schema_invalid", f"失敗收據缺少 {key}")
        return "failure"
    if receipt.get("formal_stock_backtest_completed") is True and status in (
        None,
        "formal_backtest_completed",
    ):
        return "success"
    _fail("formal_report_schema_invalid", "收據不是正式成功摘要或指定失敗收據")


def _validate_success(receipt: Mapping[str, Any]) -> None:
    if not isinstance(receipt.get("run_id"), str) or not receipt["run_id"].strip():
        _fail("formal_report_schema_invalid", "成功摘要缺少 run_id")
    for key in ("study_start", "study_end"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            _fail("formal_report_schema_invalid", f"成功摘要缺少 {key}")
    if _as_sequence(receipt.get("costs_bps"), "costs_bps") != FORMAL_COSTS_BPS:
        _fail("formal_report_schema_invalid", "成本敏感度必須完整包含 10／25／50 bps")
    if _as_sequence(receipt.get("baseline_keys"), "baseline_keys") != FORMAL_BASELINES:
        _fail("formal_report_schema_invalid", "baseline 次序或集合不符合凍結協議")
    cost_runs = _as_mapping(receipt.get("cost_runs"), "cost_runs")
    if set(cost_runs) != {str(value) for value in FORMAL_COSTS_BPS}:
        _fail("formal_report_schema_invalid", "cost_runs 必須逐一包含 10／25／50 bps")
    for cost_bps in FORMAL_COSTS_BPS:
        cost_run = _as_mapping(cost_runs[str(cost_bps)], f"cost_runs[{cost_bps}]")
        performance = _as_mapping(cost_run.get("performance"), f"performance[{cost_bps}]")
        metrics = _as_mapping(performance.get("metrics"), f"metrics[{cost_bps}]")
        expected_paths = {"candidate", *FORMAL_BASELINES}
        if set(metrics) != expected_paths:
            _fail("formal_report_schema_invalid", f"{cost_bps} bps 缺候選或 baseline metrics")
        for path_key in expected_paths:
            row = _as_mapping(metrics[path_key], f"metrics[{cost_bps}][{path_key}]")
            for field in _METRIC_FIELDS:
                _as_finite_number(row.get(field), f"{cost_bps} bps {path_key}.{field}")
        comparisons = _as_mapping(
            performance.get("comparisons"), f"comparisons[{cost_bps}]"
        )
        if set(comparisons) != set(FORMAL_BASELINES):
            _fail("formal_report_schema_invalid", f"{cost_bps} bps 缺 baseline comparison")
        for baseline in FORMAL_BASELINES:
            comparison = _as_mapping(
                comparisons[baseline], f"comparisons[{cost_bps}][{baseline}]"
            )
            for field in ("cagr_difference", "max_drawdown_difference", "positive_active_fraction"):
                _as_finite_number(comparison.get(field), f"{cost_bps} bps {baseline}.{field}")
            nw = _as_mapping(
                comparison.get("active_return_newey_west"),
                f"{cost_bps} bps {baseline}.active_return_newey_west",
            )
            _as_finite_number(nw.get("t_stat"), f"{cost_bps} bps {baseline}.NW t")
            psr = _as_mapping(
                comparison.get("active_psr"), f"{cost_bps} bps {baseline}.active_psr"
            )
            dsr = _as_mapping(
                comparison.get("active_dsr"), f"{cost_bps} bps {baseline}.active_dsr"
            )
            _as_finite_number(psr.get("probability"), f"{cost_bps} bps {baseline}.PSR")
            _as_finite_number(dsr.get("probability"), f"{cost_bps} bps {baseline}.DSR")
            _as_finite_number(dsr.get("trials"), f"{cost_bps} bps {baseline}.trials")


def validate_formal_receipt(receipt: Mapping[str, Any]) -> str:
    """Validate a run receipt and return ``success`` or ``failure``."""

    if not isinstance(receipt, Mapping):
        _fail("formal_report_schema_invalid", "收據必須是 JSON object")
    kind = _receipt_kind(receipt)
    if kind == "success":
        _validate_success(receipt)
    return kind


def load_formal_receipt(run_directory: str | Path) -> tuple[dict[str, Any], Path]:
    """Load exactly one immutable success summary or failure receipt."""

    directory = Path(run_directory).resolve()
    if not directory.is_dir() or directory.is_symlink():
        _fail("formal_report_input_invalid", "run directory 必須是實體目錄")
    candidates = [directory / "run_summary.json", directory / "run_failure.json"]
    existing = [path for path in candidates if path.is_file() and not path.is_symlink()]
    if len(existing) != 1:
        _fail("formal_report_input_invalid", "run directory 必須恰好有一份正式收據")
    try:
        payload = json.loads(existing[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("formal_report_input_invalid", f"正式收據無法讀取：{type(exc).__name__}")
    if not isinstance(payload, dict):
        _fail("formal_report_input_invalid", "正式收據必須是 JSON object")
    validate_formal_receipt(payload)
    return payload, existing[0]


def _pct(value: Any, digits: int = 2) -> str:
    return f"{_as_finite_number(value, 'percentage'):.{digits}%}"


def _usd(value: Any) -> str:
    return f"US${_as_finite_number(value, 'USD'):,.2f}"


def _num(value: Any, digits: int = 2) -> str:
    return f"{_as_finite_number(value, 'number'):,.{digits}f}"


def _metric_row(path_key: str, metrics: Mapping[str, Any]) -> str:
    label = "候選策略" if path_key == "candidate" else _BASELINE_LABELS[path_key]
    return (
        f"| {label} | {_pct(metrics['cagr'])} | {_pct(metrics['max_drawdown'], 1)} | "
        f"{_pct(metrics['volatility'])} | {_num(metrics['excess_sharpe'])} | "
        f"{_pct(metrics['annual_turnover'])} | {_usd(metrics['total_costs'])} | "
                f"{_as_integer(metrics['transactions'], 'transactions'):,} | "
        f"{_usd(metrics['terminal_usd'])} |"
    )


def _render_success(receipt: Mapping[str, Any]) -> str:
    cost_runs = receipt["cost_runs"]
    sections: list[str] = []
    for cost_bps in FORMAL_COSTS_BPS:
        performance = cost_runs[str(cost_bps)]["performance"]
        metrics = performance["metrics"]
        rows = "\n".join(
            _metric_row(path_key, metrics[path_key])
            for path_key in ("candidate", *FORMAL_BASELINES)
        )
        comparisons = performance["comparisons"]
        comparison_rows = "\n".join(
            "| {label} | {cagr} | {mdd} | {positive} | {nw} | {psr} | {dsr} | {trials} |".format(
                label=_BASELINE_LABELS[baseline],
                cagr=_pct(comparisons[baseline]["cagr_difference"]),
                mdd=_pct(comparisons[baseline]["max_drawdown_difference"], 1),
                positive=_pct(comparisons[baseline]["positive_active_fraction"], 1),
                nw=_num(comparisons[baseline]["active_return_newey_west"]["t_stat"]),
                psr=_pct(comparisons[baseline]["active_psr"]["probability"], 1),
                dsr=_pct(comparisons[baseline]["active_dsr"]["probability"], 1),
                trials=f"{_as_integer(comparisons[baseline]['active_dsr']['trials'], 'trials'):,}",
            )
            for baseline in FORMAL_BASELINES
        )
        sections.append(
            f"""### 單邊 {cost_bps} bps

| 路徑 | CAGR | 最大跌幅 | 波幅 | 超額 Sharpe | 年率化換手 | 成交成本 | 交易筆數 | 期末資金 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{rows}

| 相對基準 | CAGR 差 | 最大跌幅差 | 正回報日比例 | NW t | PSR | DSR | 全域 trials |
|---|---:|---:|---:|---:|---:|---:|---:|
{comparison_rows}"""
        )
    return f"""# 短線正式回測內部研究報表

報表版本：`{FORMAL_REPORT_VERSION}`<br>
Run ID：`{receipt['run_id']}`<br>
研究期：{receipt['study_start']} 至 {receipt['study_end']}

## 結論先行

正式 provider 回測已完成，以下只列凍結候選策略與四個預先登記 baseline 的描述性結果，並按 10／25／50 bps 成交成本分開呈現。這不是盈利保證，也不等同可落盤。

- Paper：未授權；狀態保持全現金。
- 實金動作：US$0。
- 公開升格：不允許；本報表不得接入公開決策頁。

## 路徑與成本敏感度

{chr(10).join(sections)}

## 使用邊界

這份文件是 repository 外／owner-only 研究 log 的顯示層。只有另行通過正式 release 閘門的成功白名單，才可由網站呈現策略及行動建議；任何失敗收據只保留在內部 log，不會被轉成 Paper、實金或公開建議。
"""


def _render_failure(receipt: Mapping[str, Any]) -> str:
    return f"""# 短線正式回測內部研究 log

狀態：正式回測失敗，未升格<br>
Run ID：`{receipt.get('run_id', 'unknown')}`<br>
failure code：`{receipt['failure_code']}`

## 收據

{receipt['failure_detail']}

- Formal backtest：未完成
- Paper：未授權；全現金
- 實金動作：US$0
- 公開升格：不允許

失敗只寫入內部 log；不在同一資料上改參數、重跑救援或產生網站策略／行動建議。
"""


def render_formal_backtest_report(receipt: Mapping[str, Any]) -> str:
    """Render one validated success summary or failure receipt as Markdown."""

    kind = validate_formal_receipt(receipt)
    return _render_success(receipt) if kind == "success" else _render_failure(receipt)
