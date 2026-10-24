"""B2 uniqueness, duplicate handling, and race regressions."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
from api_helpers import post_application
from fastapi.testclient import TestClient


def _count(database_url):
    with psycopg.connect(database_url) as connection:
        return connection.execute("SELECT count(*) FROM applications").fetchone()[0]


def test_second_application_same_usn_same_cycle_returns_409(db_client):
    assert post_application(db_client).status_code == 201
    duplicate = post_application(db_client)

    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "duplicate_application"


def test_duplicate_usn_different_case_returns_409(db_client):
    assert post_application(db_client, {"name": "Asha Rao", "usn": "abc123",
        "personal_email": "asha@example.com", "mobile": "9876543210",
        "domains": ["technology"]}).status_code == 201
    response = post_application(db_client, {"name": "Asha Rao", "usn": "ABC123",
        "personal_email": "other@example.com", "mobile": "9876543210",
        "domains": ["technology"]})

    assert response.status_code == 409


def test_duplicate_usn_with_surrounding_spaces_returns_409(db_client):
    first = post_application(db_client, {
        "name": "Asha Rao", "usn": "ABC123", "personal_email": "asha@example.com",
        "mobile": "9876543210", "domains": ["technology"],
    })
    second = post_application(db_client, {
        "name": "Asha Rao", "usn": " ABC123 ", "personal_email": "other@example.com",
        "mobile": "9876543210", "domains": ["technology"],
    })

    assert first.status_code == 201
    assert second.status_code == 409


def test_same_usn_in_different_cycle_is_allowed(db_client):
    assert post_application(db_client).status_code == 201
    db_client.app.state.settings = db_client.app.state.settings.model_copy(
        update={"application_cycle": "2027-hiring"}
    )
    response = post_application(db_client)

    assert response.status_code == 201


def test_different_usn_same_personal_email_is_allowed(db_client):
    payload = {
        "name": "Asha Rao", "usn": "ABC123", "personal_email": "asha@example.com",
        "mobile": "9876543210", "domains": ["technology"],
    }
    assert post_application(db_client, payload).status_code == 201
    payload["usn"] = "DEF456"
    assert post_application(db_client, payload).status_code == 201


def test_duplicate_leaves_no_orphan_resume_in_storage(
    db_client, fake_storage
):
    assert post_application(db_client).status_code == 201
    assert post_application(db_client).status_code == 409

    assert len(fake_storage.objects) == 1
    assert len(fake_storage.uploads) == 1


def test_duplicate_does_not_send_email(fake_email, db_client):
    assert post_application(db_client).status_code == 201
    assert post_application(db_client).status_code == 409

    assert len(fake_email.calls) == 1


def test_duplicate_does_not_modify_the_first_application(db_client, db_url):
    first = post_application(db_client)
    duplicate = post_application(
        db_client,
        {
            "name": "Other Person",
            "usn": "1AB23CD001",
            "personal_email": "other@example.com",
            "mobile": "9123456789",
            "domains": ["design"],
        },
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    with psycopg.connect(db_url) as connection:
        rows = connection.execute(
            "SELECT id, name FROM applications"
        ).fetchall()
        domains = connection.execute(
            "SELECT domain FROM application_domains"
        ).fetchall()
    assert rows == [(uuid.UUID(first.json()["id"]), "Asha Rao")]
    assert domains == [("technology",)]


def test_concurrent_submissions_same_usn_only_one_succeeds(
    db_client, db_url, fake_storage
):
    request_count = 5
    fake_storage.barrier = threading.Barrier(request_count)

    def send_once():
        with TestClient(db_client.app, raise_server_exceptions=False) as client:
            return post_application(client)

    with ThreadPoolExecutor(max_workers=request_count) as executor:
        responses = list(executor.map(lambda _: send_once(), range(request_count)))

    assert [response.status_code for response in responses].count(201) == 1
    assert [response.status_code for response in responses].count(409) == 4
    assert _count(db_url) == 1


def test_concurrent_duplicates_leave_no_orphan_objects(
    db_client, fake_storage
):
    request_count = 5
    fake_storage.barrier = threading.Barrier(request_count)

    def send_once():
        with TestClient(db_client.app, raise_server_exceptions=False) as client:
            return post_application(client)

    with ThreadPoolExecutor(max_workers=request_count) as executor:
        responses = list(executor.map(lambda _: send_once(), range(request_count)))

    assert [response.status_code for response in responses].count(201) == 1
    assert [response.status_code for response in responses].count(409) == 4
    assert len(fake_storage.objects) == 1
    assert len(fake_storage.uploads) == request_count
    assert len(fake_storage.deletions) == request_count - 1
