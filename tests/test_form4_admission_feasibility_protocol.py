from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md"
RECEIPT = ROOT / "artifacts/short_term_form4_admission_feasibility_protocol_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed.astimezone(UTC)


def _load_receipt() -> dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


_RAW_DATE = re.compile(r"^(\d{2})-([A-Z]{3})-(\d{4})$")


def _normalize_date(raw: str, month_tokens: list[str]) -> str:
    match = _RAW_DATE.fullmatch(raw)
    assert match is not None
    day, month_token, year = match.groups()
    assert month_token in month_tokens
    return date(int(year), month_tokens.index(month_token) + 1, int(day)).isoformat()


def _select(
    rows: list[dict[str, str]], selector: dict[str, Any], month_tokens: list[str]
) -> tuple[list[str], bool]:
    allowed = set(selector["allowed_document_types"])
    eligible = [row for row in rows if row["DOCUMENT_TYPE"] in allowed]
    keyed = [
        (
            _normalize_date(row["FILING_DATE"], month_tokens),
            row["ACCESSION_NUMBER"],
            row,
        )
        for row in eligible
    ]
    keyed.sort(key=lambda item: (item[0], item[1]))
    assert len(keyed) >= selector["samples_per_quarter_min"]
    assert len({item[1] for item in keyed}) == len(keyed)

    n = len(keyed)
    base_indices = (0, (n - 1) // 2, n - 1)
    selected = [keyed[index][1] for index in base_indices]
    amendment_rows = [item for item in keyed if item[2]["DOCUMENT_TYPE"] == "4/A"]
    if not amendment_rows:
        raise ValueError(selector["quarter_without_4/A"])
    extra = next((item[1] for item in amendment_rows if item[1] not in selected), None)
    if extra is not None:
        selected.append(extra)
    return selected, extra is None


def _row(serial: int, filing_date: str, document_type: str) -> dict[str, str]:
    return {
        "ACCESSION_NUMBER": f"{serial:010d}-26-{serial:06d}",
        "FILING_DATE": filing_date,
        "DOCUMENT_TYPE": document_type,
    }


def test_round42_receipt_binds_frozen_parent_ledger_and_sec_client_bytes() -> None:
    receipt = _load_receipt()
    assert receipt["research_round"] == 42
    assert receipt["status"] == (
        "result_blind_protocol_frozen_before_sec_fetch_real_sample_selection_"
        "admission_replay_or_result"
    )
    for key in (
        "protocol",
        "parent_form4_v1_1_protocol",
        "parent_form4_v1_1_receipt",
        "global_trial_ledger_protocol",
        "global_trial_ledger",
    ):
        binding = receipt[key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    for key in ("implementation", "isolated_tests"):
        binding = receipt["sec_client"][key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]

    parent = json.loads(
        (ROOT / receipt["parent_form4_v1_1_receipt"]["path"]).read_text(encoding="utf-8")
    )
    protocol_text = PROTOCOL.read_text(encoding="utf-8")
    frozen_match = re.search(r"^FrozenAt：`([^`]+)`$", protocol_text, flags=re.MULTILINE)
    assert frozen_match is not None
    assert frozen_match.group(1) == receipt["frozen_at"]
    assert _utc(parent["frozen_at"]) < _utc(receipt["frozen_at"])

    ledger = json.loads(
        (ROOT / receipt["global_trial_ledger"]["path"]).read_text(encoding="utf-8")
    )
    assert receipt["global_trial_ledger"]["entry_count"] == len(ledger["entries"])
    assert receipt["global_trial_ledger"]["current_lower_bound"] == ledger["current_lower_bound"]
    assert receipt["global_trial_ledger"]["chain_head_sha256"] == ledger["chain_head_sha256"]
    assert receipt["sec_client"]["network_used_by_this_freeze"] is False


def test_round42_freezes_official_zip_schema_and_result_blind_state() -> None:
    receipt = _load_receipt()
    assert receipt["fixed_quarters"] == ["2006Q1", "2016Q3", "2026Q2"]
    zip_contract = receipt["quarterly_zip_contract"]
    assert zip_contract["metadata"] == {
        "kind": "W3C_Table_Group_JSON",
        "required_count": 1,
        "recognition": "parseable_content_and_schema_not_filename_or_extension",
        "table_url_policy": "pure_unencoded_basename_without_directory_or_traversal",
        "table_roles_unique": True,
    }
    assert set(zip_contract["required_tables"]) == {
        "SUBMISSION.tsv",
        "REPORTINGOWNER.tsv",
        "NONDERIV_TRANS.tsv",
        "NONDERIV_HOLDING.tsv",
        "DERIV_TRANS.tsv",
        "DERIV_HOLDING.tsv",
        "FOOTNOTES.tsv",
        "OWNER_SIGNATURE.tsv",
    }
    assert zip_contract["required_tables"]["OWNER_SIGNATURE.tsv"] == [
        "ACCESSION_NUMBER",
        "OWNERSIGNATURENAME",
        "OWNERSIGNATUREDATE",
    ]
    assert zip_contract["filing_date_raw_format"] == "DD-MON-YYYY"

    assert receipt["global_trial_state"] == {
        "lower_bound_before": 6_287,
        "round42_increment": 0,
        "lower_bound_after": 6_287,
        "ledger_append_authorized": False,
    }
    assert receipt["state_at_freeze"] == {
        "form4_specific_admission_passed": 0,
        "form4_specific_admission_total": 16,
        "authorized_real_form4_rows": 0,
        "real_sample_selection_count": 0,
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
    }
    assert receipt["future_admission_scoring"] == {
        "individual_gate_pass_fail_allowed_with_exact_evidence": True,
        "public_progress_denominator": 16,
        "admission_requires_passed": 16,
        "below_16_candidate_selection_count": 0,
        "below_16_strategy_run_count": 0,
        "below_16_paper_authorized": False,
    }
    assert receipt["permission"]["sec_fetch"] is False
    assert receipt["permission"]["candidate_selection"] is False
    assert receipt["permission"]["backtest"] is False
    assert receipt["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert receipt["real_money_action_usd"] == 0
    assert receipt["today_action"] == "今天不下單"

    rendered = json.dumps(receipt, sort_keys=True).lower()
    for forbidden in ("ticker", "symbol", "cagr", "sharpe", "drawdown", "pnl"):
        assert forbidden not in rendered


def test_round42_selector_is_order_invariant_and_covers_amendments() -> None:
    receipt = _load_receipt()
    selector = receipt["sample_selector"]
    months = receipt["quarterly_zip_contract"]["filing_date_month_tokens"]
    assert selector["base_positions"] == [
        {"label": "first", "zero_based_index": "0"},
        {
            "label": "median",
            "zero_based_index": "floor((n-1)/2)",
            "even_policy": "lower_median",
        },
        {"label": "last", "zero_based_index": "n-1"},
    ]

    quarter_rows = {
        "2006Q1": [
            _row(1, "03-JAN-2006", "4"),
            _row(2, "04-JAN-2006", "4/A"),
            _row(3, "05-JAN-2006", "4"),
            _row(4, "06-JAN-2006", "4"),
            _row(5, "09-JAN-2006", "4"),
        ],
        "2016Q3": [
            _row(11, "01-JUL-2016", "4/A"),
            _row(12, "05-JUL-2016", "4"),
            _row(13, "06-JUL-2016", "4"),
            _row(14, "07-JUL-2016", "4/A"),
            _row(15, "08-JUL-2016", "4"),
        ],
        "2026Q2": [
            _row(21, "01-APR-2026", "4"),
            _row(22, "02-APR-2026", "4"),
            _row(23, "06-APR-2026", "4/A"),
            _row(24, "07-APR-2026", "4"),
            _row(25, "08-APR-2026", "4"),
        ],
    }
    expected = {
        "2006Q1": [
            "0000000001-26-000001",
            "0000000003-26-000003",
            "0000000005-26-000005",
            "0000000002-26-000002",
        ],
        "2016Q3": [
            "0000000011-26-000011",
            "0000000013-26-000013",
            "0000000015-26-000015",
            "0000000014-26-000014",
        ],
        "2026Q2": [
            "0000000021-26-000021",
            "0000000023-26-000023",
            "0000000025-26-000025",
        ],
    }
    coverage_by_base = {"2006Q1": False, "2016Q3": False, "2026Q2": True}
    for quarter, rows in quarter_rows.items():
        selected, covered = _select(rows, selector, months)
        assert selected == expected[quarter]
        assert covered is coverage_by_base[quarter]
        shuffled = list(rows)
        random.Random(42).shuffle(shuffled)
        assert _select(shuffled, selector, months) == (selected, covered)

    assert sum(len(value) for value in expected.values()) == 11
    assert selector["total_sample_min"] <= 11 <= selector["total_sample_max"]


def test_round42_selector_fails_when_quarter_has_no_amendment() -> None:
    receipt = _load_receipt()
    selector = receipt["sample_selector"]
    months = receipt["quarterly_zip_contract"]["filing_date_month_tokens"]
    rows = [
        _row(31, "01-APR-2026", "4"),
        _row(32, "02-APR-2026", "4"),
        _row(33, "03-APR-2026", "4"),
    ]
    with pytest.raises(ValueError, match="form4_feasibility_amendment_sample_missing"):
        _select(rows, selector, months)


def test_round42_attack_and_stop_contract_is_closed() -> None:
    receipt = _load_receipt()
    attacks = receipt["fixed_attack_codes"]
    assert len(attacks) == 19
    assert len(set(attacks)) == len(attacks)
    assert "form4_feasibility_historical_time_invented" in attacks
    assert "form4_feasibility_amendment_target_unresolved" in attacks
    assert "form4_feasibility_result_boundary_breached" in attacks
    assert receipt["stop_policy"] == {
        "on_any_failure": "stopped_no_admission_claim",
        "quarter_substitution_allowed": False,
        "resampling_allowed": False,
        "threshold_relaxation_allowed": False,
        "observed_only_result_allowed": False,
    }
    assert receipt["archive_known_at_contract"] == {
        "required_pair": [
            "complete_daily_form_index_raw_sha256_and_unique_row",
            "complete_as_filed_submission_txt_raw_sha256",
        ],
        "index_update_boundary": "approximately_22:00_America/New_York_on_index_date",
        "accepted_at_is_known_at": False,
        "local_first_observed_is_historical_public_time": False,
        "decision_session_if_future_authorized": (
            "next_full_XNYS_session_close_after_nightly_index_boundary"
        ),
        "trade_session_if_future_authorized": (
            "XNYS_session_open_after_decision_session_close"
        ),
        "clock_mapping_executed": False,
    }
