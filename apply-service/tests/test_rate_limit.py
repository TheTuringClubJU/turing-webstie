"""Group 8: rate limiting tests.

Required in PR feat/apply-email-and-hardening (B3).
Rate limiting is DISABLED by default for all other tests.
This file re-enables it and sets a tiny limit (3 requests per minute)
so tests run quickly without sleeping.

Verifies:
  - Requests under the limit succeed
  - Requests over the limit return 429 in the contract shape
  - Rate limit is per client IP
  - Rate limit resets after the window (using time manipulation, no real sleep)
  - Rate-limited requests write nothing to DB or storage
  - Health endpoint is NOT rate limited
  - Spoofed X-Forwarded-For header cannot bypass the limit
"""

import pytest
from conftest import make_pdf, valid_payload

# ---------------------------------------------------------------------------
# Skip whole module if app/main.py isn't ready
# ---------------------------------------------------------------------------


def _app_available() -> bool:
    try:
        import app.main  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B3 PR)"
)

ENDPOINT = "/api/v1/applications"
VALID_RESUME = ("resume.pdf", make_pdf(1024), "application/pdf")

# Rate limit for these tests: 3 requests per minute.
# The conftest autouse fixture sets RATE_LIMIT_ENABLED=false;
# tests here override it to 'true' and set a small limit.
RATE_LIMIT = 3


@pytest.fixture(autouse=True)
def enable_rate_limiting(monkeypatch):
    """Enable rate limiting with a small window just for this test module."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", str(RATE_LIMIT))


def post_form(client, payload=None, headers=None):
    payload = payload or valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", VALID_RESUME)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files, headers=headers or {})


# ===========================================================================
# Basic rate limit behaviour
# ===========================================================================


def test_requests_under_limit_succeed(client):
    """Requests up to the limit must all succeed."""
    for _ in range(RATE_LIMIT):
        response = post_form(client, valid_payload(usn=f"RATEOK{_:03}"))
        assert response.status_code == 201, (
            f"Request {_ + 1} of {RATE_LIMIT} failed: {response.status_code}"
        )


def test_request_over_limit_returns_429_contract_shape(client):
    """The (RATE_LIMIT + 1)th request from the same IP must return 429."""
    for i in range(RATE_LIMIT):
        post_form(client, valid_payload(usn=f"RATELIM{i:03}"))

    response = post_form(client, valid_payload(usn="RATELIMOVER"))
    assert response.status_code == 429
    body = response.json()
    assert body.get("error") == "rate_limited", (
        f"Expected error='rate_limited', got: {body}"
    )
    assert "message" in body


def test_rate_limit_is_per_client_ip(client):
    """Different client IPs must have independent rate limit counters."""
    # Exhaust the limit for IP A
    for i in range(RATE_LIMIT):
        post_form(client, valid_payload(usn=f"IPA{i:03}"),
                  headers={"X-Real-IP": "1.2.3.4"})

    # A request from a different IP must still succeed
    response = post_form(client, valid_payload(usn="IPB001"),
                         headers={"X-Real-IP": "5.6.7.8"})
    assert response.status_code == 201, (
        "Different IP should not be rate-limited by another IP's counter"
    )


def test_rate_limit_resets_after_window(client, monkeypatch):
    """After the rate-limit window expires, the counter resets and requests succeed again.

    We manipulate time rather than sleeping to keep tests fast.
    """
    try:
        import time as _time

        from slowapi.util import get_remote_address  # noqa: F401

        # Exhaust the limit
        for i in range(RATE_LIMIT):
            post_form(client, valid_payload(usn=f"WINTEST{i:03}"))

        # This request must be rate-limited
        response = post_form(client, valid_payload(usn="WINTESTOVER"))
        assert response.status_code == 429

        # Advance time by 61 seconds (beyond the 1-minute window)
        original_time = _time.time
        monkeypatch.setattr(_time, "time", lambda: original_time() + 61)

        # Should succeed now that the window has reset
        response = post_form(client, valid_payload(usn="WINTESTRESET"))
        assert response.status_code == 201, (
            "Expected success after rate limit window reset"
        )
    except ImportError:
        pytest.skip("slowapi not available")


def test_rate_limited_request_writes_nothing(client, fake_storage, fake_email, conn):
    """A rate-limited request must not create any DB row, storage object, or email."""
    for i in range(RATE_LIMIT):
        post_form(client, valid_payload(usn=f"WRITECHK{i:03}"))

    uploads_before = len(fake_storage.upload_calls)
    emails_before = len(fake_email.calls)
    count_before = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]

    post_form(client, valid_payload(usn="WRITECHKOVER"))

    assert len(fake_storage.upload_calls) == uploads_before, "Storage was called for rate-limited request"
    assert len(fake_email.calls) == emails_before,           "Email was called for rate-limited request"
    count_after = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]
    assert count_after == count_before, "DB row created for rate-limited request"


# ===========================================================================
# Health endpoint exemption
# ===========================================================================


def test_health_endpoint_is_not_rate_limited(client):
    """The /health endpoint must never be rate-limited, even after many requests."""
    for _ in range(RATE_LIMIT * 3):
        response = client.get("/api/v1/health")
        assert response.status_code == 200, (
            f"Health endpoint returned {response.status_code} after {_ + 1} requests"
        )


# ===========================================================================
# Header spoofing cannot bypass the limit
# ===========================================================================


def test_spoofed_forwarded_header_does_not_bypass_limit(client):
    """X-Forwarded-For header must not be trusted to bypass rate limiting."""
    # Exhaust the limit from the test client's default IP
    for i in range(RATE_LIMIT):
        post_form(client, valid_payload(usn=f"SPOOF{i:03}"))

    # Attempt to bypass by spoofing X-Forwarded-For
    response = post_form(
        client,
        valid_payload(usn="SPOOFBYPASS"),
        headers={"X-Forwarded-For": "203.0.113.99"},  # random "different" IP
    )
    # Must still be rate-limited — the app should use X-Real-IP or the actual
    # connection IP, not blindly trust X-Forwarded-For
    assert response.status_code == 429, (
        "Spoofed X-Forwarded-For header bypassed the rate limit"
    )
