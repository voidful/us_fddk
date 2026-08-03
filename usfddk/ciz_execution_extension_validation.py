from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pandas as pd

from .ciz_execution_accounting import run_ciz_execution_accounting_validation
from .ciz_execution_extension import (
    BENCHMARK_COLUMNS,
    FROZEN_DIVIDEND_POLICY,
    FROZEN_EXECUTION_CLOCK,
    FROZEN_PRICE_BASIS,
    FROZEN_PRIMARY_COST_BPS,
    FROZEN_QQQ_FALLBACK,
    FROZEN_SIGNAL_POLICY,
    FROZEN_STRESS_COST_BPS,
    STRATEGY_PROTOCOL_SHA256,
    ExecutionExtensionError,
    audit_ciz_execution_extension_bundle,
    transform_crsp_ciz_execution_bundle,
)
from .crsp_ciz_adapter import CIZ_ADAPTER_VERSION, CIZ_REQUIRED_COLUMNS
from .crsp_ciz_mapping_validation import _control_tables, _daily_row
from .point_in_time_ledger import PointInTimeRequirements

CONTROL_REQUIREMENTS = PointInTimeRequirements(
    start="2026-07-01",
    end="2026-07-31",
    min_daily_members=2,
    max_daily_members=2,
    min_member_price_coverage=1.0,
)
EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame(name: str, rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=CIZ_REQUIRED_COLUMNS[name])


def _calendar_rows() -> list[dict[str, object]]:
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2025-07-01", "2026-08-03")
    return [
        {
            "session": str(session.date()),
            "exchange": "XNYS",
            "open_at": calendar.session_open(session).isoformat().replace("+00:00", "Z"),
            "close_at": calendar.session_close(session).isoformat().replace("+00:00", "Z"),
        }
        for session in sessions
    ]


def _expanded_control_tables() -> dict[str, pd.DataFrame]:
    original = _control_tables()
    security = original["stk_security_info_hist.csv"].copy()
    security.loc[security["PERMNO"] == "10001", "SecInfoEndDt"] = "2026-07-31"
    security.loc[
        (security["PERMNO"] == "10002")
        & (security["SecInfoStartDt"] == "2026-01-01"),
        "SecInfoEndDt",
    ] = "2026-08-03"
    security.loc[security["PERMNO"] == "10003", "SecInfoEndDt"] = "2026-08-03"

    memberships = [
        {
            "PERMNO": "10001",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-01",
            "MbrEndDt": "2026-07-31",
            "MbrFlg": "Y",
        },
        {
            "PERMNO": "10002",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-01",
            "MbrEndDt": "2026-07-15",
            "MbrFlg": "Y",
        },
        {
            "PERMNO": "10003",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-16",
            "MbrEndDt": "2026-08-03",
            "MbrFlg": "Y",
        },
    ]
    calendar_rows = _calendar_rows()
    daily_rows: list[dict[str, object]] = []
    for offset, calendar_row in enumerate(calendar_rows):
        day = str(calendar_row["session"])
        for permno, base_price in (("10001", 100.0), ("10002", 200.0), ("10003", 300.0)):
            if permno == "10001" and day == "2026-08-03":
                daily_rows.append(
                    {
                        "PERMNO": "10001",
                        "DlyCalDt": day,
                        "DlyOpen": "",
                        "DlyHigh": "",
                        "DlyLow": "",
                        "DlyClose": "",
                        "DlyVol": 0,
                        "DlyRet": -0.5,
                        "DlyRetMissFlg": "NA",
                        "DlyOrdDivAmt": 0,
                        "DlynonOrdDivAmt": 0,
                        "DlyFacPrc": 1,
                        "DlyDelFlg": "Y",
                        "TradingStatusFlg": "X",
                    }
                )
                continue
            row = _daily_row(
                permno,
                day,
                base_price + offset * 0.05,
                daily_return=0.001,
            )
            if permno == "10003" and day == "2026-07-30":
                row["DlyOrdDivAmt"] = 0.5
            daily_rows.append(row)

    availability = [
        {
            "PERMNO": row.PERMNO,
            "SecInfoStartDt": row.SecInfoStartDt,
            "SecInfoEndDt": row.SecInfoEndDt,
            "KnownAt": (
                "2019-12-31T20:00:00Z"
                if row.SecInfoStartDt == "2020-01-01"
                else "2025-12-31T20:00:00Z"
            ),
            "EvidenceReference": f"synthetic-secinfo-{row.PERMNO}-{row.SecInfoStartDt}",
        }
        for row in security.itertuples(index=False)
    ]
    announcements = [
        {
            "PERMNO": row["PERMNO"],
            "INDNO": row["INDNO"],
            "MbrStartDt": row["MbrStartDt"],
            "MbrEndDt": row["MbrEndDt"],
            "AnnouncedAt": (
                "2026-06-30T20:00:00Z"
                if row["MbrStartDt"] == "2026-07-01"
                else "2026-07-15T20:00:00Z"
            ),
            "EvidenceReference": f"synthetic-round15-mbr-{row['PERMNO']}",
        }
        for row in memberships
    ]
    distributions = [
        {
            "PERMNO": "10003",
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
    ]
    delists = [
        {
            "PERMNO": "10001",
            "DelistingDt": "2026-07-31",
            "DelDlyDt": "2026-08-03",
            "DelActionType": "DELIST",
            "DelStatusType": "VCL",
            "DelReasonType": "EXCH",
            "DelPaymentType": "PRCF",
            "DelPERMNO": "",
            "DelPERMCO": "",
            "DelRet": -0.5,
            "DelRetMissType": "NA",
            "DelDivAmt": 0,
        }
    ]
    overlays = [
        {
            "SourceTable": "StkDistributions",
            "PERMNO": "10003",
            "EventDate": "2026-07-30",
            "Sequence": "1",
            "EventType": "dividend",
            "AnnouncedAt": "2026-07-29T20:00:00Z",
            "CashAmount": "0.5",
            "ShareRatio": "",
            "SuccessorPERMNO": "",
            "EvidenceReference": "synthetic-round15-dividend-announcement",
        },
        {
            "SourceTable": "StkDelists",
            "PERMNO": "10001",
            "EventDate": "2026-07-31",
            "Sequence": "0",
            "EventType": "delisting",
            "AnnouncedAt": "2026-07-30T20:00:00Z",
            "CashAmount": "",
            "ShareRatio": "",
            "SuccessorPERMNO": "",
            "EvidenceReference": "synthetic-round15-delist-announcement",
        },
    ]
    exit_terms = [
        {
            "PERMNO": "10001",
            "DelistingDt": "2026-07-31",
            "OutcomeType": "delisted",
            "CashConsideration": "",
            "ShareRatio": "",
            "SuccessorPERMNO": "",
            "KnownAt": "2026-08-03T20:00:00Z",
            "EvidenceReference": "synthetic-round15-delist-terms",
        }
    ]
    return {
        "stk_security_info_hist.csv": security.loc[
            :, list(CIZ_REQUIRED_COLUMNS["stk_security_info_hist.csv"])
        ],
        "stk_ind_membership.csv": _frame("stk_ind_membership.csv", memberships),
        "stk_dly_security_data.csv": _frame(
            "stk_dly_security_data.csv", daily_rows
        ),
        "stk_distributions.csv": _frame("stk_distributions.csv", distributions),
        "stk_delists.csv": _frame("stk_delists.csv", delists),
        "trading_calendar.csv": _frame("trading_calendar.csv", calendar_rows),
        "security_info_availability.csv": _frame(
            "security_info_availability.csv", availability
        ),
        "membership_announcements.csv": _frame(
            "membership_announcements.csv", announcements
        ),
        "corporate_action_overlay.csv": _frame(
            "corporate_action_overlay.csv", overlays
        ),
        "exit_terms.csv": _frame("exit_terms.csv", exit_terms),
    }


def _write_ciz_control(parent: Path) -> Path:
    bundle = parent / "synthetic-ciz-round15-control"
    bundle.mkdir(parents=True)
    receipts: dict[str, dict[str, object]] = {}
    for name, frame in _expanded_control_tables().items():
        path = bundle / name
        frame.to_csv(path, index=False, lineterminator="\n")
        receipts[name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    manifest = {
        "schema_version": 1,
        "source_format": "CIZ_FF2",
        "provider": "authorized-synthetic-control-only",
        "provider_product": "round15-ciz-shape-control-no-provider-rows",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-03T21:22:00Z",
            "reference": "synthetic-control-no-provider-rows",
        },
        "exported_at": "2026-08-03T21:22:00Z",
        "first_imported_at": "2026-08-03T21:23:00Z",
        "as_of_date": "2026-08-03",
        "sp500_indno": "1000500",
        "price_basis": "raw_unadjusted_ohlc",
        "membership_date_semantics": "inclusive_source_to_half_open_ledger",
        "delist_storage_semantics": "DelistingDt_last_price_DelDlyDt_storage_only",
        "adapter_version": CIZ_ADAPTER_VERSION,
        "files": receipts,
    }
    (bundle / "ciz_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle


def _benchmark_rows(calendar_rows: list[dict[str, object]]) -> pd.DataFrame:
    required = [
        row for row in calendar_rows if "2026-07-01" <= str(row["session"]) <= "2026-08-03"
    ]
    rows: list[dict[str, object]] = []
    for asset_id, base_price in (("QQQ", 400.0), ("SPY", 600.0)):
        for offset, session in enumerate(required):
            price = base_price + offset * 0.1
            rows.append(
                {
                    "asset_id": asset_id,
                    "session": session["session"],
                    "open_raw": price,
                    "high_raw": price + 1,
                    "low_raw": price - 1,
                    "close_raw": price + 0.5,
                    "volume": 10_000_000,
                    "total_return_factor": 1.001,
                    "source_status": "observed",
                    "source_record_id": f"synthetic-{asset_id}-{session['session']}",
                }
            )
    return pd.DataFrame(rows, columns=BENCHMARK_COLUMNS)


def _write_overlay_control(parent: Path) -> Path:
    bundle = parent / "synthetic-execution-overlay-control"
    bundle.mkdir(parents=True)
    benchmarks = _benchmark_rows(_calendar_rows())
    benchmark_path = bundle / "benchmark_daily.csv"
    benchmarks.to_csv(benchmark_path, index=False, lineterminator="\n")
    manifest = {
        "schema_version": 1,
        "status": "authorized_execution_overlay",
        "provider": "authorized-synthetic-control-only",
        "provider_product": "round15-benchmark-shape-control-no-provider-rows",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-03T22:22:00Z",
            "reference": "synthetic-execution-overlay-no-provider-rows",
        },
        "exported_at": "2026-08-03T22:22:00Z",
        "first_imported_at": "2026-08-03T22:22:30Z",
        "study_start": "2026-07-01",
        "study_end": "2026-07-31",
        "price_basis": FROZEN_PRICE_BASIS,
        "signal_policy": FROZEN_SIGNAL_POLICY,
        "execution_clock": FROZEN_EXECUTION_CLOCK,
        "dividend_cash_policy": FROZEN_DIVIDEND_POLICY,
        "qqq_fallback_asset_id": FROZEN_QQQ_FALLBACK,
        "primary_cost_bps": FROZEN_PRIMARY_COST_BPS,
        "stress_cost_bps": FROZEN_STRESS_COST_BPS,
        "strategy_protocol_sha256": STRATEGY_PROTOCOL_SHA256,
        "files": {
            "benchmark_daily.csv": {
                "sha256": _sha256_file(benchmark_path),
                "rows": len(benchmarks),
            }
        },
    }
    (bundle / "execution_overlay_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle


def _save_execution_manifest(bundle: Path, manifest: dict[str, Any]) -> None:
    (bundle / "execution/execution_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_execution_manifest(bundle: Path) -> dict[str, Any]:
    return json.loads(
        (bundle / "execution/execution_manifest.json").read_text(encoding="utf-8")
    )


def _mutate_execution_manifest(
    bundle: Path, mutate: Callable[[dict[str, Any]], None]
) -> None:
    manifest = _load_execution_manifest(bundle)
    mutate(manifest)
    _save_execution_manifest(bundle, manifest)


def _mutate_execution_table(
    bundle: Path,
    name: str,
    mutate: Callable[[pd.DataFrame], pd.DataFrame | None],
) -> None:
    path = bundle / "execution" / name
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    changed = mutate(frame)
    if changed is not None:
        frame = changed
    frame.to_csv(path, index=False, lineterminator="\n")
    manifest = _load_execution_manifest(bundle)
    manifest["files"][name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    _save_execution_manifest(bundle, manifest)


def _mutate_overlay_table(
    bundle: Path,
    name: str,
    mutate: Callable[[pd.DataFrame], pd.DataFrame | None],
) -> None:
    path = bundle / name
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    changed = mutate(frame)
    if changed is not None:
        frame = changed
    frame.to_csv(path, index=False, lineterminator="\n")
    manifest_path = bundle / "execution_overlay_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
    except ExecutionExtensionError as exc:
        observed = exc.code
    return {
        "id": attack_id,
        "label": label,
        "expected_error_code": expected,
        "observed_error_code": observed,
        "rejected": observed == expected,
    }


def _audit_attack_copy(
    control: Path,
    parent: Path,
    name: str,
    root: Path,
    mutate: Callable[[Path], None],
) -> None:
    target = parent / name
    shutil.copytree(control, target)
    mutate(target)
    audit_ciz_execution_extension_bundle(
        target, root=root, requirements=CONTROL_REQUIREMENTS
    )


def run_ciz_execution_extension_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用 Round 15 結論")
    round14 = run_ciz_execution_accounting_validation(root_path)
    if (
        round14["gate_summary"] != {"passed": 8, "total": 12, "all_passed": False}
        or round14["attack_summary"]
        != {"rejected": 10, "total": 10, "all_rejected": True}
    ):
        raise ValueError("Round 14 結論已漂移；不得沿用 Round 15 協議")

    with tempfile.TemporaryDirectory(prefix="usfddk-round15-extension-") as temporary:
        temp = Path(temporary)
        ciz_source = _write_ciz_control(temp / "source")
        overlay_source = _write_overlay_control(temp / "overlay")
        control = temp / "control-package"
        transform_result = transform_crsp_ciz_execution_bundle(
            ciz_source, overlay_source, control, root=root_path
        )
        control_result = audit_ciz_execution_extension_bundle(
            control, root=root_path, requirements=CONTROL_REQUIREMENTS
        )

        def source_file_attack() -> None:
            attacked_overlay = temp / "attack-source-files"
            shutil.copytree(overlay_source, attacked_overlay)
            (attacked_overlay / "unexpected.csv").write_text("x\n1\n", encoding="utf-8")
            transform_crsp_ciz_execution_bundle(
                ciz_source,
                attacked_overlay,
                temp / "attack-source-files-output",
                root=root_path,
            )

        attacks = [
            _attack_result(
                "01",
                "overlay 多／少檔案",
                "execution_source_file_set_mismatch",
                source_file_attack,
            ),
            _attack_result(
                "02",
                "base manifest 雜湊與 extension 不符",
                "base_ledger_binding_mismatch",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-base-binding",
                    root_path,
                    lambda bundle: _mutate_execution_manifest(
                        bundle,
                        lambda manifest: manifest.__setitem__(
                            "base_ledger_manifest_sha256", "0" * 64
                        ),
                    ),
                ),
            ),
            _attack_result(
                "03",
                "dividend 缺 pay-date",
                "dividend_pay_date_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-pay-date-missing",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "cash_entitlements.csv",
                        lambda frame: frame.assign(pay_date="", cash_available_date=""),
                    ),
                ),
            ),
            _attack_result(
                "04",
                "pay-date 早於 ex-date",
                "dividend_date_order_invalid",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-pay-before-ex",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "cash_entitlements.csv",
                        lambda frame: frame.assign(
                            pay_date="2026-07-29", cash_available_date="2026-07-29"
                        ),
                    ),
                ),
            ),
            _attack_result(
                "05",
                "entitlement 金額或 action ID 不對數",
                "dividend_entitlement_mismatch",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-dividend-terms",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "cash_entitlements.csv",
                        lambda frame: frame.assign(cash_per_share="0.6"),
                    ),
                ),
            ),
            _attack_result(
                "06",
                "候選只有 251 個訊號前回報 session",
                "pre_signal_return_history_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-return-history",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "signal_eligibility.csv",
                        lambda frame: frame.assign(return_sessions="251"),
                    ),
                ),
            ),
            _attack_result(
                "07",
                "候選只有 19 個正成交量 session",
                "pre_signal_liquidity_history_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-volume-history",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "signal_eligibility.csv",
                        lambda frame: frame.assign(positive_volume_sessions="19"),
                    ),
                ),
            ),
            _attack_result(
                "08",
                "移除後路徑中間缺一日",
                "post_removal_path_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-removal-path",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "removal_execution_windows.csv",
                        lambda frame: frame.assign(
                            observed_sessions=(
                                pd.to_numeric(frame["observed_sessions"]) - 1
                            ).astype(str)
                        ),
                    ),
                ),
            ),
            _attack_result(
                "09",
                "下一重新平衡開市價缺失",
                "post_removal_execution_open_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-removal-open",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "removal_execution_windows.csv",
                        lambda frame: frame.assign(execution_open_raw=""),
                    ),
                ),
            ),
            _attack_result(
                "10",
                "SPY 缺一個必要 session",
                "benchmark_session_missing",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-spy-session",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "benchmark_daily.csv",
                        lambda frame: frame.drop(
                            frame.loc[frame["asset_id"] == "SPY"].index[-1]
                        ),
                    ),
                ),
            ),
            _attack_result(
                "11",
                "QQQ 同日重複",
                "benchmark_duplicate",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-qqq-duplicate",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "benchmark_daily.csv",
                        lambda frame: pd.concat(
                            [
                                frame,
                                frame.loc[frame["asset_id"] == "QQQ"]
                                .iloc[[0]]
                                .assign(source_record_id="synthetic-QQQ-duplicate"),
                            ],
                            ignore_index=True,
                        ),
                    ),
                ),
            ),
            _attack_result(
                "12",
                "基準 open 非正或標示 adjusted",
                "benchmark_price_policy_invalid",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-benchmark-price",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "benchmark_daily.csv",
                        lambda frame: frame.assign(
                            open_raw=frame["open_raw"].mask(frame.index == 0, "-1")
                        ),
                    ),
                ),
            ),
            _attack_result(
                "13",
                "QQQ 補位綁定另一 ticker／序列",
                "qqq_fallback_binding_invalid",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-fallback-binding",
                    root_path,
                    lambda bundle: _mutate_execution_manifest(
                        bundle,
                        lambda manifest: manifest.__setitem__(
                            "qqq_fallback_asset_id", "SPY"
                        ),
                    ),
                ),
            ),
            _attack_result(
                "14",
                "月末訊號以同日 open 成交",
                "execution_clock_violation",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-same-day-open",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "removal_execution_windows.csv",
                        lambda frame: frame.assign(
                            execution_session=frame["signal_session"]
                        ),
                    ),
                ),
            ),
            _attack_result(
                "15",
                "primary 或壓力成本被改",
                "strategy_cost_policy_mismatch",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-cost-policy",
                    root_path,
                    lambda bundle: _mutate_execution_manifest(
                        bundle,
                        lambda manifest: manifest.__setitem__("primary_cost_bps", 11),
                    ),
                ),
            ),
            _attack_result(
                "16",
                "插入非月末訊號日",
                "signal_calendar_invalid",
                lambda: _audit_attack_copy(
                    control,
                    temp,
                    "attack-signal-calendar",
                    root_path,
                    lambda bundle: _mutate_execution_table(
                        bundle,
                        "signal_eligibility.csv",
                        lambda frame: pd.concat(
                            [
                                frame,
                                frame.iloc[[0]].assign(
                                    signal_session="2026-07-30",
                                    source_record_id="synthetic-non-month-end",
                                ),
                            ],
                            ignore_index=True,
                        ),
                    ),
                ),
            ),
        ]

    rejected = sum(int(attack["rejected"]) for attack in attacks)
    all_control = control_result["gate_summary"]["all_passed"]
    return {
        "schema_version": 1,
        "research_round": 15,
        "status": (
            "synthetic_execution_extension_passed_provider_data_still_blocked"
            if all_control and rejected == len(attacks)
            else "synthetic_execution_extension_validation_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "official_document_evidence": {
            "distribution_ex_and_pay_dates_are_distinct_fields": True,
            "ciz_daily_return_includes_delisting_return": True,
            "sources": [
                {
                    "label": "CRSP SIZ-to-CIZ cross-reference guide",
                    "url": (
                        "https://www.crsp.org/crsp_pdf/"
                        "crsp-us-stock-indexes-databases-siz-to-ciz-cross-reference-guide/"
                    ),
                },
                {
                    "label": "CRSP US Stock Databases Guide for Flat File Format 2.0",
                    "url": (
                        "https://www.crsp.org/crsp_pdf/"
                        "crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/"
                    ),
                },
                {
                    "label": "WRDS Run an Event Study (CIZ Format)",
                    "url": (
                        "https://wrds-www.wharton.upenn.edu/pages/wrds-research/"
                        "macros/run-an-event-study-ciz-format-macro/"
                    ),
                },
            ],
        },
        "control": control_result,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attacks),
            "all_rejected": rejected == len(attacks),
        },
        "attacks": attacks,
        "round14_execution_accounting": {
            "gates": round14["gate_summary"],
            "attacks": round14["attack_summary"],
        },
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "authorized_provider_sample_received": False,
        "formal_stock_backtest_authorized": False,
        "formal_stock_backtest_completed": False,
        "strategy_rule_changed": False,
        "synthetic_rows_only": True,
        "transform_result": transform_result,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "只向合法數據擁有人索取同一 schema 的細樣本；真實 1/20 未提升前不得運行正式策略。"
        ),
        "disclaimer": (
            "16/16 合成控制及攻擊只證明 execution extension 會 fail closed；"
            "不代表供應商數據、正式回測、Paper 或盈利通過。"
        ),
    }
