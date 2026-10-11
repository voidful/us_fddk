"""Reproduce mutable identity probes without qualifying new research inputs."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

# Exact pre-existing records remain valid; changed records require raw inputs.
LEGACY_RECORD_HASHES = {
    "risk_free": "f5711e38389c06ea92fa8c7496b9ac42abbd1c2ec461c68d45624895759f03a6",
    "provider_guides": "cfd67db27633524cfe6524afd3333e0261fbc638527dc1362e133878d5b12447",
    "provider_gap_sources": "27b1b4d2e314e0e66e5517b0e3265d00912d23ae92bd209fb75cbe22753ba2cc",
}
INPUT_MEMBERS = {
    "risk_free": {"source.zip"},
    "provider_guides": {
        "stock-landing.html",
        "stock.pdf",
        "treasury-landing.html",
        "treasury.pdf",
    },
    "provider_gap_sources": {"sources.json"},
}
MAX_INPUT_BYTES = 32 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _assert_unqualified(record: dict[str, Any]) -> None:
    for name in (
        "new_source_qualified",
        "new_guide_qualified",
        "provider_package_qualified",
        "formal_rf_input_ready",
        "formal_backtest_authorized",
        "paper_authorized",
    ):
        if name in record and record[name] is not False:
            raise ValueError(f"source probe cannot qualify {name}")
    if (
        type(record.get("strategy_run_count")) is not int
        or record["strategy_run_count"] != 0
        or record.get("paper_state") != "all_cash"
        or _canonical(record.get("real_money_action_usd")) != b"0"
    ):
        raise ValueError("source probe cannot authorize strategy, Paper or real money")


def _reproduce(kind: str, inputs: dict[str, bytes], root: Path) -> dict[str, Any]:
    if set(inputs) != INPUT_MEMBERS[kind]:
        raise ValueError("source probe input file set mismatch")
    if kind == "risk_free":
        from usfddk.risk_free_staging import probe_official_rf_zip

        with tempfile.TemporaryDirectory(prefix="usfddk-probe-check-") as temporary:
            source = Path(temporary) / "source.zip"
            source.write_bytes(inputs["source.zip"])
            return probe_official_rf_zip(source, root=root)
    if kind == "provider_guides":
        from usfddk.provider_convergence import inspect_provider_guides

        return inspect_provider_guides(
            stock_landing_html=inputs["stock-landing.html"].decode("utf-8", errors="replace"),
            stock_pdf_bytes=inputs["stock.pdf"],
            treasury_landing_html=inputs["treasury-landing.html"].decode("utf-8", errors="replace"),
            treasury_pdf_bytes=inputs["treasury.pdf"],
        )
    from scripts.probe_short_term_provider_gap_sources import inspect_current_sources

    downloaded = json.loads(inputs["sources.json"])
    return inspect_current_sources(downloaded)


def validate_source_probe(
    record: dict[str, Any],
    *,
    root: str | Path,
    kind: str,
    protocol_root: str | Path | None = None,
) -> dict[str, Any]:
    """Check every output field against archived inputs and its bound receipt."""
    if kind not in INPUT_MEMBERS:
        raise ValueError("unknown source probe kind")
    body = {key: value for key, value in record.items() if key != "probe_evidence"}
    _assert_unqualified(body)
    evidence = record.get("probe_evidence")
    if evidence is None:
        if _digest(body) != LEGACY_RECORD_HASHES[kind]:
            raise ValueError("changed source probe requires reproducible input evidence")
        return body
    if (
        not isinstance(evidence, dict)
        or set(evidence)
        != {
            "schema_version",
            "kind",
            "input_archive",
            "input_archive_sha256",
            "receipt_sha256",
        }
        or type(evidence["schema_version"]) is not int
        or evidence["schema_version"] != 1
        or evidence["kind"] != kind
    ):
        raise ValueError("source probe evidence schema mismatch")
    unsigned = {key: value for key, value in evidence.items() if key != "receipt_sha256"}
    if evidence["receipt_sha256"] != _digest({**body, "probe_evidence": unsigned}):
        raise ValueError("source probe receipt hash mismatch")
    digest = evidence["input_archive_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("source probe input hash invalid")
    relative = Path("artifacts/source_probe_inputs") / f"{kind}_{digest}.zip"
    if evidence["input_archive"] != relative.as_posix():
        raise ValueError("source probe input path mismatch")
    root = Path(root).resolve()
    archive_path = (root / relative).resolve()
    if not archive_path.is_relative_to(root / "artifacts/source_probe_inputs"):
        raise ValueError("source probe input path escapes its archive")
    raw = archive_path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("source probe input archive hash mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if (
            {info.filename for info in infos} != INPUT_MEMBERS[kind]
            or len(infos) != len(INPUT_MEMBERS[kind])
            or sum(info.file_size for info in infos) > MAX_INPUT_BYTES
        ):
            raise ValueError("source probe input archive file set or size mismatch")
        inputs = {info.filename: archive.read(info) for info in infos}
    research_root = root if protocol_root is None else Path(protocol_root)
    if _canonical(body) != _canonical(_reproduce(kind, inputs, research_root)):
        raise ValueError("source probe output differs from reproduced raw inputs")
    return body


def _write_mirrors(paths: tuple[Path, Path], payload: bytes) -> None:
    """Prepare both files first and roll back a failed second replacement."""
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    try:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            for target, data in (
                (staged, payload),
                (backups, path.read_bytes() if path.exists() else None),
            ):
                if data is None:
                    target[path] = None
                    continue
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                    stream.write(data)
                    target[path] = Path(stream.name)
        for path in paths:
            os.replace(staged[path], path)
            replaced.append(path)
    except OSError:
        for path in reversed(replaced):
            if backups[path] is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(backups[path], path)
        raise
    finally:
        for temporary in [*staged.values(), *backups.values()]:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def publish_source_probe(
    result: dict[str, Any],
    inputs: dict[str, bytes],
    *,
    kind: str,
    root: str | Path,
    output_root: str | Path,
    artifact: Path,
    site_data: Path,
) -> dict[str, Any]:
    """Publish unqualified metadata with immutable, reproducible source evidence."""
    root, output_root = Path(root), Path(output_root)
    paths = (output_root / artifact, output_root / site_data)
    current = None
    if any(path.exists() for path in paths):
        if not all(path.exists() for path in paths):
            raise ValueError("source probe artifact/site mirror missing")
        records = [json.loads(path.read_bytes()) for path in paths]
        if _canonical(records[0]) != _canonical(records[1]):
            raise ValueError("source probe artifact/site mirrors differ")
        # Inputs live under output_root; frozen research protocols live under root.
        current = records[0]
        validate_source_probe(current, root=output_root, kind=kind, protocol_root=root)
    if current is not None and _canonical(result) == _canonical(
        {key: value for key, value in current.items() if key != "probe_evidence"}
    ):
        return current
    if _canonical(result) != _canonical(_reproduce(kind, inputs, root)):
        raise ValueError("source probe publication differs from its raw inputs")
    _assert_unqualified(result)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(inputs.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    raw = stream.getvalue()
    if len(raw) > MAX_INPUT_BYTES or sum(map(len, inputs.values())) > MAX_INPUT_BYTES:
        raise ValueError("source probe inputs exceed size limit")
    digest = hashlib.sha256(raw).hexdigest()
    relative = Path("artifacts/source_probe_inputs") / f"{kind}_{digest}.zip"
    archive_path = output_root / relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists() and archive_path.read_bytes() != raw:
        raise ValueError("source probe input archive is immutable")
    if not archive_path.exists():
        archive_path.write_bytes(raw)
    evidence = {
        "schema_version": 1,
        "kind": kind,
        "input_archive": relative.as_posix(),
        "input_archive_sha256": digest,
    }
    record = {**result, "probe_evidence": evidence}
    evidence["receipt_sha256"] = _digest(record)
    payload = (
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False).encode()
        + b"\n"
    )
    _write_mirrors(paths, payload)
    return record
