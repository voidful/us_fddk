from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from usfddk.data import fetch_yfinance, panel_fingerprint, save_snapshot, validate_panel

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/V25_GROWTH_GOLD_DIVERSIFICATION_PROTOCOL.md"
MAPPING = ROOT / "docs/V25_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "v25_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "v25_data_receipt.json"
PROTOCOL_SHA256 = "e4cc652e7f9d7c296282aa71459abfbe58e8b945f7cafa8830a332812dd5c2db"
MAPPING_SHA256 = "6d82088fdbfb848329805a053071460cd8ca37a1954754ef5390485043ec37a9"

PATHS = {
    "vanguard": ["GLD", "SHY", "SPY", "VUG"],
    "ishares": ["IAU", "IWF", "SHY", "SPY"],
    "state_street": ["GLD", "SHY", "SPY", "SPYG"],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(label: str, tickers: list[str]) -> tuple[Path, dict, dict[str, float]]:
    existing = list(ARTIFACTS.glob(f"snapshot_v25_{label}_*.zip"))
    if existing:
        raise RuntimeError(f"拒絕重複下載 v25 {label}：{existing}")
    panel = fetch_yfinance(tickers, "2006-07-01", "2026-07-31", threads=False)
    contract = validate_panel(
        panel,
        as_of="2026-07-31",
        required=tuple(tickers),
        min_history_coverage=0.999,
        require_fresh=False,
    )
    contract.require()
    max_adjusted_moves = {
        ticker: float(panel.close[ticker].pct_change(fill_method=None).abs().max())
        for ticker in tickers
    }
    if max(max_adjusted_moves.values()) > 0.65:
        raise RuntimeError(f"v25 {label} 仍有疑似未處理公司行動：{max_adjusted_moves}")
    fingerprint = panel_fingerprint(panel)
    path = ARTIFACTS / (
        f"snapshot_v25_{label}_20060701_20260731_{fingerprint[:8]}.zip"
    )
    manifest = save_snapshot(panel, path, contract=contract)
    return path, manifest, max_adjusted_moves


def main() -> int:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if _sha256(PROTOCOL) != PROTOCOL_SHA256 or _sha256(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("v25 凍結協議或產品映射已改變")
    if protocol.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("v25 協議收據不符")
    frozen_mtime = max(
        int(protocol["protocol_mtime_epoch"]),
        int(protocol["product_mapping_mtime_epoch"]),
    )

    snapshots: dict[str, object] = {}
    for label, tickers in PATHS.items():
        path, manifest, max_moves = _snapshot(label, tickers)
        if path.stat().st_mtime <= frozen_mtime:
            raise RuntimeError(f"v25 {label} 快照沒有晚於凍結")
        snapshots[label] = {
            "path": str(path.relative_to(ROOT)),
            "snapshot_mtime_epoch": int(path.stat().st_mtime),
            "panel_sha256": manifest["panel_sha256"],
            "archive_sha256": _sha256(path),
            "rows": manifest["rows"],
            "start": manifest["start"],
            "end": manifest["end"],
            "tickers": manifest["tickers"],
            "contract": manifest["contract"],
            "max_absolute_adjusted_daily_move": max_moves,
            "performed_once": True,
        }

    vanguard = snapshots["vanguard"]
    assert isinstance(vanguard, dict)
    vug_move = float(vanguard["max_absolute_adjusted_daily_move"]["VUG"])
    payload = {
        "status": "v25_first_joint_product_downloads_contract_passed",
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_order_proved": True,
        "protocol": {
            "sha256": PROTOCOL_SHA256,
            "mtime_epoch": int(protocol["protocol_mtime_epoch"]),
        },
        "product_mapping": {
            "sha256": MAPPING_SHA256,
            "mtime_epoch": int(protocol["product_mapping_mtime_epoch"]),
        },
        "snapshots": snapshots,
        "vug_split_adjustment_audit": {
            "official_split_ratio": "6:1",
            "official_effective_date": "2026-04-21",
            "unadjusted_split_drop_threshold": 0.80,
            "maximum_absolute_adjusted_daily_move": vug_move,
            "passed": vug_move < 0.65,
        },
    }
    DATA_RECEIPT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
