from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from usfddk.data import fetch_yfinance, panel_fingerprint, save_snapshot, validate_panel

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/SHORT_TERM_SECTOR_ETF_PROTOCOL.md"
MAPPING = ROOT / "docs/SHORT_TERM_SECTOR_ETF_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "short_term_sector_etf_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "short_term_sector_etf_data_receipt.json"

PROTOCOL_SHA256 = "3affdc24f39353a6eb606075f802ffe6252cac01be57b13b9d098114a502a80d"
MAPPING_SHA256 = "c42743ed3d884c818dd3632d20db9f80d225ea1ccf361ea2a1ed1c1a76457a67"
PROTOCOL_COMMIT = "543259105c7c426aa15436b7f15a33dd2ffff620"
SNAPSHOT_START = "2004-09-23"
SNAPSHOT_END = "2026-07-31"
FORMAL_START = "2006-08-01"
TICKERS = (
    "QQQ",
    "SHY",
    "SPY",
    "VAW",
    "VCR",
    "VDC",
    "VDE",
    "VFH",
    "VGT",
    "VHT",
    "VIS",
    "VOX",
    "VPU",
    "VTI",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if _sha256(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError("短線行業 ETF 協議已在首次下載前改變")
    if _sha256(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("短線行業 ETF 產品映射已在首次下載前改變")
    if receipt.get("status") != (
        "frozen_before_first_vanguard_sector_daily_download_or_calculation"
    ):
        raise RuntimeError("短線行業 ETF 凍結收據狀態不符")
    if receipt["protocol"]["sha256"] != PROTOCOL_SHA256:
        raise RuntimeError("短線行業 ETF 協議收據雜湊不符")
    if receipt["product_mapping"]["sha256"] != MAPPING_SHA256:
        raise RuntimeError("短線行業 ETF 映射收據雜湊不符")
    existing = list(ARTIFACTS.glob("snapshot_short_term_sector_vanguard_*.zip"))
    if existing or DATA_RECEIPT.exists():
        raise RuntimeError(f"拒絕重複下載短線 Vanguard 行業路徑：{existing}")

    panel = fetch_yfinance(
        TICKERS,
        SNAPSHOT_START,
        SNAPSHOT_END,
        threads=False,
    )
    contract = validate_panel(
        panel,
        as_of=SNAPSHOT_END,
        required=TICKERS,
        min_last_coverage=1.0,
        min_history_coverage=0.995,
        require_fresh=False,
    )
    fingerprint = panel_fingerprint(panel)
    snapshot = ARTIFACTS / (
        "snapshot_short_term_sector_vanguard_"
        f"20040923_20260731_{fingerprint[:8]}.zip"
    )
    manifest = save_snapshot(panel, snapshot, contract=contract)

    formal = panel.close.loc[FORMAL_START:SNAPSHOT_END]
    formal_missing_by_field = {
        field: int(frame.loc[FORMAL_START:SNAPSHOT_END].isna().sum().sum())
        for field, frame in panel.field_map().items()
    }
    max_adjusted_moves = {
        ticker: float(panel.close[ticker].pct_change(fill_method=None).abs().max())
        for ticker in TICKERS
    }
    snapshot_mtime = int(snapshot.stat().st_mtime)
    frozen_mtime = max(
        int(receipt["protocol"]["mtime_epoch"]),
        int(receipt["product_mapping"]["mtime_epoch"]),
    )
    checks = {
        "contract_ok": contract.ok,
        "snapshot_created_after_freeze": snapshot_mtime > frozen_mtime,
        "formal_period_all_ohlcv_complete": not any(
            formal_missing_by_field.values()
        ),
        "formal_period_has_at_least_5000_sessions": len(formal) >= 5_000,
        "latest_all_positive_volume": bool((panel.volume.iloc[-1] > 0).all()),
        "maximum_adjusted_daily_move_not_above_65pct": max(
            max_adjusted_moves.values()
        )
        <= 0.65,
        "first_joint_download_only": True,
    }
    payload = {
        "status": (
            "short_term_sector_etf_first_external_download_contract_passed"
            if all(checks.values())
            else "short_term_sector_etf_first_external_download_contract_failed"
        ),
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_order_proved": snapshot_mtime > frozen_mtime,
        "protocol": {
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "mtime_epoch": int(receipt["protocol"]["mtime_epoch"]),
        },
        "product_mapping": {
            "sha256": MAPPING_SHA256,
            "mtime_epoch": int(receipt["product_mapping"]["mtime_epoch"]),
        },
        "snapshot": {
            "path": str(snapshot.relative_to(ROOT)),
            "mtime_epoch": snapshot_mtime,
            "archive_sha256": _sha256(snapshot),
            "panel_sha256": manifest["panel_sha256"],
            "start": manifest["start"],
            "end": manifest["end"],
            "rows": manifest["rows"],
            "tickers": manifest["tickers"],
            "contract": manifest["contract"],
        },
        "formal_period": {
            "start": FORMAL_START,
            "end": SNAPSHOT_END,
            "sessions": int(len(formal)),
            "missing_cells_by_field": formal_missing_by_field,
        },
        "maximum_absolute_adjusted_daily_move": max_adjusted_moves,
        "checks": checks,
        "download_performed_once": True,
        "calculation_started": False,
    }
    _write_json(DATA_RECEIPT, payload)
    if not all(checks.values()):
        raise RuntimeError(
            "短線行業 ETF 首次外部數據契約失敗；已保留快照及收據，拒絕重下載"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
