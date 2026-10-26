from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import stat
import tempfile
import time
from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import UTC, date, datetime
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

SEC_CATALOG_URL = (
    "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
)
SEC_SUBMISSIONS_BULK_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
SEC_OWNERSHIP_ATOM_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_ALLOWED_HOSTS = frozenset({"sec.gov", "www.sec.gov", "data.sec.gov"})
SEC_DEFAULT_REQUESTS_PER_SECOND = 1.0
SEC_POLICY_MAX_REQUESTS_PER_SECOND = 10.0
SEC_CLIENT_MAX_REQUESTS_PER_SECOND = 1.0
SEC_DEFAULT_MAX_RESPONSE_BYTES = 2_000_000_000
SEC_USER_AGENT_ENV = "USFDDK_SEC_USER_AGENT"
SEC_CLIENT_CONTRACT_VERSION = "round41-sec-edgar-isolated-fetch-prototype-v1"

SEC_SOURCE_CONTENT_TYPES = {
    "insider_transactions_catalog": frozenset({"text/html"}),
    "insider_transactions_quarter_zip": frozenset(
        {"application/zip", "application/octet-stream"}
    ),
    "edgar_submissions_bulk_zip": frozenset(
        {"application/zip", "application/octet-stream"}
    ),
    "edgar_daily_form_index": frozenset(
        {"text/plain", "application/octet-stream"}
    ),
    "edgar_complete_submission": frozenset(
        {"text/plain", "application/octet-stream"}
    ),
    "edgar_latest_ownership_atom": frozenset(
        {"application/atom+xml", "application/xml", "text/xml"}
    ),
}

SEC_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "client_contract_version",
        "source_kind",
        "requested_url",
        "final_url",
        "request_started_at",
        "http_status",
        "content_type",
        "content_length_header",
        "byte_count",
        "body_sha256",
        "object_path",
        "first_observed_at",
        "first_observed_basis",
        "observation_mode",
        "first_observed_external_anchor_present",
        "receipt_externally_anchored",
        "public_at",
        "known_at",
        "http_date",
        "etag",
        "last_modified",
        "cache_control",
        "user_agent_contact_declared",
        "sec_policy_ceiling_requests_per_second",
        "configured_requests_per_second",
        "local_shared_rate_lock",
        "cross_machine_global_rate_limit_proven",
        "single_designated_collector_required",
        "http_attempt_ledger_complete",
        "redirect_chain_fully_recorded",
        "encrypted_quarantine_verified",
        "form4_admission_gate_passed",
        "strategy_defined_or_run",
        "paper_authorized",
        "real_money_action_usd",
        "receipt_sha256",
    }
)

_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{1,10}$")
_QUARTER_ARCHIVE = re.compile(r"(?P<year>20\d{2})q(?P<quarter>[1-4])_form345\.zip$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class _Headers(Protocol):
    def get(self, name: str, default: str | None = None) -> str | None: ...


class _Response(Protocol):
    status: int
    headers: _Headers | Mapping[str, str] | Message

    def read(self, size: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> _Response: ...

    def __exit__(self, *args: object) -> None: ...


class SecEdgarClientError(RuntimeError):
    """Fail-closed SEC client error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise SecEdgarClientError(code, detail)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc_timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, str) or not value:
        _fail(code, "timestamp is missing")
    if not value.endswith("Z"):
        _fail(code, "timestamp is not canonical UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, "timestamp is not ISO-8601")
    normalized = parsed.astimezone(UTC)
    canonical = normalized.isoformat().replace("+00:00", "Z")
    if parsed.utcoffset() is None or canonical != value:
        _fail(code, "timestamp is not canonical UTC")
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: dict[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_user_agent(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.strip()) < 12
        or "\n" in value
        or "\r" in value
        or _EMAIL.search(value) is None
    ):
        _fail(
            "sec_user_agent_contact_missing",
            "User-Agent must name the research client and include a contact email",
        )
    return value.strip()


def _validate_url(value: str) -> str:
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        _fail("sec_url_not_allowed", "request URL has an invalid port")
    if (
        parsed.scheme != "https"
        or parsed.hostname not in SEC_ALLOWED_HOSTS
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        _fail("sec_url_not_allowed", "request URL is outside the official SEC allowlist")
    return value


def _validate_source_url(value: str, source_kind: str) -> str:
    url = _validate_url(value)
    parsed = urlparse(url)
    path = parsed.path
    valid = {
        "insider_transactions_catalog": path.rstrip("/")
        == "/data-research/sec-markets-data/insider-transactions-data-sets",
        "insider_transactions_quarter_zip": _QUARTER_ARCHIVE.search(path) is not None,
        "edgar_submissions_bulk_zip": path
        == "/Archives/edgar/daily-index/bulkdata/submissions.zip",
        "edgar_daily_form_index": re.fullmatch(
            r"/Archives/edgar/daily-index/20\d{2}/QTR[1-4]/form\.20\d{6}\.idx",
            path,
        )
        is not None,
        "edgar_complete_submission": re.fullmatch(
            r"/Archives/edgar/data/\d{1,10}/\d{18}/\d{10}-\d{2}-\d{6}\.txt",
            path,
        )
        is not None,
        "edgar_latest_ownership_atom": path == "/cgi-bin/browse-edgar",
    }.get(source_kind, False)
    if source_kind == "edgar_latest_ownership_atom":
        query = parse_qs(parsed.query, keep_blank_values=True)
        try:
            count = int(query.get("count", [""])[0])
        except (TypeError, ValueError):
            count = 0
        valid = bool(
            valid
            and query
            == {
                "action": ["getcurrent"],
                "owner": ["only"],
                "count": [str(count)],
                "output": ["atom"],
            }
            and 1 <= count <= 100
        )
    elif parsed.query:
        valid = False
    if not valid:
        _fail("sec_source_path_not_allowed", f"unexpected path for {source_kind}")
    return url


class _AllowlistedSecRedirectHandler(HTTPRedirectHandler):
    def redirect_request(  # type: ignore[no-untyped-def]
        self, request, file_pointer, code, message, headers, new_url
    ):
        _validate_url(new_url)
        _fail(
            "sec_redirect_not_allowed",
            "prototype refuses every redirect because a source-specific hop ledger is absent",
        )


def _header(headers: _Headers | Mapping[str, str] | Message, name: str) -> str | None:
    value = headers.get(name)
    return str(value) if value is not None else None


def _atomic_json_create(path: Path, payload: dict[str, Any]) -> bool:
    rendered = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        return False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return True


def _validate_owner_file(path: Path, *, code: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, type(exc).__name__)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
    ):
        _fail(code, "file must be an owner-only regular file with one link")
    return metadata


def _validate_owner_directory(path: Path, *, code: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, type(exc).__name__)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.getuid()
    ):
        _fail(code, "directory must be owner-only and owned by the current user")
    return metadata


def _receipt_hash(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("receipt_sha256", None)
    return _canonical_sha256(canonical)


class _QuarterCatalogParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.quarters: dict[tuple[int, int], str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = next((value for name, value in attrs if name.lower() == "href"), None)
        if href is None:
            return
        url = urljoin(self.base_url, href)
        match = _QUARTER_ARCHIVE.search(urlparse(url).path)
        if match is None:
            return
        _validate_url(url)
        key = (int(match.group("year")), int(match.group("quarter")))
        existing = self.quarters.get(key)
        if existing is not None and existing != url:
            _fail("sec_catalog_duplicate_quarter", f"catalog has two URLs for {key}")
        self.quarters[key] = url


def parse_insider_quarter_catalog(
    html: str,
    *,
    base_url: str = SEC_CATALOG_URL,
) -> dict[tuple[int, int], str]:
    parser = _QuarterCatalogParser(_validate_url(base_url))
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, TypeError) as exc:
        _fail("sec_catalog_parse_failed", type(exc).__name__)
    if not parser.quarters:
        _fail("sec_catalog_parse_failed", "catalog contains no quarterly Form 345 ZIP")
    return dict(sorted(parser.quarters.items()))


class SecEdgarClient:
    """Owner-only SEC fetcher prototype; never authorizes collection or a strategy.

    The rate lock coordinates processes sharing one quarantine directory. It does not
    prove a cross-machine global limiter and therefore cannot by itself pass Round 40
    disclosure readiness gate 05. File modes do not prove quarantine encryption or
    pass gate 06. The caller must designate one collector host; receipts deliberately
    keep the Form 4-specific admission state false.
    """

    def __init__(
        self,
        quarantine: str | Path,
        *,
        repository_root: str | Path,
        user_agent: str | None = None,
        requests_per_second: float = SEC_DEFAULT_REQUESTS_PER_SECOND,
        timeout_seconds: float = 60.0,
        max_response_bytes: int = SEC_DEFAULT_MAX_RESPONSE_BYTES,
        opener: Callable[[Request, float], _Response] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], str] = _utc_now,
    ):
        self.repository_root = Path(repository_root).resolve()
        configured_user_agent = user_agent or os.environ.get(SEC_USER_AGENT_ENV, "")
        self.user_agent = _validate_user_agent(configured_user_agent)
        if (
            isinstance(requests_per_second, bool)
            or not isinstance(requests_per_second, (int, float))
            or not 0 < float(requests_per_second) <= SEC_CLIENT_MAX_REQUESTS_PER_SECOND
        ):
            _fail("sec_rate_limit_invalid", "this collector must be >0 and <=1 rps")
        if timeout_seconds <= 0:
            _fail("sec_timeout_invalid", "timeout must be positive")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes <= 0
        ):
            _fail("sec_response_limit_invalid", "response byte ceiling must be positive")
        self.quarantine = self._prepare_quarantine(Path(quarantine))
        self.requests_per_second = float(requests_per_second)
        self.timeout_seconds = float(timeout_seconds)
        self.max_response_bytes = max_response_bytes
        self._opener = opener or self._default_open
        self._clock = clock
        self._sleeper = sleeper
        self._now = now
        self._catalog_cache: dict[str, Any] | None = None

    @staticmethod
    def _default_open(request: Request, timeout: float) -> _Response:
        opener = build_opener(_AllowlistedSecRedirectHandler())
        return opener.open(request, timeout=timeout)

    def _prepare_quarantine(self, value: Path) -> Path:
        if not value.is_absolute():
            _fail("sec_quarantine_path_invalid", "quarantine path must be absolute")
        if value.is_symlink():
            _fail("sec_quarantine_path_invalid", "quarantine cannot be a symlink")
        try:
            resolved = value.resolve(strict=False)
        except OSError as exc:
            _fail("sec_quarantine_path_invalid", type(exc).__name__)
        if resolved == self.repository_root or _inside(resolved, self.repository_root):
            _fail("sec_quarantine_inside_repository", "raw SEC data must remain outside Git")
        if not resolved.exists():
            resolved.mkdir(parents=True, mode=0o700)
        _validate_owner_directory(resolved, code="sec_quarantine_not_owner_only")
        for name in ("objects", "source_versions", "locks"):
            child = resolved / name
            if not child.exists():
                child.mkdir(mode=0o700)
            _validate_owner_directory(child, code="sec_quarantine_not_owner_only")
        return resolved

    @property
    def objects(self) -> Path:
        return self.quarantine / "objects"

    @property
    def source_versions(self) -> Path:
        return self.quarantine / "source_versions"

    @property
    def circuit_breaker(self) -> Path:
        return self.quarantine / "locks/sec-circuit-breaker.json"

    def _read_json_owner_file(self, path: Path, *, code: str) -> dict[str, Any]:
        _validate_owner_file(path, code=code)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _fail(code, type(exc).__name__)
        if not isinstance(payload, dict):
            _fail(code, "JSON receipt must be an object")
        return payload

    def _check_circuit_breaker(self) -> None:
        if not os.path.lexists(self.circuit_breaker):
            return
        payload = self._read_json_owner_file(
            self.circuit_breaker, code="sec_circuit_breaker_invalid"
        )
        if payload.get("receipt_sha256") != _receipt_hash(payload):
            _fail("sec_circuit_breaker_invalid", "circuit breaker receipt drifted")
        reason = payload.get("reason_code")
        _fail(
            "sec_circuit_breaker_open",
            f"automated SEC access stopped after {reason or 'unknown error'}",
        )

    def _trip_circuit_breaker(self, reason_code: str, detail: str) -> None:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "client_contract_version": SEC_CLIENT_CONTRACT_VERSION,
            "status": "manual_review_required_before_any_further_sec_access",
            "reason_code": reason_code,
            "detail": detail,
            "tripped_at": self._now(),
            "automatic_retry_allowed": False,
            "strategy_defined_or_run": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        }
        payload["receipt_sha256"] = _receipt_hash(payload)
        _atomic_json_create(self.circuit_breaker, payload)

    def _wait_rate_limit(self) -> None:
        lock_path = self.quarantine / "locks/sec-global-rate.lock"
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            _fail("sec_rate_lock_invalid", type(exc).__name__)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1
            ):
                _fail("sec_rate_lock_invalid", "rate lock is not a private regular file")
            with os.fdopen(descriptor, "r+", encoding="ascii", closefd=False) as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                raw = handle.read().strip()
                try:
                    previous = float(raw) if raw else 0.0
                except ValueError:
                    _fail("sec_rate_lock_corrupt", "shared rate timestamp is invalid")
                if not math.isfinite(previous):
                    _fail("sec_rate_lock_corrupt", "shared rate timestamp is not finite")
                current = float(self._clock())
                if not math.isfinite(current):
                    _fail("sec_rate_clock_invalid", "monotonic clock is not finite")
                if current < previous:
                    _fail("sec_rate_clock_regressed", "monotonic clock moved backwards")
                interval = 1.0 / self.requests_per_second
                for _ in range(3):
                    wait = max(0.0, interval - (current - previous))
                    if not wait:
                        break
                    self._sleeper(wait)
                    current = float(self._clock())
                    if not math.isfinite(current):
                        _fail("sec_rate_clock_invalid", "monotonic clock is not finite")
                    if current < previous:
                        _fail("sec_rate_clock_regressed", "monotonic clock moved backwards")
                if current - previous < interval:
                    _fail("sec_rate_sleep_incomplete", "rate interval was not satisfied")
                handle.seek(0)
                handle.truncate()
                handle.write(f"{current:.9f}\n")
                handle.flush()
                os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    def _open_response(self, request: Request) -> _Response:
        try:
            return self._opener(request, self.timeout_seconds)
        except HTTPError as exc:
            if exc.code == 429:
                retry_after = _header(exc.headers, "Retry-After") or "unspecified"
                self._trip_circuit_breaker(
                    "sec_rate_limited_stop", f"HTTP 429; Retry-After={retry_after}"
                )
                _fail("sec_rate_limited_stop", f"HTTP 429; Retry-After={retry_after}")
            if exc.code == 403:
                self._trip_circuit_breaker(
                    "sec_access_forbidden_stop", "HTTP 403; stop all automated access"
                )
                _fail("sec_access_forbidden_stop", "HTTP 403; stop all automated access")
            _fail("sec_http_error", f"HTTP {exc.code}")
        except (URLError, TimeoutError, OSError) as exc:
            _fail("sec_transport_error", type(exc).__name__)

    def _validate_cached_receipt(
        self,
        path: Path,
        *,
        requested_url: str,
        source_kind: str,
        body_sha256: str,
    ) -> dict[str, Any]:
        receipt = self._read_json_owner_file(path, code="sec_cached_receipt_invalid")
        if receipt.get("receipt_sha256") != _receipt_hash(receipt):
            _fail("sec_cached_receipt_invalid", "source receipt hash drifted")
        if set(receipt) != SEC_RECEIPT_KEYS:
            _fail("sec_cached_receipt_invalid", "source receipt schema is not exact")
        started = _parse_utc_timestamp(
            receipt.get("request_started_at"), code="sec_cached_receipt_invalid"
        )
        observed = _parse_utc_timestamp(
            receipt.get("first_observed_at"), code="sec_cached_receipt_invalid"
        )
        allowed_content_types = SEC_SOURCE_CONTENT_TYPES.get(source_kind)
        byte_count = receipt.get("byte_count")
        content_length = receipt.get("content_length_header")
        content_type = receipt.get("content_type")
        configured_rate = receipt.get("configured_requests_per_second")
        header_values = tuple(
            receipt.get(key)
            for key in ("http_date", "etag", "last_modified", "cache_control")
        )
        if (
            type(receipt.get("schema_version")) is not int
            or receipt.get("schema_version") != 1
            or receipt.get("client_contract_version") != SEC_CLIENT_CONTRACT_VERSION
            or receipt.get("source_kind") != source_kind
            or receipt.get("requested_url") != requested_url
            or receipt.get("final_url") != requested_url
            or type(receipt.get("http_status")) is not int
            or receipt.get("http_status") != 200
            or allowed_content_types is None
            or content_type not in allowed_content_types
            or type(byte_count) is not int
            or byte_count < 0
            or (
                content_length is not None
                and (type(content_length) is not int or content_length != byte_count)
            )
            or any(value is not None and not isinstance(value, str) for value in header_values)
            or not isinstance(body_sha256, str)
            or _SHA256.fullmatch(body_sha256) is None
            or receipt.get("body_sha256") != body_sha256
            or receipt.get("object_path") != f"objects/{body_sha256}.bin"
            or observed < started
            or receipt.get("first_observed_basis")
            != "local_full_body_completion_only"
            or receipt.get("observation_mode")
            != "engineering_fetch_not_contemporaneous_evidence"
            or receipt.get("first_observed_external_anchor_present") is not False
            or receipt.get("receipt_externally_anchored") is not False
            or receipt.get("public_at") is not None
            or receipt.get("known_at") is not None
            or receipt.get("user_agent_contact_declared") is not True
            or receipt.get("sec_policy_ceiling_requests_per_second")
            != SEC_POLICY_MAX_REQUESTS_PER_SECOND
            or isinstance(configured_rate, bool)
            or not isinstance(configured_rate, (int, float))
            or not math.isfinite(float(configured_rate))
            or not 0 < float(configured_rate) <= SEC_CLIENT_MAX_REQUESTS_PER_SECOND
            or receipt.get("local_shared_rate_lock") is not True
            or receipt.get("cross_machine_global_rate_limit_proven") is not False
            or receipt.get("single_designated_collector_required") is not True
            or receipt.get("http_attempt_ledger_complete") is not False
            or receipt.get("redirect_chain_fully_recorded") is not False
            or receipt.get("encrypted_quarantine_verified") is not False
            or receipt.get("form4_admission_gate_passed") is not False
            or receipt.get("strategy_defined_or_run") is not False
            or receipt.get("paper_authorized") is not False
            or type(receipt.get("real_money_action_usd")) is not int
            or receipt.get("real_money_action_usd") != 0
        ):
            _fail("sec_cached_receipt_invalid", "source receipt content drifted")
        _validate_source_url(str(receipt.get("final_url", "")), source_kind)
        object_path = self.objects / f"{body_sha256}.bin"
        metadata = _validate_owner_file(object_path, code="sec_cached_object_invalid")
        if metadata.st_size != byte_count:
            _fail("sec_cached_receipt_invalid", "receipt byte count differs from object")
        return receipt

    def _require_stored_receipt(
        self,
        supplied: Mapping[str, Any],
        *,
        expected_source_kind: str,
        missing_code: str = "sec_cached_receipt_invalid",
    ) -> dict[str, Any]:
        candidate = dict(supplied)
        requested_url = candidate.get("requested_url")
        body_sha256 = candidate.get("body_sha256")
        if (
            set(candidate) != SEC_RECEIPT_KEYS
            or candidate.get("source_kind") != expected_source_kind
            or not isinstance(requested_url, str)
            or not isinstance(body_sha256, str)
            or _SHA256.fullmatch(body_sha256) is None
        ):
            _fail(missing_code, "receipt identity is incomplete")
        _validate_source_url(requested_url, expected_source_kind)
        receipt_key = _canonical_sha256(
            {
                "source_kind": expected_source_kind,
                "requested_url": requested_url,
                "body_sha256": body_sha256,
            }
        )
        receipt_path = self.source_versions / f"{receipt_key}.json"
        if not receipt_path.exists():
            _fail(missing_code, "receipt is not stored by this client")
        stored = self._validate_cached_receipt(
            receipt_path,
            requested_url=requested_url,
            source_kind=expected_source_kind,
            body_sha256=body_sha256,
        )
        if stored != candidate:
            _fail(missing_code, "supplied receipt differs from stored receipt")
        return stored

    def _fetch(
        self,
        url: str,
        *,
        expected_content_types: tuple[str, ...],
        source_kind: str,
    ) -> dict[str, Any]:
        requested_url = _validate_source_url(url, source_kind)
        source_content_types = SEC_SOURCE_CONTENT_TYPES.get(source_kind)
        if (
            source_content_types is None
            or frozenset(expected_content_types) != source_content_types
        ):
            _fail("sec_source_contract_invalid", "content types do not match source contract")
        self._check_circuit_breaker()
        request_started_at = self._now()
        started = _parse_utc_timestamp(
            request_started_at, code="sec_observation_clock_invalid"
        )
        self._wait_rate_limit()
        request = Request(
            requested_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
                "Connection": "close",
            },
            method="GET",
        )
        response = self._open_response(request)
        temporary_path: Path | None = None
        try:
            with response:
                status = int(getattr(response, "status", 0))
                if status == 429:
                    retry_after = _header(response.headers, "Retry-After") or "unspecified"
                    self._trip_circuit_breaker(
                        "sec_rate_limited_stop",
                        f"HTTP 429; Retry-After={retry_after}",
                    )
                    _fail("sec_rate_limited_stop", f"HTTP 429; Retry-After={retry_after}")
                if status == 403:
                    self._trip_circuit_breaker(
                        "sec_access_forbidden_stop",
                        "HTTP 403; stop all automated access",
                    )
                    _fail("sec_access_forbidden_stop", "HTTP 403; stop all automated access")
                if status != 200:
                    _fail("sec_http_error", f"HTTP {status}")
                final_url = _validate_source_url(response.geturl(), source_kind)
                if final_url != requested_url:
                    _fail("sec_redirect_not_allowed", "final URL differs from requested URL")
                content_type = (
                    (_header(response.headers, "Content-Type") or "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if content_type not in source_content_types:
                    _fail(
                        "sec_content_type_invalid",
                        f"{source_kind} returned {content_type or 'missing'}",
                    )
                content_length = _header(response.headers, "Content-Length")
                if content_length:
                    try:
                        announced = int(content_length)
                    except ValueError:
                        _fail("sec_content_length_invalid", "Content-Length is not an integer")
                    if announced < 0 or announced > self.max_response_bytes:
                        _fail("sec_response_too_large", "announced response exceeds byte ceiling")
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=".sec-object-", suffix=".tmp", dir=self.objects
                )
                temporary_path = Path(temporary_name)
                digest = hashlib.sha256()
                byte_count = 0
                prefix = bytearray()
                with os.fdopen(descriptor, "wb") as handle:
                    os.fchmod(handle.fileno(), 0o600)
                    while chunk := response.read(1024 * 1024):
                        if not isinstance(chunk, bytes):
                            _fail("sec_transport_error", "response body was not bytes")
                        byte_count += len(chunk)
                        if byte_count > self.max_response_bytes:
                            _fail("sec_response_too_large", "response exceeded byte ceiling")
                        digest.update(chunk)
                        handle.write(chunk)
                        if len(prefix) < 4:
                            prefix.extend(chunk[: 4 - len(prefix)])
                    handle.flush()
                    os.fsync(handle.fileno())
                if content_length and byte_count != announced:
                    _fail("sec_content_length_invalid", "body length differs from header")
                if source_kind in {
                    "insider_transactions_quarter_zip",
                    "edgar_submissions_bulk_zip",
                } and bytes(prefix) not in {b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"}:
                    _fail("sec_zip_magic_invalid", "ZIP response has no valid PK signature")
                body_sha256 = digest.hexdigest()
                object_path = self.objects / f"{body_sha256}.bin"
                if object_path.exists():
                    _validate_owner_file(object_path, code="sec_cached_object_invalid")
                    if _sha256_file(object_path) != body_sha256:
                        _fail(
                            "sec_cached_object_invalid", "existing content-addressed object drifted"
                        )
                    temporary_path.unlink()
                else:
                    try:
                        os.link(temporary_path, object_path, follow_symlinks=False)
                    except FileExistsError:
                        pass
                    temporary_path.unlink()
                    _validate_owner_file(object_path, code="sec_cached_object_invalid")
                    if _sha256_file(object_path) != body_sha256:
                        _fail("sec_cached_object_invalid", "concurrent content object drifted")
                temporary_path = None
                receipt_key = _canonical_sha256(
                    {
                        "source_kind": source_kind,
                        "requested_url": requested_url,
                        "body_sha256": body_sha256,
                    }
                )
                receipt_path = self.source_versions / f"{receipt_key}.json"
                if receipt_path.exists():
                    return self._validate_cached_receipt(
                        receipt_path,
                        requested_url=requested_url,
                        source_kind=source_kind,
                        body_sha256=body_sha256,
                    )
                first_observed_at = self._now()
                observed = _parse_utc_timestamp(
                    first_observed_at, code="sec_observation_clock_invalid"
                )
                if observed < started:
                    _fail(
                        "sec_observation_clock_invalid",
                        "first observation precedes request start",
                    )
                receipt = {
                    "schema_version": 1,
                    "client_contract_version": SEC_CLIENT_CONTRACT_VERSION,
                    "source_kind": source_kind,
                    "requested_url": requested_url,
                    "final_url": final_url,
                    "request_started_at": request_started_at,
                    "http_status": status,
                    "content_type": content_type,
                    "content_length_header": int(content_length) if content_length else None,
                    "byte_count": byte_count,
                    "body_sha256": body_sha256,
                    "object_path": f"objects/{body_sha256}.bin",
                    "first_observed_at": first_observed_at,
                    "first_observed_basis": "local_full_body_completion_only",
                    "observation_mode": (
                        "engineering_fetch_not_contemporaneous_evidence"
                    ),
                    "first_observed_external_anchor_present": False,
                    "receipt_externally_anchored": False,
                    "public_at": None,
                    "known_at": None,
                    "http_date": _header(response.headers, "Date"),
                    "etag": _header(response.headers, "ETag"),
                    "last_modified": _header(response.headers, "Last-Modified"),
                    "cache_control": _header(response.headers, "Cache-Control"),
                    "user_agent_contact_declared": True,
                    "sec_policy_ceiling_requests_per_second": (SEC_POLICY_MAX_REQUESTS_PER_SECOND),
                    "configured_requests_per_second": self.requests_per_second,
                    "local_shared_rate_lock": True,
                    "cross_machine_global_rate_limit_proven": False,
                    "single_designated_collector_required": True,
                    "http_attempt_ledger_complete": False,
                    "redirect_chain_fully_recorded": False,
                    "encrypted_quarantine_verified": False,
                    "form4_admission_gate_passed": False,
                    "strategy_defined_or_run": False,
                    "paper_authorized": False,
                    "real_money_action_usd": 0,
                }
                receipt["receipt_sha256"] = _receipt_hash(receipt)
                if _atomic_json_create(receipt_path, receipt):
                    return receipt
                return self._validate_cached_receipt(
                    receipt_path,
                    requested_url=requested_url,
                    source_kind=source_kind,
                    body_sha256=body_sha256,
                )
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _stored_object_bytes(self, receipt: Mapping[str, Any]) -> bytes:
        digest = receipt.get("body_sha256")
        relative = receipt.get("object_path")
        byte_count = receipt.get("byte_count")
        if (
            not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
            or relative != f"objects/{digest}.bin"
            or type(byte_count) is not int
            or byte_count < 0
        ):
            _fail("sec_cached_receipt_invalid", "receipt does not bind one object")
        path = self.quarantine / relative
        metadata = _validate_owner_file(path, code="sec_cached_object_invalid")
        if metadata.st_size != byte_count:
            _fail("sec_cached_object_invalid", "content object size differs from receipt")
        body = path.read_bytes()
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != digest:
            _fail("sec_cached_object_invalid", "content object is missing or changed")
        return body

    def object_bytes(self, receipt: Mapping[str, Any]) -> bytes:
        source_kind = receipt.get("source_kind")
        if not isinstance(source_kind, str) or source_kind not in SEC_SOURCE_CONTENT_TYPES:
            _fail("sec_cached_receipt_invalid", "receipt source kind is invalid")
        stored = self._require_stored_receipt(
            receipt,
            expected_source_kind=source_kind,
        )
        return self._stored_object_bytes(stored)

    def fetch_catalog(self, *, force_refresh: bool = False) -> dict[str, Any]:
        if self._catalog_cache is not None and not force_refresh:
            return deepcopy(self._catalog_cache)
        receipt = self._fetch(
            SEC_CATALOG_URL,
            expected_content_types=("text/html",),
            source_kind="insider_transactions_catalog",
        )
        try:
            html = self.object_bytes(receipt).decode("utf-8")
        except UnicodeDecodeError:
            _fail("sec_catalog_parse_failed", "catalog is not UTF-8")
        quarters = parse_insider_quarter_catalog(html, base_url=receipt["final_url"])
        result = {
            "receipt": receipt,
            "quarters": {f"{year}Q{quarter}": url for (year, quarter), url in quarters.items()},
            "strategy_defined_or_run": False,
        }
        self._catalog_cache = deepcopy(result)
        return result

    def fetch_quarter(self, year: int, quarter: int) -> dict[str, Any]:
        if year < 2006 or quarter not in {1, 2, 3, 4}:
            _fail("sec_quarter_invalid", "Form 345 bulk coverage starts in 2006")
        catalog = self.fetch_catalog()
        key = f"{year}Q{quarter}"
        url = catalog["quarters"].get(key)
        if url is None:
            _fail("sec_quarter_not_published", f"official catalog has no {key}")
        receipt = self._fetch(
            url,
            expected_content_types=("application/zip", "application/octet-stream"),
            source_kind="insider_transactions_quarter_zip",
        )
        return {
            "catalog_receipt_sha256": _canonical_sha256(catalog["receipt"]),
            "quarter": key,
            "receipt": receipt,
            "strategy_defined_or_run": False,
        }

    def fetch_submissions_bulk(self) -> dict[str, Any]:
        return self._fetch(
            SEC_SUBMISSIONS_BULK_URL,
            expected_content_types=("application/zip", "application/octet-stream"),
            source_kind="edgar_submissions_bulk_zip",
        )

    def fetch_daily_form_index(self, session_date: date | str) -> dict[str, Any]:
        if isinstance(session_date, str):
            try:
                parsed = date.fromisoformat(session_date)
            except ValueError:
                _fail("sec_index_date_invalid", "daily index date must be ISO YYYY-MM-DD")
        elif isinstance(session_date, date):
            parsed = session_date
        else:
            _fail("sec_index_date_invalid", "daily index date has an invalid type")
        quarter = (parsed.month - 1) // 3 + 1
        url = (
            "https://www.sec.gov/Archives/edgar/daily-index/"
            f"{parsed.year}/QTR{quarter}/form.{parsed:%Y%m%d}.idx"
        )
        return self._fetch(
            url,
            expected_content_types=("text/plain", "application/octet-stream"),
            source_kind="edgar_daily_form_index",
        )

    def fetch_complete_submission(
        self,
        archive_cik: str | int,
        accession: str,
        *,
        daily_index_receipt: Mapping[str, Any],
    ) -> dict[str, Any]:
        cik = str(archive_cik).strip()
        if _CIK.fullmatch(cik) is None or _ACCESSION.fullmatch(accession) is None:
            _fail("sec_filing_identifier_invalid", "CIK or accession is invalid")
        normalized_cik = str(int(cik))
        stored_index_receipt = self._require_stored_receipt(
            daily_index_receipt,
            expected_source_kind="edgar_daily_form_index",
            missing_code="sec_archive_path_evidence_missing",
        )
        index_body = self._stored_object_bytes(stored_index_receipt).decode("latin-1")
        index_path = f"edgar/data/{normalized_cik}/{accession}.txt"
        exact_path_present = any(
            fields[-1] == index_path
            for line in index_body.splitlines()
            if len(fields := line.split()) >= 2
        )
        if not exact_path_present:
            _fail(
                "sec_archive_path_evidence_missing",
                "daily index does not bind accession to archive CIK",
            )
        accession_directory = accession.replace("-", "")
        url = (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{normalized_cik}/{accession_directory}/{accession}.txt"
        )
        return self._fetch(
            url,
            expected_content_types=("text/plain", "application/octet-stream"),
            source_kind="edgar_complete_submission",
        )

    def poll_ownership_atom(self, *, count: int = 100) -> dict[str, Any]:
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
            _fail("sec_atom_count_invalid", "ownership Atom count must be 1..100")
        query = urlencode(
            {
                "action": "getcurrent",
                "owner": "only",
                "count": count,
                "output": "atom",
            }
        )
        return self._fetch(
            f"{SEC_OWNERSHIP_ATOM_URL}?{query}",
            expected_content_types=("application/atom+xml", "application/xml", "text/xml"),
            source_kind="edgar_latest_ownership_atom",
        )
