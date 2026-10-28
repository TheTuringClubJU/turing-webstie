"""B3 per-client application-submission rate limiting."""

import psycopg
from api_helpers import post_application
from fastapi.testclient import TestClient


def _count(database_url):
    with psycopg.connect(database_url) as connection:
        return connection.execute("SELECT count(*) FROM applications").fetchone()[0]


def _limited_client(db_client, client_ip="192.0.2.1"):
    db_client.app.state.settings = db_client.app.state.settings.model_copy(
        update={
            "rate_limit_enabled": True,
            "rate_limit_requests": 2,
            "rate_limit_window_seconds": 60,
        }
    )
    class ClientAddressOverride:
        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                scope = {**scope, "client": (client_ip, 12345)}
            await db_client.app(scope, receive, send)

    return TestClient(ClientAddressOverride())


def _unique_payload(usn):
    return {
        "name": "Asha Rao",
        "usn": usn,
        "personal_email": f"{usn.lower()}@example.com",
        "mobile": "9876543210",
        "domains": ["technology"],
    }


def test_requests_under_limit_succeed(db_client):
    with _limited_client(db_client) as client:
        first = post_application(client, _unique_payload("ABC123"))
        second = post_application(client, _unique_payload("DEF456"))

    assert first.status_code == 201
    assert second.status_code == 201


def test_request_over_limit_returns_429_contract_shape(db_client):
    with _limited_client(db_client) as client:
        post_application(client, _unique_payload("ABC123"))
        post_application(client, _unique_payload("DEF456"))
        response = post_application(client, _unique_payload("GHI789"))

    assert response.status_code == 429
    assert response.json() == {
        "error": "rate_limited",
        "message": "Too many requests. Please try again later.",
    }


def test_rate_limit_is_per_client_ip(db_client):
    with _limited_client(db_client, "192.0.2.1") as first_client:
        assert post_application(
            first_client, _unique_payload("ABC123")
        ).status_code == 201
        assert post_application(
            first_client, _unique_payload("DEF456")
        ).status_code == 201
        assert post_application(
            first_client, _unique_payload("GHI789")
        ).status_code == 429

    with _limited_client(db_client, "192.0.2.2") as second_client:
        assert post_application(
            second_client, _unique_payload("JKL012")
        ).status_code == 201


def test_rate_limit_resets_after_window(db_client, monkeypatch):
    from app.services import rate_limit

    current_time = [100.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: current_time[0])
    with _limited_client(db_client) as client:
        assert post_application(
            client, _unique_payload("ABC123")
        ).status_code == 201
        assert post_application(
            client, _unique_payload("DEF456")
        ).status_code == 201
        current_time[0] = 160.0
        response = post_application(client, _unique_payload("GHI789"))

    assert response.status_code == 201


def test_rate_limited_request_writes_nothing(db_client, db_url, fake_storage):
    with _limited_client(db_client) as client:
        post_application(client, _unique_payload("ABC123"))
        post_application(client, _unique_payload("DEF456"))
        upload_count = len(fake_storage.uploads)
        response = post_application(client, _unique_payload("GHI789"))

    assert response.status_code == 429
    assert _count(db_url) == 2
    assert len(fake_storage.uploads) == upload_count


def test_health_endpoint_is_not_rate_limited(db_client):
    with _limited_client(db_client) as client:
        post_application(client, _unique_payload("ABC123"))
        post_application(client, _unique_payload("DEF456"))
        post_application(client, _unique_payload("GHI789"))
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_spoofed_forwarded_header_does_not_bypass_limit(db_client):
    with _limited_client(db_client) as client:
        post_application(client, _unique_payload("ABC123"))
        post_application(client, _unique_payload("DEF456"))
        response = post_application(
            client,
            _unique_payload("GHI789"),
            headers={"X-Forwarded-For": "198.51.100.77"},
        )

    assert response.status_code == 429
