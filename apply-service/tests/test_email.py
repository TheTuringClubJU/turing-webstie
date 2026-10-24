"""B3 background confirmation email behavior and failure handling."""

import logging
import time

import psycopg
from api_helpers import post_application
from conftest import valid_payload
from fastapi.testclient import TestClient


def _application(database_url, application_id):
    with psycopg.connect(database_url) as connection:
        return connection.execute(
            """
            SELECT personal_email, college_email, name, confirmation_email_status,
                   confirmation_email_sent_at
            FROM applications WHERE id = %s
            """,
            (application_id,),
        ).fetchone()


def test_confirmation_email_triggered_after_successful_save(
    db_client, db_url, fake_email
):
    response = post_application(db_client)

    assert response.status_code == 201
    row = _application(db_url, response.json()["id"])
    assert row[3] == "sent"
    assert len(fake_email.calls) == 1


def test_email_sent_to_personal_email_only(db_client, fake_email):
    response = post_application(
        db_client,
        {
            **valid_payload(),
            "college_email": "student@college.example",
            "personal_email": "student@personal.example",
        },
    )

    assert response.status_code == 201
    assert fake_email.calls[0][0] == "student@personal.example"
    assert all(call[0] != "student@college.example" for call in fake_email.calls)


def test_email_called_with_normalized_name_and_selected_domains(
    db_client, fake_email
):
    response = post_application(
        db_client,
        {
            **valid_payload(),
            "name": "  Asha Rao ",
            "personal_email": " ASHA@Example.COM ",
            "domains": ["design", "technology"],
        },
    )

    assert response.status_code == 201
    assert fake_email.calls == [
        ("asha@example.com", "Asha Rao", ["design", "technology"])
    ]


def test_email_failure_still_returns_201(db_client, fake_email):
    fake_email.error = RuntimeError("smtp credentials must not be logged")

    response = post_application(db_client)

    assert response.status_code == 201


def test_email_failure_sets_status_failed_and_keeps_application(
    db_client, db_url, fake_email
):
    fake_email.error = RuntimeError("smtp failure")

    response = post_application(db_client)

    assert response.status_code == 201
    row = _application(db_url, response.json()["id"])
    assert row is not None
    assert row[3] == "failed"
    assert row[4] is None


def test_email_success_sets_status_sent_and_timestamp(db_client, db_url):
    response = post_application(db_client)

    assert response.status_code == 201
    row = _application(db_url, response.json()["id"])
    assert row[3] == "sent"
    assert row[4] is not None


def test_slow_email_does_not_delay_the_201_response(
    db_client, fake_email, monkeypatch
):
    events: list[str] = []
    original_send = fake_email.send_confirmation_email

    def slow_send(to, name, domains):
        events.append("email_started")
        time.sleep(0.1)
        original_send(to, name, domains)

    monkeypatch.setattr(fake_email, "send_confirmation_email", slow_send)

    class ResponseEventRecorder:
        async def __call__(self, scope, receive, send):
            async def record_send(message):
                if (
                    message["type"] == "http.response.body"
                    and not message.get("more_body", False)
                ):
                    events.append("response_body_sent")
                await send(message)

            await db_client.app(scope, receive, record_send)

    with TestClient(ResponseEventRecorder()) as client:
        response = post_application(client)

    assert response.status_code == 201
    assert events.index("response_body_sent") < events.index("email_started")


def test_email_not_sent_when_validation_fails(db_client, fake_email):
    response = post_application(db_client, {"name": "!"})

    assert response.status_code == 422
    assert fake_email.calls == []


def test_email_not_sent_when_storage_fails(db_client, fake_storage, fake_email):
    fake_storage.error = RuntimeError("storage unavailable")

    response = post_application(db_client)

    assert response.status_code == 500
    assert fake_email.calls == []


def test_email_failure_logged_without_personal_data(
    db_client, fake_email, caplog
):
    fake_email.error = RuntimeError(
        "private failure Asha Rao 1AB23CD001 9876543210 asha@example.com"
    )

    with caplog.at_level(logging.ERROR):
        response = post_application(db_client)

    assert response.status_code == 201
    assert "Confirmation email failed" in caplog.text
    for private_value in (
        "Asha Rao",
        "1AB23CD001",
        "9876543210",
        "asha@example.com",
        "private failure",
    ):
        assert private_value not in caplog.text
