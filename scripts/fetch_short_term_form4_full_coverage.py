from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

from usfddk.form4_full_coverage import (
    EXPECTED_PROTOCOL_SHA256,
    MANIFEST_PATH,
    PROTOCOL_PATH,
    QUARTER_FILENAMES,
    SEC_URL_TEMPLATE,
    quarter_list,
)

USER_AGENT = "us_fddk Form4 coverage research contact@example.com"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch all frozen SEC Form 4 quarterly ZIPs without parsing rows."
    )
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path.cwd() / MANIFEST_PATH)
    parser.add_argument(
        "--seed-dir",
        type=Path,
        help="Optional owner-only directory containing already verified anchor ZIPs.",
    )
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    args = parser.parse_args()
    staging = args.staging_dir.resolve()
    staging.mkdir(parents=True, exist_ok=True)
    seed = args.seed_dir.resolve() if args.seed_dir else None
    rows: list[dict[str, object]] = []
    for index, quarter in enumerate(quarter_list()):
        year, number = quarter[:4], quarter[-1]
        filename = QUARTER_FILENAMES[quarter]
        url = SEC_URL_TEMPLATE.format(yyyy=year, q=number)
        destination = staging / filename
        if not destination.exists():
            seeded = seed / filename if seed else None
            if seeded is not None and seeded.is_file():
                shutil.copyfile(seeded, destination)
            else:
                _download(url, destination)
        if not destination.is_file() or destination.is_symlink():
            raise RuntimeError(f"missing fetched file: {destination}")
        rows.append(
            {
                "quarter": quarter,
                "filename": filename,
                "url": url,
                "bytes": destination.stat().st_size,
                "sha256": _sha256_file(destination),
            }
        )
        print(f"fetched {quarter} {rows[-1]['bytes']} bytes", flush=True)
        if index + 1 < len(quarter_list()) and args.pause_seconds > 0:
            time.sleep(args.pause_seconds)
    payload: dict[str, object] = {
        "schema_version": 1,
        "status": "fetched_without_row_readout",
        "protocol_path": str(PROTOCOL_PATH),
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "quarters": rows,
    }
    payload["manifest_sha256"] = _canonical_sha256(payload)
    manifest_path = args.manifest.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"manifest": str(manifest_path), "manifest_sha256": payload["manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
