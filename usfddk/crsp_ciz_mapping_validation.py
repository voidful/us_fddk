from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .crsp_ciz_adapter import (
    CIZ_ADAPTER_VERSION,
    CIZ_PROTOCOL_SHA256,
    CIZ_REQUIRED_COLUMNS,
    CizMappingError,
    transform_crsp_ciz_bundle,
)
from .point_in_time_ledger import PointInTimeRequirements, audit_point_in_time_bundle

CONTROL_REQUIREMENTS = PointInTimeRequirements(
    start="2026-07-29",
    end="2026-07-31",
    min_daily_members=2,
    max_daily_members=2,
    min_member_price_coverage=1.0,
)
EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}


@dataclass(frozen=True)
class MappingAttack:
    attack_id: str
    label: str
    expected_error_code: str
    mutate: Callable[[Path], None]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame(name: str, rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=CIZ_REQUIRED_COLUMNS[name])


def _security_rows() -> list[dict[str, object]]:
    common = {
        "PrimaryExch": "N",
        "ShareClass": "NONE",
        "USIncFlg": "Y",
        "IssuerType": "CORP",
        "SecurityType": "EQTY",
        "SecuritySubType": "COM",
        "ShareType": "NS",
        "SICCD": "3571",
        "NAICS": "334111",
        "TradingStatusFlg": "A",
    }
    return [
        {
            **common,
            "PERMNO": "10001",
            "PERMCO": "5001",
            "SecInfoStartDt": "2020-01-01",
            "SecInfoEndDt": "2026-07-30",
            "Ticker": "AAA",
            "CUSIP": "000000101",
            "SecurityActiveFlg": "N",
            "ICBIndustry": "45",
        },
        {
            **common,
            "PERMNO": "10002",
            "PERMCO": "5002",
            "SecInfoStartDt": "2020-01-01",
            "SecInfoEndDt": "2025-12-31",
            "Ticker": "BBX",
            "CUSIP": "000000102",
            "SecurityActiveFlg": "N",
            "ICBIndustry": "40",
        },
        {
            **common,
            "PERMNO": "10002",
            "PERMCO": "5002",
            "SecInfoStartDt": "2026-01-01",
            "SecInfoEndDt": "2026-07-31",
            "Ticker": "BBB",
            "CUSIP": "000000202",
            "SecurityActiveFlg": "Y",
            "ICBIndustry": "45",
        },
        {
            **common,
            "PERMNO": "10003",
            "PERMCO": "5003",
            "SecInfoStartDt": "2020-01-01",
            "SecInfoEndDt": "2026-07-31",
            "Ticker": "CCC",
            "CUSIP": "000000103",
            "SecurityActiveFlg": "Y",
            "ICBIndustry": "35",
        },
    ]


def _daily_row(
    permno: str,
    day: str,
    price: float,
    *,
    daily_return: float = 0.005,
) -> dict[str, object]:
    return {
        "PERMNO": permno,
        "DlyCalDt": day,
        "DlyOpen": price,
        "DlyHigh": price + 1,
        "DlyLow": price - 1,
        "DlyClose": price + 0.5,
        "DlyVol": 1_000_000,
        "DlyRet": daily_return,
        "DlyRetMissFlg": "NA",
        "DlyOrdDivAmt": 0,
        "DlynonOrdDivAmt": 0,
        "DlyFacPrc": 1,
        "DlyDelFlg": "N",
        "TradingStatusFlg": "A",
    }


def _control_tables() -> dict[str, pd.DataFrame]:
    memberships = [
        {
            "PERMNO": "10001",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-29",
            "MbrEndDt": "2026-07-30",
            "MbrFlg": "Y",
        },
        {
            "PERMNO": "10002",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-29",
            "MbrEndDt": "2026-07-31",
            "MbrFlg": "Y",
        },
        {
            "PERMNO": "10003",
            "INDNO": "1000500",
            "MbrStartDt": "2026-07-31",
            "MbrEndDt": "2026-07-31",
            "MbrFlg": "Y",
        },
    ]
    daily_rows = [
        _daily_row("10001", "2026-07-29", 100),
        _daily_row("10001", "2026-07-30", 101),
        {
            "PERMNO": "10001",
            "DlyCalDt": "2026-07-31",
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
        },
        _daily_row("10002", "2026-07-29", 200),
        _daily_row("10002", "2026-07-30", 201),
        _daily_row("10002", "2026-07-31", 202),
        _daily_row("10003", "2026-07-31", 300),
    ]
    return {
        "stk_security_info_hist.csv": _frame(
            "stk_security_info_hist.csv", _security_rows()
        ),
        "stk_ind_membership.csv": _frame("stk_ind_membership.csv", memberships),
        "stk_dly_security_data.csv": _frame(
            "stk_dly_security_data.csv", daily_rows
        ),
        "stk_distributions.csv": _frame("stk_distributions.csv", []),
        "stk_delists.csv": _frame(
            "stk_delists.csv",
            [
                {
                    "PERMNO": "10001",
                    "DelistingDt": "2026-07-30",
                    "DelDlyDt": "2026-07-31",
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
        "security_info_availability.csv": _frame(
            "security_info_availability.csv",
            [
                {
                    "PERMNO": row["PERMNO"],
                    "SecInfoStartDt": row["SecInfoStartDt"],
                    "SecInfoEndDt": row["SecInfoEndDt"],
                    "KnownAt": "2019-12-31T20:00:00Z"
                    if row["SecInfoStartDt"] == "2020-01-01"
                    else "2025-12-31T20:00:00Z",
                    "EvidenceReference": (
                        f"synthetic-secinfo-{row['PERMNO']}-{row['SecInfoStartDt']}"
                    ),
                }
                for row in _security_rows()
            ],
        ),
        "membership_announcements.csv": _frame(
            "membership_announcements.csv",
            [
                {
                    "PERMNO": row["PERMNO"],
                    "INDNO": row["INDNO"],
                    "MbrStartDt": row["MbrStartDt"],
                    "MbrEndDt": row["MbrEndDt"],
                    "AnnouncedAt": "2026-07-28T20:00:00Z"
                    if row["MbrStartDt"] == "2026-07-29"
                    else "2026-07-30T20:00:00Z",
                    "EvidenceReference": f"synthetic-mbr-{row['PERMNO']}",
                }
                for row in memberships
            ],
        ),
        "corporate_action_overlay.csv": _frame(
            "corporate_action_overlay.csv",
            [
                {
                    "SourceTable": "StkDelists",
                    "PERMNO": "10001",
                    "EventDate": "2026-07-30",
                    "Sequence": "0",
                    "EventType": "delisting",
                    "AnnouncedAt": "2026-07-29T20:00:00Z",
                    "CashAmount": "",
                    "ShareRatio": "",
                    "SuccessorPERMNO": "",
                    "EvidenceReference": "synthetic-delist-announcement",
                }
            ],
        ),
        "exit_terms.csv": _frame(
            "exit_terms.csv",
            [
                {
                    "PERMNO": "10001",
                    "DelistingDt": "2026-07-30",
                    "OutcomeType": "delisted",
                    "CashConsideration": "",
                    "ShareRatio": "",
                    "SuccessorPERMNO": "",
                    "KnownAt": "2026-07-31T20:00:00Z",
                    "EvidenceReference": "synthetic-delist-terms",
                }
            ],
        ),
    }


def _write_control_bundle(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    bundle = parent / "synthetic-ciz-ff2-control"
    bundle.mkdir()
    receipts: dict[str, dict[str, object]] = {}
    for name, frame in _control_tables().items():
        path = bundle / name
        frame.to_csv(path, index=False, lineterminator="\n")
        receipts[name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    manifest = {
        "schema_version": 1,
        "source_format": "CIZ_FF2",
        "provider": "authorized-synthetic-control-only",
        "provider_product": "crsp-ciz-shape-control-no-provider-rows",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-03T21:22:00Z",
            "reference": "synthetic-control-no-provider-rows",
        },
        "exported_at": "2026-08-03T21:22:00Z",
        "first_imported_at": "2026-08-03T21:23:00Z",
        "as_of_date": "2026-07-31",
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


def _load_manifest(bundle: Path) -> dict[str, Any]:
    return json.loads((bundle / "ciz_manifest.json").read_text(encoding="utf-8"))


def _save_manifest(bundle: Path, manifest: dict[str, Any]) -> None:
    (bundle / "ciz_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    changed = mutate(frame)
    if changed is not None:
        frame = changed
    frame.to_csv(path, index=False, lineterminator="\n")
    manifest = _load_manifest(bundle)
    manifest["files"][name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    _save_manifest(bundle, manifest)


def _attacks() -> tuple[MappingAttack, ...]:
    def missing_membership_file(bundle: Path) -> None:
        (bundle / "membership_announcements.csv").unlink()

    def effective_date_as_announcement(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[0, "AnnouncedAt"] = "2026-07-29T00:00:00-04:00"

        _mutate_table(bundle, "membership_announcements.csv", mutate)

    def missing_security_availability(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> pd.DataFrame:
            return frame.iloc[1:].reset_index(drop=True)

        _mutate_table(bundle, "security_info_availability.csv", mutate)

    def current_row_backfill(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            old = (frame["PERMNO"] == "10002") & (
                frame["SecInfoStartDt"] == "2020-01-01"
            )
            current = frame[(frame["PERMNO"] == "10002") & (frame["SecInfoStartDt"] == "2026-01-01")].iloc[0]
            copy_columns = [
                column
                for column in frame.columns
                if column not in {"SecInfoStartDt", "SecInfoEndDt", "SecurityActiveFlg"}
            ]
            frame.loc[old, copy_columns] = current[copy_columns].to_numpy()

        _mutate_table(bundle, "stk_security_info_hist.csv", mutate)

    def adjusted_prices(bundle: Path) -> None:
        _mutate_manifest(
            bundle, lambda manifest: manifest.update({"price_basis": "adjusted_ohlc"})
        )

    def storage_on_event_date(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            frame.loc[0, "DelDlyDt"] = frame.loc[0, "DelistingDt"]

        _mutate_table(bundle, "stk_delists.csv", mutate)

    def missing_exit_economics(bundle: Path) -> None:
        def mutate_delist(frame: pd.DataFrame) -> None:
            frame.loc[0, "DelRet"] = ""
            frame.loc[0, "DelRetMissType"] = "MP"

        _mutate_table(bundle, "stk_delists.csv", mutate_delist)

    def unknown_successor(bundle: Path) -> None:
        def mutate_delist(frame: pd.DataFrame) -> None:
            frame.loc[0, "DelRet"] = ""
            frame.loc[0, "DelRetMissType"] = "MP"

        def mutate_terms(frame: pd.DataFrame) -> None:
            frame.loc[0, "OutcomeType"] = "acquired_stock"
            frame.loc[0, "ShareRatio"] = "1"
            frame.loc[0, "SuccessorPERMNO"] = "99999"

        def mutate_overlay(frame: pd.DataFrame) -> None:
            frame.loc[0, "EventType"] = "merger_stock"
            frame.loc[0, "ShareRatio"] = "1"
            frame.loc[0, "SuccessorPERMNO"] = "99999"

        _mutate_table(bundle, "stk_delists.csv", mutate_delist)
        _mutate_table(bundle, "exit_terms.csv", mutate_terms)
        _mutate_table(bundle, "corporate_action_overlay.csv", mutate_overlay)

    def missing_license_reference(bundle: Path) -> None:
        _mutate_manifest(
            bundle,
            lambda manifest: manifest["license_attestation"].pop("reference"),
        )

    def legacy_schema(bundle: Path) -> None:
        _mutate_manifest(
            bundle, lambda manifest: manifest.update({"source_format": "SIZ_FF1"})
        )

    def distribution_without_overlay(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> pd.DataFrame:
            row = {
                "PERMNO": "10002",
                "DisExDt": "2026-07-30",
                "DisSeqnbr": "1",
                "DisType": "CD",
                "DisOrdinaryFlg": "Y",
                "DisDeclareDt": "2026-07-20",
                "DisPayDt": "2026-08-15",
                "DisDivAmt": "1",
                "DisFacPr": "1",
                "DisFacShr": "1",
                "DisPERMNO": "",
            }
            return pd.concat([frame, pd.DataFrame([row])], ignore_index=True)

        _mutate_table(bundle, "stk_distributions.csv", mutate)

    def security_known_late(bundle: Path) -> None:
        def mutate(frame: pd.DataFrame) -> None:
            row = (frame["PERMNO"] == "10002") & (
                frame["SecInfoStartDt"] == "2026-01-01"
            )
            frame.loc[row, "KnownAt"] = "2026-01-01T21:00:00-05:00"

        _mutate_table(bundle, "security_info_availability.csv", mutate)

    return (
        MappingAttack(
            "01", "缺少成分公布時間 overlay", "source_file_set_mismatch", missing_membership_file
        ),
        MappingAttack(
            "02",
            "用 MbrStartDt 午夜冒充 announced_at",
            "membership_effective_date_substitution",
            effective_date_as_announcement,
        ),
        MappingAttack(
            "03",
            "security info 缺 availability 對數",
            "security_info_availability_missing",
            missing_security_availability,
        ),
        MappingAttack(
            "04",
            "以現時 security info 整列倒填歷史",
            "current_security_info_backfill",
            current_row_backfill,
        ),
        MappingAttack(
            "05", "把 adjusted OHLC 當 raw", "adjusted_price_prohibited", adjusted_prices
        ),
        MappingAttack(
            "06",
            "把 DelDlyDt 放在 DelistingDt 同日",
            "delist_storage_date_invalid",
            storage_on_event_date,
        ),
        MappingAttack(
            "07",
            "DelRet 缺失且沒有現金／換股代價",
            "missing_exit_economics",
            missing_exit_economics,
        ),
        MappingAttack(
            "08", "換股 successor PERMNO 不在 master", "unknown_successor_permno", unknown_successor
        ),
        MappingAttack(
            "09", "授權聲明缺 reference", "license_attestation_invalid", missing_license_reference
        ),
        MappingAttack("10", "legacy SIZ／schema 漂移", "source_schema_drift", legacy_schema),
        MappingAttack(
            "11",
            "distribution 缺 announcement／事件 overlay",
            "distribution_overlay_missing",
            distribution_without_overlay,
        ),
        MappingAttack(
            "12", "security info 在生效後才可知", "security_info_known_late", security_known_late
        ),
    )


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt = json.loads(
        (root / "artifacts/short_term_crsp_ciz_mapping_protocol_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    tracked = {
        key: receipt[key]
        for key in (
            "protocol",
            "point_in_time_contract",
            "manifest_schema",
            "strategy_protocol",
            "sample_acceptance_protocol",
        )
    }
    hash_checks = {
        key: _sha256_file(root / item["path"]) == item["sha256"]
        for key, item in tracked.items()
    }
    passed = bool(
        receipt["status"] == "frozen_before_ciz_adapter_implementation"
        and receipt["frozen_attack_count"] == 12
        and receipt["ciz_adapter_implemented_at_freeze"] is False
        and receipt["authorized_provider_sample_present_at_freeze"] is False
        and receipt["protocol"]["sha256"] == CIZ_PROTOCOL_SHA256
        and all(hash_checks.values())
    )
    return {
        "passed": passed,
        "frozen_at": receipt["frozen_at"],
        "hash_checks": hash_checks,
    }


def run_crsp_ciz_mapping_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol = _protocol_integrity(root_path)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用第十三輪結論")

    with tempfile.TemporaryDirectory(prefix="usfddk-round13-ciz-") as temporary:
        temporary_root = Path(temporary)
        control_source = _write_control_bundle(temporary_root / "control-source")
        control_output = temporary_root / "control-ledger"
        mapping = transform_crsp_ciz_bundle(
            control_source, control_output, root=root_path
        )
        control_audit = audit_point_in_time_bundle(
            control_output,
            root=root_path,
            requirements=CONTROL_REQUIREMENTS,
        )

        attack_results: list[dict[str, Any]] = []
        for attack in _attacks():
            attack_source = _write_control_bundle(
                temporary_root / f"attack-{attack.attack_id}-source"
            )
            attack.mutate(attack_source)
            error_code: str | None = None
            downstream_gate_summary: dict[str, Any] | None = None
            try:
                attack_output = temporary_root / f"attack-{attack.attack_id}-ledger"
                transform_crsp_ciz_bundle(
                    attack_source, attack_output, root=root_path
                )
                downstream = audit_point_in_time_bundle(
                    attack_output,
                    root=root_path,
                    requirements=CONTROL_REQUIREMENTS,
                )
                downstream_gate_summary = downstream["gate_summary"]
                if not downstream["gate_summary"]["all_passed"]:
                    error_code = "downstream_ledger_rejected"
            except CizMappingError as exc:
                error_code = exc.code
            rejected = error_code == attack.expected_error_code
            attack_results.append(
                {
                    "id": attack.attack_id,
                    "label": attack.label,
                    "expected_error_code": attack.expected_error_code,
                    "observed_error_code": error_code,
                    "rejected": rejected,
                    "downstream_gate_summary": downstream_gate_summary,
                }
            )

    control_passed = bool(
        mapping["status"] == "ciz_mapping_completed_ledger_audit_required"
        and control_audit["gate_summary"]
        == {"passed": 20, "total": 20, "all_passed": True}
        and mapping["announcement_timestamps_inferred"] is False
        and mapping["adjusted_prices_used_as_raw"] is False
        and mapping["missing_delisting_returns_imputed"] is False
        and mapping["delisting_storage_dates_used_as_exit_dates"] is False
    )
    rejected = sum(int(attack["rejected"]) for attack in attack_results)
    suite_passed = bool(protocol["passed"] and control_passed and rejected == 12)
    return {
        "schema_version": 1,
        "research_round": 13,
        "status": (
            "ciz_mapping_bridge_passed_provider_data_still_blocked"
            if suite_passed
            else "ciz_mapping_bridge_incomplete_or_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "protocol_integrity": protocol,
        "official_document_evidence": {
            "current_format": "CIZ Flat File Format 2.0; legacy SIZ discontinued after December 2024 release",
            "direct_fields_verified": [
                "PERMNO",
                "PERMCO",
                "SecInfoStartDt/SecInfoEndDt",
                "Ticker/PrimaryExch/CUSIP",
                "DlyOpen/DlyHigh/DlyLow/DlyClose/DlyVol/DlyRet",
                "MbrStartDt/MbrEndDt",
                "DelistingDt/DelDlyDt/DelRet/DelRetMissType",
            ],
            "not_verified_in_public_table_definition": [
                "membership announcement timestamp",
                "security-info availability timestamp",
                "exact authorized WRDS export schema",
                "fixed-period missing delisting-return rate",
            ],
            "sources": [
                {
                    "label": "WRDS Changes to CRSP Data",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/",
                },
                {
                    "label": "WRDS CRSP CIZtoSIZ macro",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/",
                },
                {
                    "label": "CRSP US Stock Databases Guide for Flat File Format 2.0",
                    "url": "https://index-website-frontend-prd.mif0286.eas.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true",
                },
            ],
        },
        "mapping_policy": {
            "direct": [
                "PERMNO/PERMCO",
                "historical security identifiers",
                "raw daily OHLCV",
                "membership effective ranges",
                "DelistingDt and DelRet",
            ],
            "deterministic_derived": [
                "inclusive source end to half-open ledger end",
                "1 + DlyRet total-return factor",
                "CRSP permanent-ID prefixes",
            ],
            "external_evidence_required": [
                "membership announced_at",
                "security-info known_at",
                "corporate-action announced_at and normalized terms",
                "cash/stock exit terms when DelRet is missing",
            ],
            "prohibited_inference": [
                "MbrStartDt as announcement time",
                "SecInfoStartDt as known_at",
                "current ticker/classification backfill",
                "adjusted OHLC as raw",
                "missing DelRet as zero",
                "DelDlyDt as exit event date",
            ],
        },
        "control": {
            "synthetic_only": True,
            "contains_provider_rows": False,
            "mapping_completed": mapping[
                "status"
            ]
            == "ciz_mapping_completed_ledger_audit_required",
            "ledger_gate_summary": control_audit["gate_summary"],
            "paper_authorized": False,
        },
        "attacks": attack_results,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attack_results),
            "all_rejected": rejected == len(attack_results),
        },
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "actual_provider_bundle_present": readiness["bundle"]["configured"],
        "authorized_provider_sample_received": False,
        "wrds_catalog_queried": False,
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
        "next_action": "只接受合法 CIZ 小樣本加四類 evidence overlay；先逐欄通過 adapter 與 20 道賬本稽核，再考慮固定 20 年正式匯出。",
        "disclaimer": "本輪只證明合成 CIZ 形狀的轉換及拒收規則；不證明 CRSP／WRDS 已授權或策略可盈利，不構成投資建議。",
    }
