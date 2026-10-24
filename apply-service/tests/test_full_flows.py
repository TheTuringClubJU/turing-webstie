"""B3 end-to-end API/database/storage/email contract regressions."""

import psycopg
import pytest
from api_helpers import post_application


def test_full_happy_path_all_fields_all_five_domains(
    db_client, db_url, fake_storage, fake_email
):
    domains = ["technology", "photography", "design", "marketing", "social-media"]
    response = post_application(
        db_client,
        {
            "name": "Asha Rao",
            "usn": "1AB23CD001",
            "college_email": "asha@college.example",
            "personal_email": "asha@example.com",
            "mobile": "9876543210",
            "domains": domains,
        },
    )

    assert response.status_code == 201
    application_id = response.json()["id"]
    with psycopg.connect(db_url) as connection:
        application = connection.execute(
            """
            SELECT id, name, usn, college_email, personal_email, mobile,
                   resume_object_key, confirmation_email_status
            FROM applications WHERE id = %s
            """,
            (application_id,),
        ).fetchone()
        selected_domains = {
            row[0]
            for row in connection.execute(
                "SELECT domain FROM application_domains WHERE application_id = %s",
                (application_id,),
            ).fetchall()
        }

    assert application[1:6] == (
        "Asha Rao",
        "1AB23CD001",
        "asha@college.example",
        "asha@example.com",
        "9876543210",
    )
    assert application[6] in fake_storage.objects
    assert application[7] == "sent"
    assert selected_domains == set(domains)
    assert len(fake_storage.uploads) == 1
    assert fake_email.calls == [("asha@example.com", "Asha Rao", domains)]


def test_minimal_application_no_college_email_one_domain(db_client, db_url):
    response = post_application(
        db_client,
        {
            "name": "Min Rao",
            "usn": "X1234",
            "personal_email": "min@example.com",
            "mobile": "9876543210",
            "domains": ["design"],
        },
    )

    assert response.status_code == 201
    with psycopg.connect(db_url) as connection:
        application = connection.execute(
            "SELECT college_email FROM applications WHERE id = %s",
            (response.json()["id"],),
        ).fetchone()
        domains = connection.execute(
            "SELECT domain FROM application_domains WHERE application_id = %s",
            (response.json()["id"],),
        ).fetchall()

    assert application == (None,)
    assert domains == [("design",)]


@pytest.mark.parametrize(
    ("name", "usn", "personal_email", "mobile", "domains"),
    [
        ("Asha Rao", "1AB23CD001", "asha@example.com", "9876543210", ["technology"]),
        ("Min Rao", "X1234", "min@example.com", "9123456789", ["design"]),
        ("Lee O'Neil", "2026A", "lee@example.com", "8765432109", ["photography"]),
        ("Sam Patel", "ABCD1234567890123456", "sam@example.com", "7654321098", ["marketing"]),
    ],
)
def test_realistic_applicant_matrix(
    db_client, name, usn, personal_email, mobile, domains
):
    response = post_application(
        db_client,
        {
            "name": name,
            "usn": usn,
            "personal_email": personal_email,
            "mobile": mobile,
            "domains": domains,
        },
    )

    assert response.status_code == 201
