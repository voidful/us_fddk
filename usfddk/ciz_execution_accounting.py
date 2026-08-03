from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from .crsp_ciz_adapter import transform_crsp_ciz_bundle
from .crsp_ciz_mapping_validation import (
    CONTROL_REQUIREMENTS,
    _mutate_table,
    _write_control_bundle,
    run_crsp_ciz_mapping_validation,
)
from .point_in_time_ledger import audit_point_in_time_bundle

EXECUTION_PROTOCOL_SHA256 = (
    "db3b7e95c1a47d5284e1a699e19a0032bf86fb332089b267559add6b8bf5acff"
)
ROUND13_ADAPTER_SHA256_AT_FREEZE = (
    "2ce8c8c6d760153d094c9511c9a1d2aa9a510328c729e289abdb523618d6cbab"
)
EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}


class ExecutionAccountingError(ValueError):
    """Fail-closed execution/accounting error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise ExecutionAccountingError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settle_delisting_return(
    last_value: float,
    delisting_return: float | None,
    *,
    apply_storage_return: bool,
    apply_outcome_return: bool,
) -> float:
    if apply_storage_return and apply_outcome_return:
        _fail(
            "delisting_return_double_count",
            "DelDlyDt storage DlyRet 與 outcome DelRet 不可同時計入",
        )
    if delisting_return is None or not math.isfinite(delisting_return):
        _fail("missing_exit_economics", "沒有可用 DelRet")
    if delisting_return < -1:
        _fail("missing_exit_economics", "DelRet 不可低於 -1")
    if not (apply_storage_return ^ apply_outcome_return):
        _fail("missing_exit_economics", "DelRet 必須恰好由一條路徑結算")
    return float(last_value) * (1.0 + float(delisting_return))


def settle_cash_exit(
    *,
    last_value: float,
    shares: float,
    delisting_return: float | None,
    cash_consideration: float | None,
    apply_return: bool,
    apply_cash: bool,
) -> float:
    if apply_return and apply_cash:
        _fail(
            "cash_exit_double_count",
            "現金收購不可同時計 DelRet 及每股現金代價",
        )
    if apply_return:
        return settle_delisting_return(
            last_value,
            delisting_return,
            apply_storage_return=False,
            apply_outcome_return=True,
        )
    if apply_cash:
        if cash_consideration is None or not math.isfinite(cash_consideration):
            _fail("missing_exit_economics", "現金退出缺每股代價")
        if cash_consideration <= 0 or shares < 0:
            _fail("missing_exit_economics", "現金退出代價或股數無效")
        return float(shares) * float(cash_consideration)
    _fail("missing_exit_economics", "現金退出沒有選定唯一結算路徑")


def settle_stock_exit(
    shares: float,
    successor_security_id: str,
    share_ratio: float | None,
) -> tuple[str, float]:
    if (
        not successor_security_id
        or share_ratio is None
        or not math.isfinite(share_ratio)
        or share_ratio <= 0
        or shares < 0
    ):
        _fail("stock_exit_terms_missing", "換股退出缺 successor 或正換股比率")
    return successor_security_id, float(shares) * float(share_ratio)


def apply_split_once(
    *,
    shares: float,
    pre_split_price: float,
    share_ratio: float,
    post_split_price: float,
    apply_ratio_to_shares: bool,
    apply_ratio_as_return: bool,
) -> dict[str, float]:
    if apply_ratio_to_shares and apply_ratio_as_return:
        _fail("split_double_count", "拆細比率不可同時調股數及當成額外回報")
    if not apply_ratio_to_shares or apply_ratio_as_return:
        _fail("split_double_count", "拆細只可透過股數路徑結算一次")
    if min(shares, pre_split_price, share_ratio, post_split_price) <= 0:
        _fail("split_double_count", "拆細例子含非正數")
    before = float(shares) * float(pre_split_price)
    after_shares = float(shares) * float(share_ratio)
    after = after_shares * float(post_split_price)
    return {"before_value": before, "after_shares": after_shares, "after_value": after}


def credit_dividend_cash(
    *,
    shares: float,
    cash_per_share: float,
    ex_date: str,
    pay_date: str,
    credit_date: str,
) -> float:
    ex_day = pd.Timestamp(ex_date)
    pay_day = pd.Timestamp(pay_date)
    credit_day = pd.Timestamp(credit_date)
    if pay_day < ex_day:
        _fail("dividend_cash_available_early", "pay-date 早於 ex-date")
    if credit_day < pay_day:
        _fail("dividend_cash_available_early", "付款日前不得釋放可交易現金")
    if shares < 0 or cash_per_share <= 0:
        _fail("dividend_cash_available_early", "派息股數或金額無效")
    return float(shares) * float(cash_per_share)


def require_next_open_execution(
    *,
    signal_date: str,
    execution_date: str,
    sessions: list[str],
    open_price: float | None,
    forward_filled: bool = False,
) -> None:
    ordered = [pd.Timestamp(day) for day in sessions]
    signal = pd.Timestamp(signal_date)
    execution = pd.Timestamp(execution_date)
    later = [day for day in ordered if day > signal]
    valid_open = open_price is not None and math.isfinite(open_price) and open_price > 0
    if not later or execution != later[0] or not valid_open or forward_filled:
        _fail(
            "execution_clock_violation",
            "訊號只可在下一正式交易日真實 open 成交，不得同日或補值",
        )


def require_benchmark_execution_data(
    available: dict[str, set[str]], required_sessions: set[str]
) -> None:
    required = {"QQQ", "SPY"}
    if set(available) != required:
        _fail("benchmark_execution_data_missing", "缺 QQQ／SPY 同步行情")
    if any(not required_sessions.issubset(available[ticker]) for ticker in required):
        _fail("benchmark_execution_data_missing", "QQQ／SPY 同日 open／回報覆蓋不足")


def _read_ledger(bundle: Path) -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(bundle / name, dtype=str, keep_default_na=False, na_filter=False)
        for name in (
            "security_master.csv",
            "membership_history.csv",
            "trading_calendar.csv",
            "daily_prices.csv",
            "corporate_actions.csv",
            "security_outcomes.csv",
        )
    }


def require_pre_signal_history(
    tables: dict[str, pd.DataFrame], *, required_return_sessions: int = 252
) -> dict[str, int]:
    calendar = pd.DatetimeIndex(pd.to_datetime(tables["trading_calendar.csv"]["session"])).sort_values()
    prices = tables["daily_prices.csv"].copy()
    prices["__session"] = pd.to_datetime(prices["session"])
    memberships = tables["membership_history.csv"].copy()
    memberships["__start"] = pd.to_datetime(memberships["effective_from"])
    minimum = required_return_sessions
    failures: list[str] = []
    for _, row in memberships.iterrows():
        start = row["__start"]
        history_sessions = calendar[calendar < start]
        available = prices.loc[
            (prices["security_id"] == row["security_id"])
            & (prices["__session"].isin(history_sessions)),
            "__session",
        ].nunique()
        minimum = min(minimum, int(available))
        if available < required_return_sessions:
            failures.append(str(row["security_id"]))
    if failures:
        _fail(
            "pre_signal_history_missing",
            f"至少一隻候選不足 {required_return_sessions} 個訊號前交易日：{failures[:3]}",
        )
    return {"minimum_return_sessions": minimum, "required_return_sessions": required_return_sessions}


def require_post_removal_execution_prices(
    tables: dict[str, pd.DataFrame]
) -> dict[str, int]:
    calendar = pd.DatetimeIndex(pd.to_datetime(tables["trading_calendar.csv"]["session"])).sort_values()
    prices = tables["daily_prices.csv"].copy()
    prices["__session"] = pd.to_datetime(prices["session"])
    outcomes = tables["security_outcomes.csv"]
    checked = 0
    for row in outcomes.loc[outcomes["outcome_type"] == "removed_continues"].itertuples(index=False):
        removed = pd.Timestamp(row.membership_effective_to)
        later = calendar[calendar >= removed]
        if not len(later):
            _fail("post_removal_execution_price_missing", "移除後沒有交易日曆")
        by_month = pd.Series(later, index=later).groupby(later.to_period("M"))
        month_end = by_month.max().iloc[0]
        executions = calendar[calendar > month_end]
        if not len(executions):
            _fail(
                "post_removal_execution_price_missing",
                "未覆蓋移除後首個完整月末的下一開市",
            )
        execution = executions[0]
        needed = calendar[(calendar >= removed) & (calendar <= execution)]
        rows = prices.loc[prices["security_id"] == row.security_id]
        available = set(rows["__session"])
        if any(day not in available for day in needed):
            _fail(
                "post_removal_execution_price_missing",
                f"{row.security_id} 移除後至 {execution.date()} 價格中斷",
            )
        execution_row = rows.loc[rows["__session"] == execution]
        if execution_row.empty or execution_row.iloc[0]["open_raw"] == "":
            _fail("post_removal_execution_price_missing", "退出重新平衡 open 缺失")
        checked += 1
    return {"removed_continues_checked": checked}


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt_path = root / "artifacts/short_term_ciz_execution_accounting_protocol_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        tracked = (
            receipt["protocol"],
            receipt["round13_mapping_protocol"],
            receipt["round13_mapping_receipt"],
            receipt["point_in_time_contract"],
            receipt["strategy_protocol"],
            receipt["round13_adapter_at_freeze"],
        )
        checks = {
            item["path"]: _sha256_file(root / item["path"]) == item["sha256"]
            for item in tracked
        }
        passed = bool(
            receipt["status"]
            == "frozen_before_execution_accounting_auditor_implementation"
            and receipt["protocol"]["sha256"] == EXECUTION_PROTOCOL_SHA256
            and receipt["round13_adapter_at_freeze"]["sha256"]
            == ROUND13_ADAPTER_SHA256_AT_FREEZE
            and receipt["frozen_gate_count"] == 12
            and receipt["frozen_attack_count"] == 10
            and receipt["execution_accounting_auditor_implemented_at_freeze"] is False
            and receipt["authorized_provider_sample_present_at_freeze"] is False
            and all(checks.values())
        )
        return {"passed": passed, "frozen_at": receipt["frozen_at"], "hash_checks": checks}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {"passed": False, "error": type(exc).__name__}


def _transform_scenario(
    parent: Path,
    name: str,
    root: Path,
    mutators: list[tuple[str, Callable[[pd.DataFrame], None]]],
) -> tuple[Path, Path, dict[str, Any]]:
    source = _write_control_bundle(parent / f"{name}-source")
    for filename, mutate in mutators:
        _mutate_table(source, filename, mutate)
    output = parent / f"{name}-ledger"
    mapping = transform_crsp_ciz_bundle(source, output, root=root)
    return source, output, mapping


def _cash_scenario(parent: Path, root: Path) -> tuple[Path, Path, dict[str, Any]]:
    def clear_delret(frame: pd.DataFrame) -> None:
        frame.loc[0, "DelRet"] = ""
        frame.loc[0, "DelRetMissType"] = "MP"

    def cash_terms(frame: pd.DataFrame) -> None:
        frame.loc[0, "OutcomeType"] = "acquired_cash"
        frame.loc[0, "CashConsideration"] = "50"

    def cash_action(frame: pd.DataFrame) -> None:
        frame.loc[0, "EventType"] = "merger_cash"
        frame.loc[0, "CashAmount"] = "50"

    def missing_storage_return(frame: pd.DataFrame) -> None:
        row = (frame["PERMNO"] == "10001") & (frame["DlyCalDt"] == "2026-07-31")
        frame.loc[row, "DlyRet"] = ""
        frame.loc[row, "DlyRetMissFlg"] = "MP"

    return _transform_scenario(
        parent,
        "cash",
        root,
        [
            ("stk_delists.csv", clear_delret),
            ("exit_terms.csv", cash_terms),
            ("corporate_action_overlay.csv", cash_action),
            ("stk_dly_security_data.csv", missing_storage_return),
        ],
    )


def _stock_scenario(parent: Path, root: Path) -> tuple[Path, Path, dict[str, Any]]:
    def clear_delret(frame: pd.DataFrame) -> None:
        frame.loc[0, "DelRet"] = ""
        frame.loc[0, "DelRetMissType"] = "MP"
        frame.loc[0, "DelPERMNO"] = "10002"
        frame.loc[0, "DelPERMCO"] = "5002"

    def stock_terms(frame: pd.DataFrame) -> None:
        frame.loc[0, "OutcomeType"] = "acquired_stock"
        frame.loc[0, "ShareRatio"] = "0.5"
        frame.loc[0, "SuccessorPERMNO"] = "10002"

    def stock_action(frame: pd.DataFrame) -> None:
        frame.loc[0, "EventType"] = "merger_stock"
        frame.loc[0, "ShareRatio"] = "0.5"
        frame.loc[0, "SuccessorPERMNO"] = "10002"

    def missing_storage_return(frame: pd.DataFrame) -> None:
        row = (frame["PERMNO"] == "10001") & (frame["DlyCalDt"] == "2026-07-31")
        frame.loc[row, "DlyRet"] = ""
        frame.loc[row, "DlyRetMissFlg"] = "MP"

    return _transform_scenario(
        parent,
        "stock",
        root,
        [
            ("stk_delists.csv", clear_delret),
            ("exit_terms.csv", stock_terms),
            ("corporate_action_overlay.csv", stock_action),
            ("stk_dly_security_data.csv", missing_storage_return),
        ],
    )


def _dividend_scenario(parent: Path, root: Path) -> tuple[Path, Path, dict[str, Any]]:
    def add_distribution(frame: pd.DataFrame) -> None:
        frame.loc[len(frame)] = {
            "PERMNO": "10002",
            "DisExDt": "2026-07-30",
            "DisSeqnbr": "1",
            "DisType": "CD",
            "DisOrdinaryFlg": "Y",
            "DisDeclareDt": "2026-07-28",
            "DisPayDt": "2026-08-03",
            "DisDivAmt": "0.5",
            "DisFacPr": "1",
            "DisFacShr": "1",
            "DisPERMNO": "",
        }

    def add_overlay(frame: pd.DataFrame) -> None:
        frame.loc[len(frame)] = {
            "SourceTable": "StkDistributions",
            "PERMNO": "10002",
            "EventDate": "2026-07-30",
            "Sequence": "1",
            "EventType": "dividend",
            "AnnouncedAt": "2026-07-28T20:00:00Z",
            "CashAmount": "0.5",
            "ShareRatio": "",
            "SuccessorPERMNO": "",
            "EvidenceReference": "synthetic-dividend-announcement",
        }

    def daily_cash(frame: pd.DataFrame) -> None:
        row = (frame["PERMNO"] == "10002") & (frame["DlyCalDt"] == "2026-07-30")
        frame.loc[row, "DlyOrdDivAmt"] = "0.5"

    return _transform_scenario(
        parent,
        "dividend",
        root,
        [
            ("stk_distributions.csv", add_distribution),
            ("corporate_action_overlay.csv", add_overlay),
            ("stk_dly_security_data.csv", daily_cash),
        ],
    )


def _share_action_scenario(parent: Path, root: Path) -> tuple[Path, Path, dict[str, Any]]:
    def add_distributions(frame: pd.DataFrame) -> None:
        rows = [
            {
                "PERMNO": "10002",
                "DisExDt": "2026-07-30",
                "DisSeqnbr": "1",
                "DisType": "SPLIT",
                "DisOrdinaryFlg": "N",
                "DisDeclareDt": "2026-07-28",
                "DisPayDt": "2026-07-30",
                "DisDivAmt": "0",
                "DisFacPr": "2",
                "DisFacShr": "2",
                "DisPERMNO": "",
            },
            {
                "PERMNO": "10002",
                "DisExDt": "2026-07-30",
                "DisSeqnbr": "2",
                "DisType": "SPIN",
                "DisOrdinaryFlg": "N",
                "DisDeclareDt": "2026-07-28",
                "DisPayDt": "2026-07-30",
                "DisDivAmt": "0",
                "DisFacPr": "1",
                "DisFacShr": "0.25",
                "DisPERMNO": "10003",
            },
        ]
        for row in rows:
            frame.loc[len(frame)] = row

    def add_overlays(frame: pd.DataFrame) -> None:
        rows = [
            {
                "SourceTable": "StkDistributions",
                "PERMNO": "10002",
                "EventDate": "2026-07-30",
                "Sequence": "1",
                "EventType": "split",
                "AnnouncedAt": "2026-07-28T20:00:00Z",
                "CashAmount": "",
                "ShareRatio": "2",
                "SuccessorPERMNO": "",
                "EvidenceReference": "synthetic-split-announcement",
            },
            {
                "SourceTable": "StkDistributions",
                "PERMNO": "10002",
                "EventDate": "2026-07-30",
                "Sequence": "2",
                "EventType": "spinoff",
                "AnnouncedAt": "2026-07-28T20:00:00Z",
                "CashAmount": "",
                "ShareRatio": "0.25",
                "SuccessorPERMNO": "10003",
                "EvidenceReference": "synthetic-spinoff-announcement",
            },
        ]
        for row in rows:
            frame.loc[len(frame)] = row

    return _transform_scenario(
        parent,
        "share-actions",
        root,
        [
            ("stk_distributions.csv", add_distributions),
            ("corporate_action_overlay.csv", add_overlays),
        ],
    )


def _removal_scenario(parent: Path, root: Path) -> tuple[Path, Path, dict[str, Any]]:
    def end_membership(frame: pd.DataFrame) -> None:
        row = frame["PERMNO"] == "10002"
        frame.loc[row, "MbrEndDt"] = "2026-07-30"

    return _transform_scenario(
        parent,
        "removal",
        root,
        [
            ("stk_ind_membership.csv", end_membership),
            ("membership_announcements.csv", end_membership),
        ],
    )


def _attack_result(
    attack_id: str,
    label: str,
    expected: str,
    operation: Callable[[], None],
) -> dict[str, Any]:
    observed: str | None = None
    try:
        operation()
    except ExecutionAccountingError as exc:
        observed = exc.code
    return {
        "id": attack_id,
        "label": label,
        "expected_error_code": expected,
        "observed_error_code": observed,
        "rejected": observed == expected,
    }


def run_ciz_execution_accounting_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol = _protocol_integrity(root_path)
    round13 = run_crsp_ciz_mapping_validation(root_path)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用 Round 14 結論")

    with tempfile.TemporaryDirectory(prefix="usfddk-round14-accounting-") as temporary:
        temp = Path(temporary)
        control_source, control_output, control_mapping = _transform_scenario(
            temp, "control", root_path, []
        )
        control_tables = _read_ledger(control_output)
        control_audit = audit_point_in_time_bundle(
            control_output, root=root_path, requirements=CONTROL_REQUIREMENTS
        )
        source_daily = pd.read_csv(
            control_source / "stk_dly_security_data.csv",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
        storage = source_daily[source_daily["DlyDelFlg"] == "Y"].iloc[0]
        outcome = control_tables["security_outcomes.csv"].query(
            "security_id == 'CRSP-PERMNO-10001'"
        ).iloc[0]
        storage_isolated = bool(
            not (
                (control_tables["daily_prices.csv"]["security_id"] == "CRSP-PERMNO-10001")
                & (control_tables["daily_prices.csv"]["session"] == storage["DlyCalDt"])
            ).any()
            and math.isclose(float(storage["DlyRet"]), float(outcome["delisting_return"]))
            and control_mapping["delisting_storage_dates_used_as_exit_dates"] is False
        )
        terminal_value = settle_delisting_return(
            100.0,
            float(outcome["delisting_return"]),
            apply_storage_return=False,
            apply_outcome_return=True,
        )

        _, cash_output, _ = _cash_scenario(temp, root_path)
        cash_tables = _read_ledger(cash_output)
        cash_outcome = cash_tables["security_outcomes.csv"].query(
            "security_id == 'CRSP-PERMNO-10001'"
        ).iloc[0]
        cash_value = settle_cash_exit(
            last_value=100.0,
            shares=2.0,
            delisting_return=None,
            cash_consideration=float(cash_outcome["cash_consideration"]),
            apply_return=False,
            apply_cash=True,
        )

        _, stock_output, _ = _stock_scenario(temp, root_path)
        stock_tables = _read_ledger(stock_output)
        stock_action = stock_tables["corporate_actions.csv"].query(
            "security_id == 'CRSP-PERMNO-10001' and event_type == 'merger_stock'"
        ).iloc[0]
        stock_security, stock_shares = settle_stock_exit(
            4.0,
            stock_action["successor_security_id"],
            float(stock_action["share_ratio"]),
        )

        dividend_source, dividend_output, _ = _dividend_scenario(temp, root_path)
        dividend_source_rows = pd.read_csv(
            dividend_source / "stk_distributions.csv",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
        dividend_action = _read_ledger(dividend_output)["corporate_actions.csv"].query(
            "event_type == 'dividend'"
        ).iloc[0]
        dividend_pay_date = dividend_source_rows.iloc[0]["DisPayDt"]
        dividend_dates_preserved = bool(
            dividend_action["ex_date"] == dividend_source_rows.iloc[0]["DisExDt"]
            and dividend_action["effective_date"] == dividend_pay_date
        )

        _, share_output, _ = _share_action_scenario(temp, root_path)
        share_tables = _read_ledger(share_output)
        actions = share_tables["corporate_actions.csv"]
        split = actions.query("event_type == 'split'").iloc[0]
        spinoff = actions.query("event_type == 'spinoff'").iloc[0]
        split_example = apply_split_once(
            shares=1.0,
            pre_split_price=100.0,
            share_ratio=float(split["share_ratio"]),
            post_split_price=50.0,
            apply_ratio_to_shares=True,
            apply_ratio_as_return=False,
        )
        spin_security, spin_shares = settle_stock_exit(
            4.0,
            spinoff["successor_security_id"],
            float(spinoff["share_ratio"]),
        )
        share_actions_ready = bool(
            split_example == {"before_value": 100.0, "after_shares": 2.0, "after_value": 100.0}
            and spin_security == "CRSP-PERMNO-10003"
            and math.isclose(spin_shares, 1.0)
        )

        _, removal_output, _ = _removal_scenario(temp, root_path)
        removal_tables = _read_ledger(removal_output)

        history_error: str | None = None
        try:
            require_pre_signal_history(control_tables)
        except ExecutionAccountingError as exc:
            history_error = exc.code
        removal_error: str | None = None
        try:
            require_post_removal_execution_prices(removal_tables)
        except ExecutionAccountingError as exc:
            removal_error = exc.code
        benchmark_error: str | None = None
        try:
            require_benchmark_execution_data({}, set(control_tables["trading_calendar.csv"]["session"]))
        except ExecutionAccountingError as exc:
            benchmark_error = exc.code
        require_next_open_execution(
            signal_date="2026-07-29",
            execution_date="2026-07-30",
            sessions=["2026-07-29", "2026-07-30", "2026-07-31"],
            open_price=100.0,
        )

        gates = [
            ("01", "事前凍結完整性", bool(protocol.get("passed")), "協議、收據及前置雜湊對數"),
            (
                "02",
                "第十三輪不變",
                round13["control"]["ledger_gate_summary"]["all_passed"]
                and round13["attack_summary"]["all_rejected"],
                "Round 13 控制 20/20、攻擊 12/12",
            ),
            ("03", "退市儲存列隔離", storage_isolated, "return-only 儲存列不進普通日線"),
            ("04", "退市回報只計一次", math.isclose(terminal_value, 50.0), "100 × (1 − 50%) = 50"),
            ("05", "缺失 DelRet 現金退出", math.isclose(cash_value, 100.0), "2 股 × US$50 = US$100"),
            (
                "06",
                "缺失 DelRet 換股退出",
                stock_security == "CRSP-PERMNO-10002" and math.isclose(stock_shares, 2.0),
                "4 股 × 0.5 = 2 股 successor",
            ),
            (
                "07",
                "派息權利與付款分離",
                dividend_dates_preserved,
                "現行 adapter 把 effective_date 寫成 ex-date，DisPayDt 未保留"
                if not dividend_dates_preserved
                else "ex-date 與 pay-date 均保留",
            ),
            ("08", "拆細／分拆持股會計", share_actions_ready, "拆細及 successor 權利各只結算一次"),
            (
                "09",
                "訊號前歷史覆蓋",
                history_error is None,
                "現行 20 道 audit 未要求每股訊號前 252 日數據"
                if history_error
                else "每股訊號前歷史完整",
            ),
            (
                "10",
                "移除後成交覆蓋",
                removal_error is None,
                "現行 audit 只要求移除日後至少一列，未覆蓋下次月度 open"
                if removal_error
                else "移除後至下一重新平衡 open 完整",
            ),
            (
                "11",
                "公平基準同步",
                benchmark_error is None,
                "八份逐股賬本沒有 QQQ／SPY 及 QQQ 補位行情"
                if benchmark_error
                else "QQQ／SPY 同步完整",
            ),
            ("12", "D+1 執行失敗關閉", True, "下一正式交易日真實 open；同日或補值拒收"),
        ]

        attacks = [
            _attack_result(
                "01",
                "同時計 DelDlyDt DlyRet 及 outcome DelRet",
                "delisting_return_double_count",
                lambda: settle_delisting_return(
                    100.0,
                    -0.5,
                    apply_storage_return=True,
                    apply_outcome_return=True,
                ),
            ),
            _attack_result(
                "02",
                "DelRet 缺失時填 0／沒有退出代價",
                "missing_exit_economics",
                lambda: settle_cash_exit(
                    last_value=100.0,
                    shares=2.0,
                    delisting_return=None,
                    cash_consideration=None,
                    apply_return=False,
                    apply_cash=True,
                ),
            ),
            _attack_result(
                "03",
                "現金收購同時計現金代價及 DelRet",
                "cash_exit_double_count",
                lambda: settle_cash_exit(
                    last_value=100.0,
                    shares=2.0,
                    delisting_return=-0.5,
                    cash_consideration=50.0,
                    apply_return=True,
                    apply_cash=True,
                ),
            ),
            _attack_result(
                "04",
                "換股退出缺 successor／share ratio",
                "stock_exit_terms_missing",
                lambda: settle_stock_exit(4.0, "", None),
            ),
            _attack_result(
                "05",
                "付款日前釋放派息現金",
                "dividend_cash_available_early",
                lambda: credit_dividend_cash(
                    shares=10.0,
                    cash_per_share=0.5,
                    ex_date="2026-07-30",
                    pay_date="2026-08-03",
                    credit_date="2026-07-30",
                ),
            ),
            _attack_result(
                "06",
                "拆細同時調股數及當額外回報",
                "split_double_count",
                lambda: apply_split_once(
                    shares=1.0,
                    pre_split_price=100.0,
                    share_ratio=2.0,
                    post_split_price=50.0,
                    apply_ratio_to_shares=True,
                    apply_ratio_as_return=True,
                ),
            ),
            _attack_result(
                "07",
                "成分移除後價格未覆蓋至下次重新平衡",
                "post_removal_execution_price_missing",
                lambda: require_post_removal_execution_prices(removal_tables),
            ),
            _attack_result(
                "08",
                "新成分沒有 252 日歷史仍計訊號",
                "pre_signal_history_missing",
                lambda: require_pre_signal_history(control_tables),
            ),
            _attack_result(
                "09",
                "缺 QQQ／SPY 仍跑正式比較",
                "benchmark_execution_data_missing",
                lambda: require_benchmark_execution_data(
                    {}, set(control_tables["trading_calendar.csv"]["session"])
                ),
            ),
            _attack_result(
                "10",
                "月末訊號使用同日 open／補值",
                "execution_clock_violation",
                lambda: require_next_open_execution(
                    signal_date="2026-07-29",
                    execution_date="2026-07-29",
                    sessions=["2026-07-29", "2026-07-30", "2026-07-31"],
                    open_price=100.0,
                    forward_filled=True,
                ),
            ),
        ]

    gate_rows = [
        {"id": gate_id, "label": label, "passed": bool(passed), "detail": detail}
        for gate_id, label, passed, detail in gates
    ]
    passed_gates = sum(int(gate["passed"]) for gate in gate_rows)
    rejected = sum(int(attack["rejected"]) for attack in attacks)
    controls_passed = bool(
        protocol.get("passed")
        and control_audit["gate_summary"]["all_passed"]
        and rejected == len(attacks)
    )
    all_execution_ready = passed_gates == len(gate_rows)
    return {
        "schema_version": 1,
        "research_round": 14,
        "status": (
            "execution_accounting_controls_passed_formal_inputs_incomplete"
            if controls_passed and not all_execution_ready
            else "execution_accounting_ready_for_authorized_data"
            if controls_passed and all_execution_ready
            else "execution_accounting_validation_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "protocol_integrity": protocol,
        "official_document_evidence": {
            "ciz_daily_return_includes_delisting_return": True,
            "delisting_storage_date_is_not_trade_date": True,
            "distribution_ex_and_pay_dates_are_distinct_fields": True,
            "sources": [
                {
                    "label": "WRDS Run an Event Study (CIZ Format)",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/",
                },
                {
                    "label": "WRDS CRSP CIZtoSIZ macro",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/",
                },
                {
                    "label": "CRSP US Stock Databases Guide for Flat File Format 2.0",
                    "url": "https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/",
                },
            ],
        },
        "accounting_controls": {
            "delisting_last_value": 100.0,
            "delisting_return": -0.5,
            "delisting_terminal_value_once": terminal_value,
            "cash_exit_shares": 2.0,
            "cash_consideration_per_share": 50.0,
            "cash_exit_terminal_value": cash_value,
            "stock_exit_old_shares": 4.0,
            "stock_exit_ratio": 0.5,
            "stock_exit_successor_shares": stock_shares,
            "split_before_value": split_example["before_value"],
            "split_after_value": split_example["after_value"],
            "spinoff_successor_shares": spin_shares,
        },
        "gate_summary": {
            "passed": passed_gates,
            "total": len(gate_rows),
            "all_passed": all_execution_ready,
        },
        "gates": gate_rows,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attacks),
            "all_rejected": rejected == len(attacks),
        },
        "attacks": attacks,
        "unresolved_execution_inputs": [
            gate["label"] for gate in gate_rows if not gate["passed"]
        ],
        "round13_control_ledger_gates": control_audit["gate_summary"],
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "authorized_provider_sample_received": False,
        "formal_stock_backtest_authorized": False,
        "formal_stock_backtest_completed": False,
        "strategy_rule_changed": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "先凍結 CIZ adapter v2／ledger execution extension：保留 DisPayDt、要求每股訊號前 "
            "252 日、移除後至下次 open 的價格，以及同步 QQQ／SPY；不得先跑策略。"
        ),
        "disclaimer": (
            "本輪證明會計攻擊可拒收並找出四項輸入缺口；不代表正式引擎、供應商數據或策略通過，"
            "不構成投資建議或盈利保證。"
        ),
    }
