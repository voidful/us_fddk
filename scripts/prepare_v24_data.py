from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from usfddk.data import fetch_yfinance, panel_fingerprint, save_snapshot, validate_panel

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/V24_QUALITY_MOMENTUM_FACTOR_PROTOCOL.md"
MAPPING = ROOT / "docs/V24_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "v24_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "v24_data_receipt.json"
PROTOCOL_SHA256 = "0d35082a8c7d07a247966a85906158e57f0126c195b355f1d79a2f084e8fb147"
MAPPING_SHA256 = "70e0f6c6336a56e13e339f7e1726d8c080c285eaa779ffa819f89acb335122a9"

FRENCH_FILES = {
    "market": ARTIFACTS / "v24_french_ff3_monthly.zip",
    "quality": ARTIFACTS / "v24_french_6_me_op_monthly.zip",
    "momentum": ARTIFACTS / "v24_french_6_me_prior_12_2_monthly.zip",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(label: str, tickers: list[str], start: str) -> tuple[Path, dict]:
    existing = list(ARTIFACTS.glob(f"snapshot_v24_{label}_*.zip"))
    if existing:
        raise RuntimeError(f"拒絕重複下載 v24 {label}：{existing}")
    panel = fetch_yfinance(tickers, start, "2026-07-31", threads=False)
    contract = validate_panel(
        panel,
        as_of="2026-07-31",
        required=tuple(tickers),
        min_history_coverage=0.98,
        require_fresh=False,
    )
    contract.require()
    fingerprint = panel_fingerprint(panel)
    path = ARTIFACTS / (
        f"snapshot_v24_{label}_{start.replace('-', '')}_20260731_{fingerprint[:8]}.zip"
    )
    manifest = save_snapshot(panel, path, contract=contract)
    return path, manifest


def main() -> int:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if _sha256(PROTOCOL) != PROTOCOL_SHA256 or _sha256(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("v24 凍結協議或產品映射已改變")
    if protocol.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("v24 協議收據不符")
    frozen_mtime = max(
        int(protocol["protocol_mtime_epoch"]),
        int(protocol["product_mapping_mtime_epoch"]),
    )
    academic: dict[str, object] = {}
    for key, path in FRENCH_FILES.items():
        if not path.exists() or path.stat().st_mtime <= frozen_mtime:
            raise RuntimeError(f"v24 French {key} 原檔不存在或沒有晚於凍結")
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            if len(members) != 1 or not members[0].lower().endswith(".csv"):
                raise RuntimeError(f"v24 French {key} ZIP 成員不符：{members}")
        academic[key] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
            "mtime_epoch": int(path.stat().st_mtime),
            "members": members,
            "download_performed_once": True,
        }

    ishares_path, ishares = _snapshot(
        "ishares_quality_momentum", ["MTUM", "QUAL", "SPY"], "2013-07-01"
    )
    invesco_path, invesco = _snapshot(
        "invesco_quality_momentum", ["PDP", "SPHQ", "SPY"], "2007-03-01"
    )
    for path in (ishares_path, invesco_path):
        if path.stat().st_mtime <= frozen_mtime:
            raise RuntimeError("v24 產品快照沒有晚於凍結")

    payload = {
        "status": "v24_first_academic_and_product_downloads_contract_passed",
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
        "academic_sources": academic,
        "ishares_snapshot": {
            "path": str(ishares_path.relative_to(ROOT)),
            "snapshot_mtime_epoch": int(ishares_path.stat().st_mtime),
            "panel_sha256": ishares["panel_sha256"],
            "archive_sha256": _sha256(ishares_path),
            "rows": ishares["rows"],
            "start": ishares["start"],
            "end": ishares["end"],
            "tickers": ishares["tickers"],
            "contract": ishares["contract"],
            "performed_once": True,
        },
        "invesco_snapshot": {
            "path": str(invesco_path.relative_to(ROOT)),
            "snapshot_mtime_epoch": int(invesco_path.stat().st_mtime),
            "panel_sha256": invesco["panel_sha256"],
            "archive_sha256": _sha256(invesco_path),
            "rows": invesco["rows"],
            "start": invesco["start"],
            "end": invesco["end"],
            "tickers": invesco["tickers"],
            "contract": invesco["contract"],
            "performed_once": True,
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
