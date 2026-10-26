from __future__ import annotations

import json
import os
import stat
from collections import deque
from pathlib import Path
from urllib.request import Request

import pytest

from usfddk.sec_edgar_client import (
    SEC_CATALOG_URL,
    SEC_OWNERSHIP_ATOM_URL,
    SEC_SUBMISSIONS_BULK_URL,
    SecEdgarClient,
    SecEdgarClientError,
    _AllowlistedSecRedirectHandler,
    _receipt_hash,
    parse_insider_quarter_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "us-fddk-form4-research test-owner@example.com"
ZIP_BODY = b"PK\x03\x04isolated-test-zip"


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str,
        status: int = 200,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Date": "Mon, 10 Aug 2026 00:00:00 GMT",
            **(headers or {}),
        }
        self._body = body
        self._offset = 0
        self._url = url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body) - self._offset
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeOpener:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = deque(responses)
        self.requests: list[tuple[Request, float]] = []

    def __call__(self, request: Request, timeout: float) -> FakeResponse:
        self.requests.append((request, timeout))
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        return self.responses.popleft()


class AdvancingClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        value = self.value
        self.value += 1.0
        return value


class SleepingClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.value

    def sleep(self, duration: float) -> None:
        self.sleeps.append(duration)
        self.value += duration


class SequenceNow:
    def __init__(self, *values: str) -> None:
        self.values = deque(values)

    def __call__(self) -> str:
        if not self.values:
            raise AssertionError("unexpected wall-clock read")
        return self.values.popleft()


def _client(
    tmp_path: Path,
    opener: FakeOpener,
    *,
    quarantine: Path | None = None,
    **overrides: object,
) -> SecEdgarClient:
    options = {
        "repository_root": ROOT,
        "user_agent": USER_AGENT,
        "opener": opener,
        "clock": AdvancingClock(),
        "sleeper": lambda _: None,
        "now": lambda: "2026-08-09T22:00:00Z",
    }
    options.update(overrides)
    return SecEdgarClient(quarantine or tmp_path / "sec-quarantine", **options)


def _error_code(callable_: object) -> str:
    with pytest.raises(SecEdgarClientError) as error:
        callable_()  # type: ignore[operator]
    return error.value.code


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def test_client_rejects_missing_contact_and_rate_above_one_before_mkdir(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-contact"
    with pytest.raises(SecEdgarClientError) as error:
        SecEdgarClient(missing, repository_root=ROOT, user_agent="us-fddk")
    assert error.value.code == "sec_user_agent_contact_missing"
    assert not missing.exists()

    too_fast = tmp_path / "too-fast"
    with pytest.raises(SecEdgarClientError) as error:
        SecEdgarClient(
            too_fast,
            repository_root=ROOT,
            user_agent=USER_AGENT,
            requests_per_second=1.01,
        )
    assert error.value.code == "sec_rate_limit_invalid"
    assert not too_fast.exists()


def test_quarantine_must_be_absolute_external_owner_only_and_not_symlink(
    tmp_path: Path,
) -> None:
    opener = FakeOpener()
    assert (
        _error_code(
            lambda: SecEdgarClient(
                "relative/raw", repository_root=ROOT, user_agent=USER_AGENT, opener=opener
            )
        )
        == "sec_quarantine_path_invalid"
    )
    assert (
        _error_code(
            lambda: SecEdgarClient(
                ROOT / "raw-sec-data",
                repository_root=ROOT,
                user_agent=USER_AGENT,
                opener=opener,
            )
        )
        == "sec_quarantine_inside_repository"
    )

    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    assert (
        _error_code(
            lambda: SecEdgarClient(
                public, repository_root=ROOT, user_agent=USER_AGENT, opener=opener
            )
        )
        == "sec_quarantine_not_owner_only"
    )

    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    assert (
        _error_code(
            lambda: SecEdgarClient(
                alias, repository_root=ROOT, user_agent=USER_AGENT, opener=opener
            )
        )
        == "sec_quarantine_path_invalid"
    )


def test_catalog_discovery_handles_moved_paths_and_rejects_ambiguity() -> None:
    html = """
    <a href="/files/structureddata/data/insider-transactions-data-sets/2006q1_form345.zip">Q1</a>
    <a href="https://www.sec.gov/files/dera/data/insider-transactions-data-sets/2026q2_form345.zip">Q2</a>
    """
    quarters = parse_insider_quarter_catalog(html)
    assert quarters[(2006, 1)].endswith("2006q1_form345.zip")
    assert quarters[(2026, 2)].endswith("2026q2_form345.zip")

    duplicate = html + ('<a href="/different/2026q2_form345.zip">duplicate</a>')
    assert (
        _error_code(lambda: parse_insider_quarter_catalog(duplicate))
        == "sec_catalog_duplicate_quarter"
    )
    assert (
        _error_code(
            lambda: parse_insider_quarter_catalog(
                '<a href="https://evil.example/2026q2_form345.zip">bad</a>'
            )
        )
        == "sec_url_not_allowed"
    )
    assert (
        _error_code(lambda: parse_insider_quarter_catalog("<html>none</html>"))
        == "sec_catalog_parse_failed"
    )
    assert (
        _error_code(
            lambda: parse_insider_quarter_catalog(html, base_url="https://www.sec.gov:444/catalog")
        )
        == "sec_url_not_allowed"
    )


def test_fetch_stores_owner_only_content_and_whole_receipt_hash(tmp_path: Path) -> None:
    opener = FakeOpener(
        FakeResponse(
            ZIP_BODY,
            url=SEC_SUBMISSIONS_BULK_URL,
            content_type="application/zip",
            headers={"ETag": '"test-etag"'},
        )
    )
    client = _client(tmp_path, opener)
    receipt = client.fetch_submissions_bulk()

    assert receipt["body_sha256"]
    assert receipt["first_observed_basis"] == "local_full_body_completion_only"
    assert receipt["observation_mode"] == "engineering_fetch_not_contemporaneous_evidence"
    assert receipt["first_observed_external_anchor_present"] is False
    assert receipt["receipt_externally_anchored"] is False
    assert receipt["public_at"] is None
    assert receipt["known_at"] is None
    assert receipt["configured_requests_per_second"] == 1.0
    assert receipt["cross_machine_global_rate_limit_proven"] is False
    assert receipt["encrypted_quarantine_verified"] is False
    assert receipt["form4_admission_gate_passed"] is False
    assert receipt["paper_authorized"] is False
    assert receipt["real_money_action_usd"] == 0
    assert len(receipt["receipt_sha256"]) == 64

    object_path = client.quarantine / receipt["object_path"]
    receipt_path = next(client.source_versions.glob("*.json"))
    assert object_path.read_bytes() == ZIP_BODY
    assert _mode(client.quarantine) == 0o700
    assert _mode(object_path) == 0o600
    assert _mode(receipt_path) == 0o600
    assert object_path.stat().st_nlink == 1
    assert receipt_path.stat().st_nlink == 1

    request, timeout = opener.requests[0]
    assert request.full_url == SEC_SUBMISSIONS_BULK_URL
    assert request.get_header("User-agent") == USER_AGENT
    assert timeout == 60.0


def test_same_url_new_bytes_append_new_versions_and_first_seen_never_moves(
    tmp_path: Path,
) -> None:
    clock = AdvancingClock()
    first_opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    quarantine = tmp_path / "versions"
    first = _client(
        tmp_path, first_opener, quarantine=quarantine, clock=clock
    ).fetch_submissions_bulk()

    second_opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    second = _client(
        tmp_path,
        second_opener,
        quarantine=quarantine,
        clock=clock,
        now=lambda: "2026-08-10T22:00:00Z",
    ).fetch_submissions_bulk()
    assert second == first

    changed = b"PK\x03\x04changed-snapshot"
    third_opener = FakeOpener(FakeResponse(changed, url=SEC_SUBMISSIONS_BULK_URL))
    third = _client(
        tmp_path,
        third_opener,
        quarantine=quarantine,
        clock=clock,
        now=lambda: "2026-08-11T22:00:00Z",
    ).fetch_submissions_bulk()
    assert third["body_sha256"] != first["body_sha256"]
    assert len(list((quarantine / "objects").glob("*.bin"))) == 2
    assert len(list((quarantine / "source_versions").glob("*.json"))) == 2


def test_rehashed_receipt_mutations_are_detected(tmp_path: Path) -> None:
    quarantine = tmp_path / "tamper"
    clock = AdvancingClock()
    opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    client = _client(tmp_path, opener, quarantine=quarantine, clock=clock)
    receipt = client.fetch_submissions_bulk()
    receipt_path = next(client.source_versions.glob("*.json"))
    mutations = (
        {"form4_admission_gate_passed": True},
        {"http_attempt_ledger_complete": True},
        {"first_observed_basis": "official_public_timestamp"},
        {"first_observed_at": "2006-01-01T00:00:00Z"},
        {"content_type": "text/html"},
        {
            "byte_count": receipt["byte_count"] + 1,
            "content_length_header": receipt["byte_count"] + 1,
        },
        {"real_money_action_usd": False},
    )

    for mutation in mutations:
        payload = dict(receipt)
        payload.update(mutation)
        payload["receipt_sha256"] = _receipt_hash(payload)
        receipt_path.write_text(json.dumps(payload), encoding="utf-8")
        receipt_path.chmod(0o600)
        retry = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
        retry_client = _client(
            tmp_path,
            retry,
            quarantine=quarantine,
            clock=clock,
        )
        assert _error_code(retry_client.fetch_submissions_bulk) == "sec_cached_receipt_invalid"

    payload = {**receipt, "unexpected_admission_claim": True}
    payload["receipt_sha256"] = _receipt_hash(payload)
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")
    receipt_path.chmod(0o600)
    retry = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    retry_client = _client(tmp_path, retry, quarantine=quarantine, clock=clock)
    assert _error_code(retry_client.fetch_submissions_bulk) == "sec_cached_receipt_invalid"


def test_content_object_mutation_is_detected_with_valid_stored_receipt(tmp_path: Path) -> None:
    client = _client(
        tmp_path,
        FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL)),
    )
    receipt = client.fetch_submissions_bulk()
    object_path = client.quarantine / receipt["object_path"]
    object_path.write_bytes(b"X" * len(ZIP_BODY))
    object_path.chmod(0o600)
    assert _error_code(lambda: client.object_bytes(receipt)) == "sec_cached_object_invalid"


def test_rate_lock_rejects_symlink_and_enforces_one_request_per_second(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, FakeOpener())
    target = tmp_path / "lock-target"
    target.write_text("100\n", encoding="ascii")
    target.chmod(0o600)
    lock = client.quarantine / "locks/sec-global-rate.lock"
    lock.symlink_to(target)
    assert _error_code(client._wait_rate_limit) == "sec_rate_lock_invalid"
    assert target.read_text(encoding="ascii") == "100\n"

    lock.unlink()
    clock = SleepingClock()
    client._clock = clock.now
    client._sleeper = clock.sleep
    client._wait_rate_limit()
    client._wait_rate_limit()
    assert clock.sleeps == [1.0]

    clock.value = 50.0
    assert _error_code(client._wait_rate_limit) == "sec_rate_clock_regressed"


@pytest.mark.parametrize("raw", ["nan\n", "inf\n", "-inf\n"])
def test_rate_lock_rejects_non_finite_persisted_timestamps(
    tmp_path: Path,
    raw: str,
) -> None:
    client = _client(tmp_path / raw.strip().replace("-", "negative"), FakeOpener())
    lock = client.quarantine / "locks/sec-global-rate.lock"
    lock.write_text(raw, encoding="ascii")
    lock.chmod(0o600)
    assert _error_code(client._wait_rate_limit) == "sec_rate_lock_corrupt"


@pytest.mark.parametrize("clock_value", [float("nan"), float("inf"), float("-inf")])
def test_rate_lock_rejects_non_finite_clock_values(
    tmp_path: Path,
    clock_value: float,
) -> None:
    client = _client(tmp_path, FakeOpener(), clock=lambda: clock_value)
    assert _error_code(client._wait_rate_limit) == "sec_rate_clock_invalid"


def test_rate_lock_fails_closed_when_sleep_does_not_satisfy_interval(
    tmp_path: Path,
) -> None:
    sleeps: list[float] = []
    client = _client(
        tmp_path,
        FakeOpener(),
        clock=lambda: 100.0,
        sleeper=sleeps.append,
    )
    lock = client.quarantine / "locks/sec-global-rate.lock"
    lock.write_text("100\n", encoding="ascii")
    lock.chmod(0o600)

    assert _error_code(client._wait_rate_limit) == "sec_rate_sleep_incomplete"
    assert sleeps == [1.0, 1.0, 1.0]
    assert lock.read_text(encoding="ascii") == "100\n"


def test_403_or_429_trips_persistent_manual_circuit_breaker(tmp_path: Path) -> None:
    opener = FakeOpener(
        FakeResponse(
            b"",
            url=SEC_SUBMISSIONS_BULK_URL,
            status=429,
            headers={"Retry-After": "120"},
        ),
        FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL),
    )
    client = _client(tmp_path, opener)
    assert _error_code(client.fetch_submissions_bulk) == "sec_rate_limited_stop"
    assert client.circuit_breaker.exists()
    assert _mode(client.circuit_breaker) == 0o600
    assert _error_code(client.fetch_submissions_bulk) == "sec_circuit_breaker_open"
    assert len(opener.requests) == 1


@pytest.mark.parametrize(
    ("response", "max_bytes", "code"),
    [
        (
            FakeResponse(
                ZIP_BODY,
                url=SEC_SUBMISSIONS_BULK_URL,
                content_type="text/html",
            ),
            100,
            "sec_content_type_invalid",
        ),
        (
            FakeResponse(
                ZIP_BODY,
                url=SEC_SUBMISSIONS_BULK_URL,
                headers={"Content-Length": "not-an-integer"},
            ),
            100,
            "sec_content_length_invalid",
        ),
        (
            FakeResponse(
                ZIP_BODY,
                url=SEC_SUBMISSIONS_BULK_URL,
                headers={"Content-Length": "1000"},
            ),
            100,
            "sec_response_too_large",
        ),
        (
            FakeResponse(
                ZIP_BODY,
                url=SEC_SUBMISSIONS_BULK_URL,
                headers={"Content-Length": "1"},
            ),
            100,
            "sec_content_length_invalid",
        ),
        (
            FakeResponse(b"not-a-zip", url=SEC_SUBMISSIONS_BULK_URL),
            100,
            "sec_zip_magic_invalid",
        ),
        (
            FakeResponse(ZIP_BODY, url="https://evil.example/redirected"),
            100,
            "sec_url_not_allowed",
        ),
    ],
)
def test_response_validation_fails_closed(
    tmp_path: Path,
    response: FakeResponse,
    max_bytes: int,
    code: str,
) -> None:
    client = _client(
        tmp_path,
        FakeOpener(response),
        max_response_bytes=max_bytes,
    )
    assert _error_code(client.fetch_submissions_bulk) == code


@pytest.mark.parametrize(
    "now_value",
    ["not-a-timestamp", "2026-08-09T22:00:00+00:00", ""],
)
def test_fetch_rejects_invalid_or_noncanonical_observation_clock_before_request(
    tmp_path: Path,
    now_value: str,
) -> None:
    opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    client = _client(tmp_path, opener, now=lambda: now_value)
    assert _error_code(client.fetch_submissions_bulk) == "sec_observation_clock_invalid"
    assert opener.requests == []


def test_fetch_rejects_first_observation_before_request_start(tmp_path: Path) -> None:
    opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    client = _client(
        tmp_path,
        opener,
        now=SequenceNow(
            "2026-08-09T22:00:00Z",
            "2026-08-09T21:59:59Z",
        ),
    )
    assert _error_code(client.fetch_submissions_bulk) == "sec_observation_clock_invalid"
    assert len(opener.requests) == 1
    assert list(client.source_versions.glob("*.json")) == []


def test_redirect_handler_blocks_foreign_location_before_following() -> None:
    handler = _AllowlistedSecRedirectHandler()
    request = Request(SEC_CATALOG_URL)
    assert (
        _error_code(
            lambda: handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://evil.example/steal-contact",
            )
        )
        == "sec_url_not_allowed"
    )
    assert (
        _error_code(
            lambda: handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                SEC_SUBMISSIONS_BULK_URL,
            )
        )
        == "sec_redirect_not_allowed"
    )


def test_public_methods_construct_exact_official_urls_and_catalog_is_memoized(
    tmp_path: Path,
) -> None:
    quarter_url = (
        "https://www.sec.gov/files/structureddata/data/"
        "insider-transactions-data-sets/2026q2_form345.zip"
    )
    catalog_body = f'<a href="{quarter_url}">2026 Q2</a>'.encode()
    opener = FakeOpener(
        FakeResponse(catalog_body, url=SEC_CATALOG_URL, content_type="text/html"),
        FakeResponse(ZIP_BODY, url=quarter_url, content_type="application/zip"),
    )
    client = _client(tmp_path, opener)
    first_catalog = client.fetch_catalog()
    second_catalog = client.fetch_catalog()
    assert second_catalog == first_catalog
    client.fetch_quarter(2026, 2)
    assert [request.full_url for request, _ in opener.requests] == [
        SEC_CATALOG_URL,
        quarter_url,
    ]

    daily_url = "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR2/form.20260630.idx"
    accession = "0000123456-26-000001"
    index_body = (f"4  issuer  123456  2026-06-30  edgar/data/123456/{accession}.txt\n").encode(
        "ascii"
    )
    raw_url = (
        "https://www.sec.gov/Archives/edgar/data/123456/"
        f"{accession.replace('-', '')}/{accession}.txt"
    )
    atom_url = f"{SEC_OWNERSHIP_ATOM_URL}?action=getcurrent&owner=only&count=100&output=atom"
    opener = FakeOpener(
        FakeResponse(index_body, url=daily_url, content_type="text/plain"),
        FakeResponse(b"<SEC-DOCUMENT>test</SEC-DOCUMENT>", url=raw_url, content_type="text/plain"),
        FakeResponse(b"<feed/>", url=atom_url, content_type="application/atom+xml"),
    )
    client = _client(tmp_path / "other", opener)
    index_receipt = client.fetch_daily_form_index("2026-06-30")
    client.fetch_complete_submission(
        123456,
        accession,
        daily_index_receipt=index_receipt,
    )
    client.poll_ownership_atom()
    assert [request.full_url for request, _ in opener.requests] == [
        daily_url,
        raw_url,
        atom_url,
    ]


def test_complete_submission_requires_daily_index_archive_path_evidence(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, FakeOpener())
    fake = {
        "source_kind": "edgar_submissions_bulk_zip",
        "body_sha256": "a" * 64,
        "object_path": f"objects/{'a' * 64}.bin",
    }
    assert (
        _error_code(
            lambda: client.fetch_complete_submission(
                123456,
                "0000123456-26-000001",
                daily_index_receipt=fake,
            )
        )
        == "sec_archive_path_evidence_missing"
    )


def test_complete_submission_rejects_forged_daily_receipt_backed_by_other_object(
    tmp_path: Path,
) -> None:
    accession = "0000123456-26-000001"
    archive_path = f"edgar/data/123456/{accession}.txt"
    body = b"PK\x03\x04arbitrary object " + archive_path.encode("ascii") + b"\n"
    opener = FakeOpener(FakeResponse(body, url=SEC_SUBMISSIONS_BULK_URL))
    client = _client(tmp_path, opener)
    other_receipt = client.fetch_submissions_bulk()
    daily_url = "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR2/form.20260630.idx"
    forged = {
        **other_receipt,
        "source_kind": "edgar_daily_form_index",
        "requested_url": daily_url,
        "final_url": daily_url,
    }
    forged["receipt_sha256"] = _receipt_hash(forged)

    assert (
        _error_code(
            lambda: client.fetch_complete_submission(
                123456,
                accession,
                daily_index_receipt=forged,
            )
        )
        == "sec_archive_path_evidence_missing"
    )
    assert len(opener.requests) == 1


def test_complete_submission_requires_exact_archive_path_field_per_index_line(
    tmp_path: Path,
) -> None:
    accession = "0000123456-26-000001"
    archive_path = f"edgar/data/123456/{accession}.txt"
    daily_url = "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR2/form.20260630.idx"
    embedded_only = f"4 issuer 123456 2026-06-30 {archive_path}.backup\n".encode("ascii")
    opener = FakeOpener(
        FakeResponse(embedded_only, url=daily_url, content_type="text/plain")
    )
    client = _client(tmp_path, opener)
    receipt = client.fetch_daily_form_index("2026-06-30")

    assert (
        _error_code(
            lambda: client.fetch_complete_submission(
                123456,
                accession,
                daily_index_receipt=receipt,
            )
        )
        == "sec_archive_path_evidence_missing"
    )
    assert len(opener.requests) == 1


def test_non_https_nonstandard_port_userinfo_fragment_and_wrong_path_fail() -> None:
    html = '<a href="https://www.sec.gov:444/files/2026q2_form345.zip">bad</a>'
    assert _error_code(lambda: parse_insider_quarter_catalog(html)) == "sec_url_not_allowed"
    html = '<a href="https://user@www.sec.gov/files/2026q2_form345.zip">bad</a>'
    assert _error_code(lambda: parse_insider_quarter_catalog(html)) == "sec_url_not_allowed"
    html = '<a href="https://www.sec.gov/files/2026q2_form345.zip#part">bad</a>'
    assert _error_code(lambda: parse_insider_quarter_catalog(html)) == "sec_url_not_allowed"

    client = SecEdgarClient.__new__(SecEdgarClient)
    assert (
        _error_code(
            lambda: SecEdgarClient._fetch(
                client,
                "https://www.sec.gov/files/wrong.zip",
                expected_content_types=("application/zip",),
                source_kind="edgar_submissions_bulk_zip",
            )
        )
        == "sec_source_path_not_allowed"
    )


def test_quarantine_files_remain_owned_by_current_user(tmp_path: Path) -> None:
    opener = FakeOpener(FakeResponse(ZIP_BODY, url=SEC_SUBMISSIONS_BULK_URL))
    client = _client(tmp_path, opener)
    receipt = client.fetch_submissions_bulk()
    paths = [
        client.quarantine,
        client.objects,
        client.source_versions,
        client.quarantine / "locks",
        client.quarantine / receipt["object_path"],
        next(client.source_versions.glob("*.json")),
    ]
    assert all(path.lstat().st_uid == os.getuid() for path in paths)
