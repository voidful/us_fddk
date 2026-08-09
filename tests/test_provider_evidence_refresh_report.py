from __future__ import annotations

import json
from pathlib import Path

from scripts.build_short_term_provider_evidence_refresh_report import (
    render_report,
)
from scripts.probe_short_term_provider_evidence_refresh import _write_payload

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_evidence_refresh.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_REPORT.md"


def test_report_is_rendered_from_the_current_receipt() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")
    assert report == render_report(payload)
    assert payload["status"] in report
    assert payload["provider_package_qualified"] is False
    assert payload["formal_backtest_authorized"] is False
    assert payload["paper_state"] == "all_cash"
    assert payload["real_money_action_usd"] == 0
    assert payload["observed_at_utc"].endswith("Z")
    assert payload["observed_at_utc"] in report
    for observation in payload["observations"].values():
        assert observation["body_sha256"] in report


def test_probe_writer_keeps_artifact_site_data_and_report_in_lockstep(
    tmp_path: Path, monkeypatch
) -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    artifact = tmp_path / "artifact.json"
    site_data = tmp_path / "site-data.json"
    report = tmp_path / "report.md"
    monkeypatch.setattr(
        "scripts.probe_short_term_provider_evidence_refresh.ARTIFACT", artifact
    )
    monkeypatch.setattr(
        "scripts.probe_short_term_provider_evidence_refresh.SITE_DATA", site_data
    )
    monkeypatch.setattr(
        "scripts.probe_short_term_provider_evidence_refresh.REPORT", report
    )

    _write_payload(payload)

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    assert artifact.read_text(encoding="utf-8") == serialized
    assert site_data.read_text(encoding="utf-8") == serialized
    assert report.read_text(encoding="utf-8") == render_report(json.loads(serialized))
