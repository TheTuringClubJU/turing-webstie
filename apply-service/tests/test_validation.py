"""B2 application form validation and normalization regressions."""

import uuid

import psycopg
import pytest
from api_helpers import post_application

from app.config import (
    ALLOWED_DOMAINS,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    USN_MAX_LENGTH,
    USN_MIN_LENGTH,
)


def _saved_application(db_url, usn=None):
    with psycopg.connect(db_url) as connection:
        if usn is None:
            return connection.execute(
                "SELECT * FROM applications ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return connection.execute(
            "SELECT * FROM applications WHERE usn = %s", (usn,)
        ).fetchone()


def _invalid(client, **changes):
    payload = {
        "name": "Asha Rao",
        "usn": "1AB23CD001",
        "college_email": None,
        "personal_email": "asha@example.com",
        "mobile": "9876543210",
        "domains": ["technology"],
    }
    payload.update(changes)
    return post_application(client, payload)


def test_name_required(db_client):
    response = _invalid(db_client, name=None)

    assert response.status_code == 422
    assert "name" in response.json()["fields"]


def test_name_trimmed(db_client, db_url):
    response = _invalid(db_client, name="  Asha Rao  ")

    assert response.status_code == 201
    assert _saved_application(db_url)[2] == "Asha Rao"


def test_name_too_short_rejected(db_client):
    response = _invalid(db_client, name="A" * (NAME_MIN_LENGTH - 1))

    assert response.status_code == 422
    assert "name" in response.json()["fields"]


def test_name_too_long_rejected(db_client):
    response = _invalid(db_client, name="A" * (NAME_MAX_LENGTH + 1))

    assert response.status_code == 422
    assert "name" in response.json()["fields"]


def test_name_allows_dots_apostrophes_hyphens(db_client):
    response = _invalid(db_client, name="  Asha O'Neil-Smith Jr. ")

    assert response.status_code == 201


def test_name_accepts_non_ascii_letters(db_client):
    response = _invalid(db_client, name="Élodie 李")

    assert response.status_code == 201


def test_name_with_html_or_script_rejected(db_client):
    response = _invalid(db_client, name="<script>alert(1)</script>")

    assert response.status_code == 422


def test_usn_required(db_client):
    response = _invalid(db_client, usn=None)

    assert response.status_code == 422
    assert "usn" in response.json()["fields"]


def test_usn_whitespace_only_rejected(db_client):
    response = _invalid(db_client, usn="   ")

    assert response.status_code == 422


def test_usn_trimmed_and_uppercased(db_client, db_url):
    response = _invalid(db_client, usn="  aBc123  ")

    assert response.status_code == 201
    assert _saved_application(db_url, "ABC123")[3] == "ABC123"


@pytest.mark.parametrize(
    "usn",
    ["1AB23CD001", "24BTRCS001", "ABC123", "123456789012", "ABCDE", "X" * USN_MAX_LENGTH],
)
def test_usn_accepts_many_different_formats(db_client, usn):
    response = _invalid(db_client, usn=usn)

    assert response.status_code == 201


@pytest.mark.parametrize("usn", ["A" * USN_MIN_LENGTH, "X" * USN_MAX_LENGTH])
def test_usn_boundary_lengths_accepted(db_client, usn):
    response = _invalid(db_client, usn=usn)

    assert response.status_code == 201


def test_usn_too_short_rejected(db_client):
    response = _invalid(db_client, usn="A" * (USN_MIN_LENGTH - 1))

    assert response.status_code == 422


def test_usn_too_long_rejected(db_client):
    response = _invalid(db_client, usn="A" * (USN_MAX_LENGTH + 1))

    assert response.status_code == 422


def test_usn_inner_spaces_rejected(db_client):
    response = _invalid(db_client, usn="ABC 123")

    assert response.status_code == 422


@pytest.mark.parametrize("usn", ["<script>", "1;DROP TABLE", "../abcd", "ABC_123", "AB😀CD"])
def test_usn_special_characters_rejected(db_client, usn):
    response = _invalid(db_client, usn=usn)

    assert response.status_code == 422


def test_college_email_omitted_is_ok(db_client, db_url):
    payload = {
        "name": "Asha Rao",
        "usn": "ABC123",
        "personal_email": "asha@example.com",
        "mobile": "9876543210",
        "domains": ["technology"],
    }
    response = post_application(db_client, payload)

    assert response.status_code == 201
    assert _saved_application(db_url, "ABC123")[4] is None


def test_college_email_empty_string_stored_as_null(db_client, db_url):
    response = _invalid(db_client, college_email="")

    assert response.status_code == 201
    assert _saved_application(db_url)[4] is None


def test_college_email_whitespace_only_stored_as_null(db_client, db_url):
    response = _invalid(db_client, college_email="   ")

    assert response.status_code == 201
    assert _saved_application(db_url)[4] is None


def test_college_email_valid_is_stored_trimmed_and_lowercase(db_client, db_url):
    response = _invalid(db_client, college_email="  ASHA@Example.COM ")

    assert response.status_code == 201
    assert _saved_application(db_url)[4] == "asha@example.com"


def test_college_email_invalid_rejected(db_client):
    response = _invalid(db_client, college_email="not-an-email")

    assert response.status_code == 422


def test_college_email_any_domain_accepted(db_client):
    response = _invalid(db_client, college_email="asha@university.example")

    assert response.status_code == 201


def test_college_email_same_as_personal_email_is_ok(db_client):
    response = _invalid(db_client, college_email="asha@example.com")

    assert response.status_code == 201


def test_personal_email_required(db_client):
    response = _invalid(db_client, personal_email=None)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "email",
    ["asha.example.com", "asha@@example.com", "asha @example.com", "asha@", "asha@example.com."],
)
def test_personal_email_invalid_rejected(db_client, email):
    response = _invalid(db_client, personal_email=email)

    assert response.status_code == 422


def test_personal_email_trimmed_and_lowercased(db_client, db_url):
    response = _invalid(db_client, personal_email="  ASHA@Example.COM ")

    assert response.status_code == 201
    assert _saved_application(db_url)[5] == "asha@example.com"


def test_personal_email_plus_addressing_accepted(db_client):
    response = _invalid(db_client, personal_email="asha+club@example.com")

    assert response.status_code == 201


def test_mobile_required(db_client):
    response = _invalid(db_client, mobile=None)

    assert response.status_code == 422


def test_mobile_ten_digits_accepted(db_client):
    assert _invalid(db_client, mobile="9123456789").status_code == 201


def test_mobile_plus91_prefix_normalized_to_ten_digits(db_client, db_url):
    response = _invalid(db_client, mobile="+91 9876543210")

    assert response.status_code == 201
    assert _saved_application(db_url)[6] == "9876543210"


def test_mobile_leading_zero_normalized_to_ten_digits(db_client, db_url):
    response = _invalid(db_client, mobile="09876543210")

    assert response.status_code == 201
    assert _saved_application(db_url)[6] == "9876543210"


def test_mobile_spaces_and_dashes_normalized(db_client, db_url):
    response = _invalid(db_client, mobile="98765-43210")

    assert response.status_code == 201
    assert _saved_application(db_url)[6] == "9876543210"


@pytest.mark.parametrize("mobile", ["5123456789", "0123456789"])
def test_mobile_starting_with_0_to_5_rejected(db_client, mobile):
    response = _invalid(db_client, mobile=mobile)

    assert response.status_code == 422


def test_mobile_too_short_rejected(db_client):
    assert _invalid(db_client, mobile="987654321").status_code == 422


def test_mobile_too_long_rejected(db_client):
    assert _invalid(db_client, mobile="98765432101").status_code == 422


def test_mobile_with_letters_rejected(db_client):
    assert _invalid(db_client, mobile="98765abcde").status_code == 422


def test_domains_required(db_client):
    response = _invalid(db_client, domains=None)

    assert response.status_code == 422


def test_domains_empty_list_rejected(db_client):
    response = _invalid(db_client, domains=[])

    assert response.status_code == 422


def test_domains_single_accepted(db_client):
    assert _invalid(db_client, domains=["design"]).status_code == 201


def test_domains_multiple_accepted(db_client):
    assert _invalid(db_client, domains=["design", "technology"]).status_code == 201


def test_domains_all_five_accepted(db_client):
    assert _invalid(db_client, domains=list(ALLOWED_DOMAINS)).status_code == 201


def test_domains_order_does_not_matter(db_client, db_url):
    domains = ["design", "technology"]
    response = _invalid(db_client, domains=domains)

    assert response.status_code == 201
    with psycopg.connect(db_url) as connection:
        saved = connection.execute(
            "SELECT domain FROM application_domains ORDER BY domain"
        ).fetchall()
    assert {row[0] for row in saved} == set(domains)


@pytest.mark.parametrize("domain", ["unlisted", "tech", "social_media"])
def test_domains_unknown_key_rejected(db_client, domain):
    response = _invalid(db_client, domains=[domain])

    assert response.status_code == 422


def test_domains_wrong_case_rejected(db_client):
    response = _invalid(db_client, domains=["Technology"])

    assert response.status_code == 422


def test_domains_duplicate_value_rejected(db_client):
    response = _invalid(db_client, domains=["technology", "technology"])

    assert response.status_code == 422


def test_domains_saved_rows_match_selection_exactly(db_client, db_url):
    domains = ["technology", "marketing", "social-media"]
    response = _invalid(db_client, domains=domains)

    assert response.status_code == 201
    with psycopg.connect(db_url) as connection:
        saved = connection.execute(
            "SELECT domain FROM application_domains"
        ).fetchall()
    assert {row[0] for row in saved} == set(domains)
    assert len(saved) == len(domains)


def test_multiple_invalid_fields_reported_together(db_client):
    response = _invalid(db_client, name="!", usn="x", personal_email="bad", mobile="12")

    assert response.status_code == 422
    assert {"name", "usn", "personal_email", "mobile"} <= set(
        response.json()["fields"]
    )


def test_error_fields_keyed_by_field_name(db_client):
    response = _invalid(db_client, name="!", personal_email="bad")

    assert set(response.json()["fields"]) == {"name", "personal_email"}


def test_validation_failure_writes_nothing(
    db_client, db_url, fake_storage, fake_email
):
    response = _invalid(db_client, name="<script>")

    assert response.status_code == 422
    assert fake_storage.uploads == []
    assert fake_storage.deletions == []
    assert fake_email.calls == []
    with psycopg.connect(db_url) as connection:
        assert connection.execute("SELECT count(*) FROM applications").fetchone()[0] == 0


def test_success_response_has_only_id_and_message(db_client):
    response = _invalid(db_client)

    assert response.status_code == 201
    assert set(response.json()) == {"id", "message"}
    assert response.json()["message"] == "Application received"
    uuid.UUID(response.json()["id"])


def test_unknown_extra_form_fields_ignored(db_client):
    response = post_application(
        db_client, extra_fields={"unexpected": "ignored"}
    )

    assert response.status_code == 201


def test_json_body_instead_of_multipart_returns_clean_422_not_500(db_client):
    response = db_client.post(
        "/api/v1/applications",
        json={"name": "Asha Rao", "usn": "ABC123"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
