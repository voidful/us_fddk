from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .point_in_time_ledger import (
    MANIFEST_POLICY_VALUES,
    REQUIRED_COLUMNS,
    PointInTimeRequirements,
    audit_point_in_time_bundle,
)

ROUND12_PROTOCOL_SHA256 = (
    "50d58265c36d126bcf4b315abbbc4bbf433b077d1e5a05b8d409e6a0e0c5f7a3"
)
EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}
CONTROL_REQUIREMENTS = PointInTimeRequirements(
    start="2026-07-29",
    end="2026-07-31",
    min_daily_members=2,
    max_daily_members=2,
    min_member_price_coverage=1.0,
)


@dataclass(frozen=True)
class AcceptanceAttack:
    attack_id: str
    label: str
    expected_failed_gates: tuple[str, ...]
    mutate: Callable[[Path], None]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame(name: str, rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS[name])


def _price_row(security_id: str, session: str, price: float) -> dict[str, object]:
    return {
        "security_id": security_id,
        "session": session,
        "open_raw": price,
        "high_raw": price + 1,
        "low_raw": price - 1,
        "close_raw": price + 0.5,
        "volume": 1_000_000,
        "cash_distribution": 0,
        "split_factor": 1,
        "total_return_factor": 1.005,
        "source_status": "observed",
    }


def _control_tables() -> dict[str, pd.DataFrame]:
    return {
        "security_master.csv": _frame(
            "security_master.csv",
            [
                {
                    "security_id": "SEC1",
                    "company_id": "CO1",
                    "security_type": "common_stock",
                    "share_class": "A",
                    "country_of_incorporation": "US",
                    "currency": "USD",
                },
                {
                    "security_id": "SEC2",
                    "company_id": "CO2",
                    "security_type": "common_stock",
                    "share_class": "single",
                    "country_of_incorporation": "US",
                    "currency": "USD",
                },
                {
                    "security_id": "SEC3",
                    "company_id": "CO3",
                    "security_type": "common_stock",
                    "share_class": "single",
                    "country_of_incorporation": "US",
                    "currency": "USD",
                },
            ],
        ),
        "identifier_history.csv": _frame(
            "identifier_history.csv",
            [
                {
                    "security_id": security_id,
                    "ticker": ticker,
                    "exchange": exchange,
                    "cusip": cusip,
                    "isin": "",
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "known_at": "2019-12-31T20:00:00Z",
                }
                for security_id, ticker, exchange, cusip in (
                    ("SEC1", "AAA", "XNYS", "000000001"),
                    ("SEC2", "BBB", "XNAS", "000000002"),
                    ("SEC3", "CCC", "XNYS", "000000003"),
                )
            ],
        ),
        "membership_history.csv": _frame(
            "membership_history.csv",
            [
                {
                    "index_id": "SP500",
                    "security_id": "SEC1",
                    "effective_from": "2026-07-29",
                    "effective_to": "2026-07-31",
                    "announced_at": "2026-07-28T20:00:00Z",
                    "source_record_id": "MEM1",
                },
                {
                    "index_id": "SP500",
                    "security_id": "SEC2",
                    "effective_from": "2026-07-29",
                    "effective_to": "",
                    "announced_at": "2026-07-28T20:00:00Z",
                    "source_record_id": "MEM2",
                },
                {
                    "index_id": "SP500",
                    "security_id": "SEC3",
                    "effective_from": "2026-07-31",
                    "effective_to": "",
                    "announced_at": "2026-07-30T20:00:00Z",
                    "source_record_id": "MEM3",
                },
            ],
        ),
        "trading_calendar.csv": _frame(
            "trading_calendar.csv",
            [
                {
                    "session": day,
                    "exchange": "XNYS",
                    "open_at": f"{day}T13:30:00Z",
                    "close_at": f"{day}T20:00:00Z",
                }
                for day in ("2026-07-29", "2026-07-30", "2026-07-31")
            ],
        ),
        "daily_prices.csv": _frame(
            "daily_prices.csv",
            [
                _price_row("SEC1", "2026-07-29", 100),
                _price_row("SEC1", "2026-07-30", 101),
                _price_row("SEC2", "2026-07-29", 200),
                _price_row("SEC2", "2026-07-30", 201),
                _price_row("SEC2", "2026-07-31", 202),
                _price_row("SEC3", "2026-07-31", 300),
            ],
        ),
        "corporate_actions.csv": _frame(
            "corporate_actions.csv",
            [
                {
                    "event_id": "EVENT1",
                    "security_id": "SEC1",
                    "event_type": "delisting",
                    "announced_at": "2026-07-29T20:00:00Z",
                    "ex_date": "2026-07-31",
                    "effective_date": "2026-07-31",
                    "cash_amount": 0,
                    "share_ratio": 0,
                    "successor_security_id": "",
                    "source_record_id": "ACTION1",
                }
            ],
        ),
        "classification_history.csv": _frame(
            "classification_history.csv",
            [
                {
                    "security_id": security_id,
                    "scheme": "GICS",
                    "sector_code": sector,
                    "industry_code": industry,
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "known_at": "2019-12-31T20:00:00Z",
                    "source_record_id": f"CLASS-{security_id}",
                }
                for security_id, sector, industry in (
                    ("SEC1", "45", "4510"),
                    ("SEC2", "40", "4010"),
                    ("SEC3", "35", "3510"),
                )
            ],
        ),
        "security_outcomes.csv": _frame(
            "security_outcomes.csv",
            [
                {
                    "source_record_id": "MEM1",
                    "security_id": "SEC1",
                    "membership_effective_to": "2026-07-31",
                    "outcome_type": "delisted",
                    "last_trade_date": "2026-07-30",
                    "exit_effective_date": "2026-07-31",
                    "delisting_return": -0.5,
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "DELIST_VALID_CONTROL",
                    "known_at": "2026-07-31T20:00:00Z",
                },
                {
                    "source_record_id": "MEM2",
                    "security_id": "SEC2",
                    "membership_effective_to": "",
                    "outcome_type": "still_member",
                    "last_trade_date": "",
                    "exit_effective_date": "",
                    "delisting_return": "",
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "",
                    "known_at": "2026-07-31T20:00:00Z",
                },
                {
                    "source_record_id": "MEM3",
                    "security_id": "SEC3",
                    "membership_effective_to": "",
                    "outcome_type": "still_member",
                    "last_trade_date": "",
                    "exit_effective_date": "",
                    "delisting_return": "",
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "",
                    "known_at": "2026-07-31T20:00:00Z",
                },
            ],
        ),
    }


def _write_control_bundle(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    bundle = parent / "authorized-crsp-shape-control"
    bundle.mkdir()
    receipts: dict[str, dict[str, object]] = {}
    for name, frame in _control_tables().items():
        path = bundle / name
        frame.to_csv(path, index=False, lineterminator="\n")
        receipts[name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    manifest = {
        "schema_version": 1,
        "provider": "authorized-synthetic-control-only",
        "provider_product": "crsp-shape-acceptance-control",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-03T20:39:00Z",
            "reference": "synthetic-control-no-provider-rows",
        },
        "exported_at": "2026-08-03T20:39:00Z",
        "first_imported_at": "2026-08-03T20:40:00Z",
        "as_of_date": "2026-07-31",
        "currency": "USD",
        "timezone": "America/New_York",
        **MANIFEST_POLICY_VALUES,
        "transform_version": "round12-control-v1",
        "files": receipts,
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle


def _load_manifest(bundle: Path) -> dict[str, Any]:
    return json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))


def _save_manifest(bundle: Path, manifest: dict[str, Any]) -> None:
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mutate_manifest(bundle: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    manifest = _load_manifest(bundle)
    mutate(manifest)
    _save_manifest(bundle, manifest)


def _mutate_table(
    bundle: Path,
    name: str,
    mutate: Callable[[pd.DataFrame], pd.DataFrame | None],
) -> None:
    path = bundle / name
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    changed = mutate(frame)
    if changed is not None:
        frame = changed
    frame.to_csv(path, index=False, lineterminator="\n")
    manifest = _load_manifest(bundle)
    manifest["files"][name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    _save_manifest(bundle, manifest)


def _attacks() -> tuple[AcceptanceAttack, ...]:
    def missing_license_field(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest["license_attestation"].pop(
                "raw_redistribution_allowed"
            ),
        )

    def extra_license_field(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest["license_attestation"].update(
                {"provider_claimed_complete": True}
            ),
        )

    def naive_attestation(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest["license_attestation"].update(
                {"attested_at": "2026-08-03T20:39:00"}
            ),
        )

    def export_after_import(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest.update(
                {"exported_at": "2026-08-03T20:41:00Z"}
            ),
        )

    def stale_as_of(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest.update({"as_of_date": "2026-07-30"}),
        )

    def late_identifier(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[0, "known_at"] = "2020-01-01T21:00:00-05:00"

        _mutate_table(bundle, "identifier_history.csv", mutate)

    def late_membership(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[0, "announced_at"] = "2026-07-29T21:00:00-04:00"

        _mutate_table(bundle, "membership_history.csv", mutate)

    def missing_exit_economics(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[frame["security_id"] == "SEC1", "delisting_return"] = ""

        _mutate_table(bundle, "security_outcomes.csv", mutate)

    def unknown_successor(bundle: Path) -> None:
        def mutate_outcome(frame: pd.DataFrame) -> None:
            row = frame["security_id"] == "SEC1"
            frame.loc[row, "outcome_type"] = "acquired_stock"
            frame.loc[row, "delisting_return"] = ""
            frame.loc[row, "successor_security_id"] = "SEC-MISSING"

        def mutate_action(frame: pd.DataFrame) -> None:
            frame.loc[0, "event_type"] = "merger_stock"
            frame.loc[0, "share_ratio"] = "1"
            frame.loc[0, "successor_security_id"] = "SEC-MISSING"

        _mutate_table(bundle, "security_outcomes.csv", mutate_outcome)
        _mutate_table(bundle, "corporate_actions.csv", mutate_action)

    def contradictory_still_member(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            row = frame["security_id"] == "SEC2"
            frame.loc[row, "exit_effective_date"] = "2026-07-31"
            frame.loc[row, "delisting_return"] = "0"

        _mutate_table(bundle, "security_outcomes.csv", mutate)

    def mismatched_exit_date(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[frame["security_id"] == "SEC1", "exit_effective_date"] = (
                "2026-07-30"
            )

        _mutate_table(bundle, "security_outcomes.csv", mutate)

    def ghost_price(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> pd.DataFrame:
            return pd.concat(
                [frame, pd.DataFrame([_price_row("SEC1", "2026-07-31", 102)])],
                ignore_index=True,
            )

        _mutate_table(bundle, "daily_prices.csv", mutate)

    return (
        AcceptanceAttack("01", "授權聲明缺必要欄位", ("02_manifest_and_file_set",), missing_license_field),
        AcceptanceAttack("02", "授權聲明含未授權欄位", ("02_manifest_and_file_set",), extra_license_field),
        AcceptanceAttack(
            "03",
            "授權時間沒有 UTC offset",
            ("01_authorized_provider", "02_manifest_and_file_set"),
            naive_attestation,
        ),
        AcceptanceAttack("04", "匯出時間晚於首次匯入", ("02_manifest_and_file_set",), export_after_import),
        AcceptanceAttack("05", "數據截至日早於固定終點", ("09_fixed_20_year_calendar",), stale_as_of),
        AcceptanceAttack("06", "歷史代號在生效後才可知", ("06_identifier_history",), late_identifier),
        AcceptanceAttack("07", "指數成分在生效後才公布", ("07_membership_availability",), late_membership),
        AcceptanceAttack("08", "退市回報及代價全部缺失", ("16_permanent_exit_economics",), missing_exit_economics),
        AcceptanceAttack(
            "09",
            "換股 successor 不在永久主檔",
            ("14_corporate_actions", "16_permanent_exit_economics"),
            unknown_successor,
        ),
        AcceptanceAttack("10", "仍在籍結果混入退出欄位", ("16_permanent_exit_economics",), contradictory_still_member),
        AcceptanceAttack("11", "退出日與成分終止日不一致", ("16_permanent_exit_economics",), mismatched_exit_date),
        AcceptanceAttack("12", "最後交易日後仍有行情", ("17_no_post_exit_prices",), ghost_price),
    )


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt_path = root / "artifacts/short_term_crsp_sample_acceptance_protocol_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    files = {
        "protocol": receipt["protocol"],
        "point_in_time_contract": receipt["point_in_time_contract"],
        "manifest_schema": receipt["manifest_schema"],
        "strategy_protocol": receipt["strategy_protocol"],
    }
    checks = {
        key: _sha256_file(root / item["path"]) == item["sha256"]
        for key, item in files.items()
    }
    passed = bool(
        receipt["status"] == "frozen_before_acceptance_harness_implementation"
        and receipt["frozen_attack_count"] == 12
        and receipt["acceptance_harness_implemented_at_freeze"] is False
        and receipt["authorized_provider_sample_present_at_freeze"] is False
        and receipt["strategy_rule_changed"] is False
        and receipt["protocol"]["sha256"] == ROUND12_PROTOCOL_SHA256
        and all(checks.values())
    )
    return {"passed": passed, "hash_checks": checks, "frozen_at": receipt["frozen_at"]}


def _sample_request() -> dict[str, Any]:
    return {
        "purpose": "只驗證 schema、時間語義、缺值及授權；不購買、不回測、不公開原始列",
        "official_product_path": "CRSP US Stock and Indexes plus Historical Indexes via an authorized WRDS or flat-file subscription",
        "required_provider_answers": [
            "S&P 500 membership 的 start/end 是生效日還是數據庫可用日",
            "能否逐次提供 announcement timestamp；不能時須明示不可重建",
            "2006-08-01 至 2026-07-31 的 DelRetMissType 數量、比例及原因分布",
            "缺失 DelRet 能否由 DelAmt、DelDivAmt、successor PERMNO/PERMCO 或完整付款重建",
            "本地研究、衍生匯總、SHA-256 收據及禁止原始列再分發的授權邊界",
        ],
        "requested_table_shapes": [
            {
                "official_area": "security and issuer history",
                "minimum_fields": [
                    "PERMNO",
                    "PERMCO",
                    "historical ticker/trading symbol",
                    "CUSIP",
                    "primary exchange",
                    "share/security type",
                    "effective start/end",
                    "SIC/NAICS/ICB or equivalent historical industry",
                ],
            },
            {
                "official_area": "StkIndMembership and S&P 500 history",
                "minimum_fields": [
                    "PERMNO",
                    "index identifier",
                    "MbrStartDt",
                    "MbrEndDt",
                    "announcement or availability timestamp",
                ],
            },
            {
                "official_area": "StkDlySecurityData",
                "minimum_fields": [
                    "DlyCalDt",
                    "DlyOpen/DlyHigh/DlyLow/DlyClose",
                    "DlyVolume",
                    "daily total return and missing flag",
                    "daily delisting flag",
                    "ordinary/non-ordinary distribution amount",
                ],
            },
            {
                "official_area": "distributions and delists",
                "minimum_fields": [
                    "announcement/ex/effective/payment dates",
                    "cash and share factors",
                    "DelRet",
                    "DelRetMissType",
                    "delisting amount/dividend",
                    "successor PERMNO/PERMCO",
                    "delisting reason/payment type",
                ],
            },
        ],
        "required_edge_cases": [
            "代號或交易所變更",
            "同公司多股份類別",
            "S&P 500 加入及移除",
            "有效退市回報",
            "缺失退市回報",
            "現金收購",
            "換股收購",
            "停牌",
            "拆股及現金派息",
            "歷史分類變更",
        ],
        "formal_coverage_unchanged": {
            "start": "2006-08-01",
            "end": "2026-07-31",
            "minimum_member_price_coverage": 0.995,
            "required_daily_member_range": [495, 510],
            "all_twenty_gates_required": True,
        },
    }


def run_crsp_sample_acceptance_rehearsal(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol = _protocol_integrity(root_path)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用第十二輪結論")

    with tempfile.TemporaryDirectory(prefix="usfddk-crsp-acceptance-") as temp:
        temp_root = Path(temp)
        control = _write_control_bundle(temp_root / "control")
        control_result = audit_point_in_time_bundle(
            control,
            root=root_path,
            requirements=CONTROL_REQUIREMENTS,
        )
        attack_results: list[dict[str, Any]] = []
        for attack in _attacks():
            attack_root = temp_root / f"attack-{attack.attack_id}"
            bundle = _write_control_bundle(attack_root)
            attack.mutate(bundle)
            result = audit_point_in_time_bundle(
                bundle,
                root=root_path,
                requirements=CONTROL_REQUIREMENTS,
            )
            designated = {
                gate: result["gates"][gate]["passed"]
                for gate in attack.expected_failed_gates
            }
            rejected = bool(
                not result["gate_summary"]["all_passed"]
                and all(value is False for value in designated.values())
            )
            attack_results.append(
                {
                    "id": attack.attack_id,
                    "label": attack.label,
                    "expected_failed_gates": list(attack.expected_failed_gates),
                    "designated_gate_pass_values": designated,
                    "rejected": rejected,
                    "overall_gate_count": result["gate_summary"],
                }
            )

    control_passed = control_result["gate_summary"] == {
        "passed": 20,
        "total": 20,
        "all_passed": True,
    }
    rejected_count = sum(int(item["rejected"]) for item in attack_results)
    harness_passed = bool(protocol["passed"] and control_passed and rejected_count == 12)
    return {
        "schema_version": 1,
        "research_round": 12,
        "status": (
            "acceptance_harness_passed_provider_data_still_blocked"
            if harness_passed
            else "acceptance_harness_incomplete_or_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "protocol_integrity": protocol,
        "control": {
            "synthetic_only": True,
            "contains_provider_rows": False,
            "gate_summary": control_result["gate_summary"],
            "formal_backtest_authorized_for_control_only": control_result[
                "formal_backtest_authorized"
            ],
            "paper_authorized": control_result["paper"]["authorized"],
        },
        "attacks": attack_results,
        "attack_summary": {
            "rejected": rejected_count,
            "total": len(attack_results),
            "all_rejected": rejected_count == len(attack_results),
        },
        "sample_request": _sample_request(),
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "actual_provider_bundle_present": readiness["bundle"]["configured"],
        "wrds_catalog_queried": False,
        "authorized_provider_sample_received": False,
        "provider_qualified": False,
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
        "next_action": "把凍結最小樣本要求交給 CRSP／WRDS；只有合法樣本通過同一驗收及正式 20/20 後，才可運行一次凍結 v1 回測。",
        "disclaimer": "12/12 只證明合成攻擊被拒絕，不證明 CRSP／WRDS 已合格，不構成投資建議或盈利保證。",
    }
