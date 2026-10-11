from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from scripts import probe_short_term_provider_gap_sources as gap_script
from scripts import probe_short_term_provider_guides as guide_script
from scripts import probe_short_term_risk_free_source as rf_script
from usfddk.provider_convergence import STOCK_GUIDE, TREASURY_GUIDE, inspect_provider_guides
from usfddk.risk_free_staging import (
    RiskFreeStagingError,
    inspect_official_rf_zip,
    probe_official_rf_zip,
)
from usfddk.source_probe_evidence import (
    LEGACY_RECORD_HASHES,
    publish_source_probe,
    validate_source_probe,
)

ROOT = Path(__file__).resolve().parents[1]
KINDS = tuple(LEGACY_RECORD_HASHES)
ARTIFACT = Path("artifacts/probe.json")
SITE_DATA = Path("site/data/probe.json")


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _resign(record: dict) -> None:
    unsigned = {
        key: value for key, value in record["probe_evidence"].items() if key != "receipt_sha256"
    }
    record["probe_evidence"]["receipt_sha256"] = _canonical_hash(
        {
            **{key: value for key, value in record.items() if key != "probe_evidence"},
            "probe_evidence": unsigned,
        }
    )


@pytest.fixture(params=KINDS)
def changed_probe(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[str, dict, dict]:
    kind = request.param
    if kind == "risk_free":
        source = ROOT / "artifacts/french_ff_factors_daily_39f9ae1d.zip"
        with zipfile.ZipFile(source) as frozen:
            member = frozen.namelist()[0]
            text = frozen.read(member).decode("utf-8-sig").replace("202606", "202608", 1)
        # Synthetic rows are confined to this regression fixture and never LIVE.
        import exchange_calendars as xcals

        sessions = xcals.get_calendar("XNYS").sessions_in_range("2026-07-01", "2026-07-31")
        text += "\n" + "\n".join(f"{day:%Y%m%d},0,0,0,0.02" for day in sessions)
        text += "\n20260831,0,0,0,0.02\n"
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(member, text.encode())
        inputs = {"source.zip": stream.getvalue()}
        updated = tmp_path / "updated-rf.zip"
        updated.write_bytes(inputs["source.zip"])
        result = probe_official_rf_zip(updated, root=ROOT)
    elif kind == "provider_guides":
        inputs = {}
        for prefix, guide in [("stock", STOCK_GUIDE), ("treasury", TREASURY_GUIDE)]:
            inputs[f"{prefix}-landing.html"] = (
                f"{guide['title']} {guide['effective_date']} {guide['pdf_url'].rsplit('/', 1)[-1]}"
            ).encode()
            inputs[f"{prefix}.pdf"] = b"%PDF-1.7\n/Type/Page>>\nChanged test guide\n"
        result = inspect_provider_guides(
            stock_landing_html=inputs["stock-landing.html"].decode(),
            stock_pdf_bytes=inputs["stock.pdf"],
            treasury_landing_html=inputs["treasury-landing.html"].decode(),
            treasury_pdf_bytes=inputs["treasury.pdf"],
        )
    else:
        downloaded = {
            source_id: [gap_script.PRIMARY_SOURCES[source_id]["url"], identity["marker"]]
            for source_id, identity in gap_script.PROBE_IDENTITIES.items()
        }
        downloaded["factset_benchmarks"][1] = "Changed official page without its identity marker"
        inputs = {"sources.json": json.dumps(downloaded).encode()}
        result = gap_script.inspect_current_sources(downloaded)
    return kind, inputs, result


def _publish(case: tuple[str, dict, dict], tmp_path: Path) -> dict:
    kind, inputs, result = case
    return publish_source_probe(
        result,
        inputs,
        kind=kind,
        root=ROOT,
        output_root=tmp_path,
        artifact=ARTIFACT,
        site_data=SITE_DATA,
    )


def test_changed_source_is_reproducible_and_cannot_qualify(
    changed_probe: tuple, tmp_path: Path
) -> None:
    kind, _, result = changed_probe
    record = _publish(changed_probe, tmp_path)
    assert validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind) == result
    assert json.loads((tmp_path / ARTIFACT).read_text()) == record
    assert json.loads((tmp_path / SITE_DATA).read_text()) == record
    assert result["schema_version"] == 1
    assert result["formal_backtest_authorized"] is False
    assert result["paper_authorized"] is False
    assert result["paper_state"] == "all_cash"
    assert result["strategy_run_count"] == result["real_money_action_usd"] == 0
    assert _publish(changed_probe, tmp_path) == record  # Same-source retries retain the receipt.
    if kind == "risk_free":
        assert result["data_cut"] == "202608"
        assert result["study"]["available_sessions"] == 5_031
        assert result["study"]["missing_session_count"] == 0
        assert (
            result["status"]
            == "candidate_full_coverage_detected_manual_freeze_and_license_review_required"
        )
        assert result["matches_frozen_source"] is False
        assert result["new_source_qualified"] is result["formal_rf_input_ready"] is False
        with pytest.raises(RiskFreeStagingError) as error:
            inspect_official_rf_zip(tmp_path / "updated-rf.zip", root=ROOT)
        assert error.value.code == "rf_source_hash_mismatch"
    elif kind == "provider_guides":
        assert result["status"] == "unqualified_new_guide"
        assert result["all_match_frozen_guides"] is result["new_guide_qualified"] is False
    else:
        assert result["status"] == "manual_review_required"
        assert result["source_identity_count"] == 5
        assert result["all_match_frozen_identities"] is result["new_source_qualified"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "tampered"),
        ("schema_version", 2),
        ("strategy_run_count", 1),
        ("paper_authorized", True),
        ("paper_state", "invested"),
        ("real_money_action_usd", 1),
    ],
)
def test_tampered_artifact_is_rejected(
    changed_probe: tuple, tmp_path: Path, field: str, value: object
) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    record[field] = value
    with pytest.raises(ValueError):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_recomputed_receipt_cannot_hide_changed_source_output(
    changed_probe: tuple, tmp_path: Path
) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    record["schema_version"] = 2
    _resign(record)
    with pytest.raises(ValueError, match="differs from reproduced raw inputs"):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_coverage_or_identity_tampering_fails_even_with_rebound_receipt(
    changed_probe: tuple, tmp_path: Path
) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    if kind == "risk_free":
        record["study"]["available_sessions"] -= 1
    elif kind == "provider_guides":
        record["observations"]["stock_ciz"]["pdf_sha256"] = "0" * 64
    else:
        record["observations"]["factset_benchmarks"]["marker_present"] = True
    _resign(record)
    with pytest.raises(ValueError, match="differs from reproduced raw inputs"):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_tampered_input_archive_is_rejected(changed_probe: tuple, tmp_path: Path) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    path = tmp_path / record["probe_evidence"]["input_archive"]
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="input archive hash mismatch"):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_changed_input_path_cannot_escape_archive(changed_probe: tuple, tmp_path: Path) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    record["probe_evidence"]["input_archive"] = "../../external.zip"
    _resign(record)
    with pytest.raises(ValueError, match="input path mismatch"):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_receipt_schema_rejects_boolean_version_even_if_resigned(
    changed_probe: tuple,
    tmp_path: Path,
) -> None:
    kind, _, _ = changed_probe
    record = _publish(changed_probe, tmp_path)
    record["probe_evidence"]["schema_version"] = True
    _resign(record)
    with pytest.raises(ValueError, match="evidence schema mismatch"):
        validate_source_probe(record, root=tmp_path, protocol_root=ROOT, kind=kind)


def test_publisher_does_not_overwrite_a_corrupt_mirror(
    changed_probe: tuple, tmp_path: Path
) -> None:
    _publish(changed_probe, tmp_path)
    site = tmp_path / SITE_DATA
    record = json.loads(site.read_text())
    record["schema_version"] = 2
    site.write_text(json.dumps(record))
    before = {path: (tmp_path / path).read_bytes() for path in (ARTIFACT, SITE_DATA)}
    with pytest.raises(ValueError, match="mirrors differ"):
        _publish(changed_probe, tmp_path)
    assert before == {path: (tmp_path / path).read_bytes() for path in before}


@pytest.mark.parametrize("kind", KINDS)
def test_legacy_fixtures_remain_exact_and_tamper_evident(kind: str) -> None:
    record = json.loads((ROOT / f"tests/fixtures/source_probes/{kind}.json").read_text())
    assert _canonical_hash(record) == LEGACY_RECORD_HASHES[kind]
    assert validate_source_probe(record, root=ROOT, kind=kind) == record
    changed = copy.deepcopy(record)
    changed["status"] = "edited"
    with pytest.raises(ValueError, match="requires reproducible input evidence"):
        validate_source_probe(changed, root=ROOT, kind=kind)


def test_changed_source_cli_outputs_and_exit_status(
    changed_probe: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kind, inputs, result = changed_probe
    if kind == "risk_free":
        exit_code = rf_script.main(
            ["--source", str(tmp_path / "updated-rf.zip"), "--output-root", str(tmp_path)]
        )
        name = "risk_free_source"
        assert exit_code == 0
    elif kind == "provider_guides":
        arguments = ["--output-root", str(tmp_path)]
        for member, option in [
            ("stock-landing.html", "--stock-landing"),
            ("stock.pdf", "--stock-pdf"),
            ("treasury-landing.html", "--treasury-landing"),
            ("treasury.pdf", "--treasury-pdf"),
        ]:
            path = tmp_path / member
            path.write_bytes(inputs[member])
            arguments += [option, str(path)]
        assert guide_script.main(arguments) == 0
        name = "provider_guide"
    else:
        downloaded = json.loads(inputs["sources.json"])
        by_url = {
            gap_script.PRIMARY_SOURCES[key]["url"]: value for key, value in downloaded.items()
        }
        monkeypatch.setattr(gap_script, "_download", lambda url: by_url[url])
        assert gap_script.main(["--output-root", str(tmp_path)]) == 2
        name = "provider_gap_source"
    artifact = json.loads((tmp_path / f"artifacts/short_term_{name}_probe.json").read_text())
    site = json.loads(
        (tmp_path / f"site/data/short-term-{name.replace('_', '-')}-probe.json").read_text()
    )
    assert artifact == site
    assert validate_source_probe(artifact, root=tmp_path, protocol_root=ROOT, kind=kind) == result


def test_failed_second_mirror_replacement_restores_prior_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kind = "provider_gap_sources"
    downloaded = {
        key: [gap_script.PRIMARY_SOURCES[key]["url"], value["marker"]]
        for key, value in gap_script.PROBE_IDENTITIES.items()
    }
    before_case = (
        kind,
        {"sources.json": json.dumps(downloaded).encode()},
        gap_script.inspect_current_sources(downloaded),
    )
    _publish(before_case, tmp_path)
    before = {path: (tmp_path / path).read_bytes() for path in (ARTIFACT, SITE_DATA)}
    downloaded["factset_benchmarks"][1] = "changed"
    changed_case = (
        kind,
        {"sources.json": json.dumps(downloaded).encode()},
        gap_script.inspect_current_sources(downloaded),
    )
    real_replace = os.replace

    def failed_site_replace(source: Path, target: Path) -> None:
        if target == tmp_path / SITE_DATA:
            raise OSError("simulated site replacement failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", failed_site_replace)
    with pytest.raises(OSError, match="simulated site replacement failure"):
        _publish(changed_case, tmp_path)
    assert before == {path: (tmp_path / path).read_bytes() for path in before}


@pytest.mark.parametrize(
    ("kind", "script", "name"),
    [
        ("provider_guides", guide_script, "provider_guide"),
        ("provider_gap_sources", gap_script, "provider_gap_source"),
    ],
)
def test_unavailable_source_preserves_published_pair(
    kind: str, script: object, name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = (ROOT / f"tests/fixtures/source_probes/{kind}.json").read_bytes()
    paths = [
        tmp_path / f"artifacts/short_term_{name}_probe.json",
        tmp_path / f"site/data/short-term-{name.replace('_', '-')}-probe.json",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fixture)

    def unavailable(url: str) -> bytes:
        raise OSError("HTTP 404 fixture")

    monkeypatch.setattr(script, "_download", unavailable)
    with pytest.raises(OSError, match="HTTP 404"):
        script.main(["--output-root", str(tmp_path)])
    assert all(path.read_bytes() == fixture for path in paths)
