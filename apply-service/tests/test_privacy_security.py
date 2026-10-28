"""B2 privacy and injection-resistance regressions."""

import logging

import psycopg
import pytest
from api_helpers import post_application

SENSITIVE_VALUES = (
    "Asha Rao",
    "1AB23CD001",
    "9876543210",
    "asha@example.com",
)


def test_logs_never_contain_name_usn_phone_or_email(
    db_client, fake_storage, caplog
):
    with caplog.at_level(logging.INFO):
        post_application(db_client)
        post_application(db_client, {"name": "!", "usn": "x"})
        fake_storage.error = RuntimeError("failure containing " + " ".join(SENSITIVE_VALUES))
        post_application(db_client)

    for value in SENSITIVE_VALUES:
        assert value not in caplog.text


def test_responses_never_echo_personal_data(db_client):
    success = post_application(db_client)
    error = post_application(db_client, {"name": "<script>alert(1)</script>"})

    for response in (success, error):
        for value in SENSITIVE_VALUES:
            assert value not in response.text


@pytest.mark.parametrize(
    "malicious_usn",
    [
        "'; DROP TABLE applications; --",
        "ABC123;DELETE",
        "../applications",
    ],
)
def test_sql_injection_payloads_rejected_or_stored_as_plain_data_and_tables_intact(
    db_client, db_url, malicious_usn
):
    response = post_application(
        db_client,
        {
            "name": "Asha Rao",
            "usn": malicious_usn,
            "personal_email": "asha@example.com",
            "mobile": "9876543210",
            "domains": ["technology"],
        },
    )

    assert response.status_code == 422
    with psycopg.connect(db_url) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            ).fetchall()
        }
    assert {"applications", "application_domains"} <= tables


def test_500_response_has_no_stack_trace_or_connection_string(
    db_client, fake_storage
):
    fake_storage.error = RuntimeError(
        "postgresql://user:password@db.example/private-database"
    )
    response = post_application(db_client)

    assert response.status_code == 500
    assert "Traceback" not in response.text
    assert "postgresql://" not in response.text
    assert "password" not in response.text
