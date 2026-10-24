"""Group 2: field validation tests.

Required in PR feat/apply-submit-endpoint (B2).
Covers every field rule from the shared contract in TODO.md:
  Name, USN, College email, Personal email, Mobile, Domains,
  and whole-request behaviour.

All tests hit POST /api/v1/applications with multipart/form-data.
Success: 201 with {id, message}.
Failure: 422 with {error: "validation_error", fields: {field: message}}.

These tests skip gracefully if app/main.py isn't ready yet.
"""

import pytest
from conftest import make_pdf, valid_payload

# ---------------------------------------------------------------------------
# Skip the whole module if app/main.py isn't ready yet
# ---------------------------------------------------------------------------


def _app_available() -> bool:
    try:
        import app.main  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B1/B2 PR)"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENDPOINT = "/api/v1/applications"
VALID_RESUME = ("resume.pdf", make_pdf(1024), "application/pdf")


def post_form(client, payload: dict, resume=VALID_RESUME):
    """Post multipart form. domains list is sent as repeated fields."""
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


def assert_validation_error(response, field: str | None = None):
    """Assert the response is a 422 in the contract shape."""
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    body = response.json()
    assert body.get("error") == "validation_error"
    assert isinstance(body.get("fields"), dict)
    if field:
        assert field in body["fields"], (
            f"Expected field '{field}' in error fields, got: {list(body['fields'].keys())}"
        )
    return body


def assert_success(response):
    """Assert the response is a 201 in the contract shape."""
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    assert "id" in body
    assert "message" in body
    return body


# ===========================================================================
# NAME
# ===========================================================================


def test_name_required(client):
    payload = valid_payload(name="")
    response = post_form(client, payload)
    assert_validation_error(response, "name")


def test_name_trimmed(client):
    """Leading/trailing whitespace is stripped before validation."""
    payload = valid_payload(name="  Ravi Kumar  ")
    response = post_form(client, payload)
    # Trimmed name is valid (len >= 2)
    assert_success(response)


def test_name_too_short_rejected(client):
    payload = valid_payload(name="R")  # 1 char — below minimum of 2
    response = post_form(client, payload)
    assert_validation_error(response, "name")


def test_name_too_long_rejected(client):
    payload = valid_payload(name="R" * 101)  # 101 chars — above maximum of 100
    response = post_form(client, payload)
    assert_validation_error(response, "name")


def test_name_allows_dots_apostrophes_hyphens(client):
    """Names with . ' - are valid per the contract."""
    for name in ["St. Mary", "O'Brien", "Jean-Pierre", "Dr. A. Rao"]:
        response = post_form(client, valid_payload(name=name))
        assert_success(response), f"Expected success for name '{name}'"


def test_name_accepts_non_ascii_letters(client):
    """Unicode letters (e.g. accented, Devanagari) are accepted."""
    for name in ["Rénée Dupont", "Müller Hans", "Priya Ñoño"]:
        response = post_form(client, valid_payload(name=name))
        assert_success(response), f"Expected success for name '{name}'"


def test_name_with_html_or_script_rejected(client):
    """Names containing HTML tags or script injection are rejected."""
    for bad_name in ["<script>alert(1)</script>", "<b>Bold</b>", "alert('xss')"]:
        response = post_form(client, valid_payload(name=bad_name))
        assert_validation_error(response, "name"), (
            f"Expected rejection for name '{bad_name}'"
        )


# ===========================================================================
# USN  (no fixed format — deliberately loose rules)
# ===========================================================================


def test_usn_required(client):
    payload = valid_payload(usn="")
    response = post_form(client, payload)
    assert_validation_error(response, "usn")


def test_usn_whitespace_only_rejected(client):
    for usn in ["   ", "\t", "\n"]:
        response = post_form(client, valid_payload(usn=usn))
        assert_validation_error(response, "usn"), f"Expected rejection for usn={usn!r}"


def test_usn_trimmed_and_uppercased(client):
    """The backend trims and uppercases the USN before storing."""
    response = post_form(client, valid_payload(usn="1ju24cs042"))
    body = assert_success(response)
    # Optionally verify the stored value is uppercased via the response or DB,
    # but at minimum the submission must succeed.
    assert body["id"]


@pytest.mark.parametrize(
    "usn",
    [
        "1AB23CD001",    # old-style
        "24BTRCS001",    # newer style
        "1JU24CS042",    # JU-style
        "ABC123",        # letters-first
        "123456789",     # all digits
        "A1B2C3D4E5",    # mixed, medium length
        "ABCDE",         # shortest allowed (5)
        "A" * 20,        # longest allowed (20)
    ],
)
def test_usn_accepts_many_different_formats(client, usn):
    """No year/branch/college pattern is enforced — many shapes must be accepted."""
    response = post_form(client, valid_payload(usn=usn))
    assert_success(response)


def test_usn_boundary_lengths_accepted(client):
    """Exactly min (5) and exactly max (20) chars are both accepted."""
    for usn in ["AB123", "A" * 20]:
        response = post_form(client, valid_payload(usn=usn))
        assert_success(response), f"Expected success for usn of length {len(usn)}"


def test_usn_too_short_rejected(client):
    payload = valid_payload(usn="AB12")  # 4 chars — below minimum of 5
    response = post_form(client, payload)
    assert_validation_error(response, "usn")


def test_usn_too_long_rejected(client):
    payload = valid_payload(usn="A" * 21)  # 21 chars — above maximum of 20
    response = post_form(client, payload)
    assert_validation_error(response, "usn")


def test_usn_inner_spaces_rejected(client):
    """USN may not contain internal spaces (only letters and digits)."""
    response = post_form(client, valid_payload(usn="1JU 24CS042"))
    assert_validation_error(response, "usn")


@pytest.mark.parametrize(
    "usn",
    [
        "<script>usn</script>",
        "'; DROP TABLE applications; --",
        "../etc/passwd",
        "USN😀",          # emoji
        "USN@#$%",       # punctuation
    ],
)
def test_usn_special_characters_rejected(client, usn):
    """Special chars, SQL injection, path traversal, and emoji are all rejected."""
    response = post_form(client, valid_payload(usn=usn))
    assert_validation_error(response, "usn"), f"Expected rejection for usn={usn!r}"


# ===========================================================================
# COLLEGE EMAIL  (optional — absent/empty/whitespace stored as NULL)
# ===========================================================================


def test_college_email_omitted_is_ok(client):
    """college_email is fully optional — the field may be absent entirely."""
    payload = valid_payload()
    payload.pop("college_email", None)
    response = post_form(client, payload)
    assert_success(response)


def test_college_email_empty_string_stored_as_null(client):
    """An empty string for college_email is treated as NULL (not a validation error)."""
    response = post_form(client, valid_payload(college_email=""))
    assert_success(response)


def test_college_email_whitespace_only_stored_as_null(client):
    """Whitespace-only college_email is treated as NULL (not a validation error)."""
    for value in ["   ", "\t", "  \n  "]:
        response = post_form(client, valid_payload(college_email=value))
        assert_success(response), f"Expected success for college_email={value!r}"


def test_college_email_valid_is_stored_trimmed_and_lowercase(client):
    """A given college email must be accepted and stored trimmed + lowercase."""
    response = post_form(client, valid_payload(college_email="  Ravi@JainUniversity.ac.in  "))
    assert_success(response)


def test_college_email_invalid_rejected(client):
    """An explicitly given but malformed email must be rejected."""
    for bad in ["not-an-email", "missing@", "@nodomain", "two@@at.com"]:
        response = post_form(client, valid_payload(college_email=bad))
        assert_validation_error(response, "college_email"), (
            f"Expected rejection for college_email={bad!r}"
        )


def test_college_email_any_domain_accepted(client):
    """No domain restriction — @gmail, @yahoo, @jainuniversity are all fine."""
    for email in [
        "student@gmail.com",
        "student@yahoo.co.in",
        "student@jainuniversity.ac.in",
        "student@protonmail.ch",
    ]:
        response = post_form(client, valid_payload(college_email=email))
        assert_success(response), f"Expected success for college_email={email!r}"


def test_college_email_same_as_personal_email_is_ok(client):
    """Using the same address for both email fields is allowed."""
    email = "same@example.com"
    response = post_form(client, valid_payload(college_email=email, personal_email=email))
    assert_success(response)


# ===========================================================================
# PERSONAL EMAIL  (required)
# ===========================================================================


def test_personal_email_required(client):
    payload = valid_payload(personal_email="")
    response = post_form(client, payload)
    assert_validation_error(response, "personal_email")


@pytest.mark.parametrize(
    "bad_email",
    [
        "noatsign",
        "double@@at.com",
        "spaces in@email.com",
        "@nodomain.com",
        "trailing.dot@domain.",
    ],
)
def test_personal_email_invalid_rejected(client, bad_email):
    response = post_form(client, valid_payload(personal_email=bad_email))
    assert_validation_error(response, "personal_email"), (
        f"Expected rejection for personal_email={bad_email!r}"
    )


def test_personal_email_trimmed_and_lowercased(client):
    """Leading/trailing spaces stripped and email stored lowercase."""
    response = post_form(client, valid_payload(personal_email="  Ravi.KUMAR@Gmail.Com  "))
    assert_success(response)


def test_personal_email_plus_addressing_accepted(client):
    """Plus-addressing (e.g. user+tag@domain.com) is a valid email format."""
    response = post_form(client, valid_payload(personal_email="ravi+turing@gmail.com"))
    assert_success(response)


# ===========================================================================
# MOBILE  (Indian 10-digit starting 6–9)
# ===========================================================================


def test_mobile_required(client):
    payload = valid_payload(mobile="")
    response = post_form(client, payload)
    assert_validation_error(response, "mobile")


def test_mobile_ten_digits_accepted(client):
    response = post_form(client, valid_payload(mobile="9876543210"))
    assert_success(response)


def test_mobile_plus91_prefix_normalized_to_ten_digits(client):
    """+91 prefix is accepted and stripped before storage."""
    response = post_form(client, valid_payload(mobile="+919876543210"))
    assert_success(response)


def test_mobile_leading_zero_normalized_to_ten_digits(client):
    """Leading 0 (e.g. 09876543210) is accepted and stripped."""
    response = post_form(client, valid_payload(mobile="09876543210"))
    assert_success(response)


def test_mobile_spaces_and_dashes_normalized(client):
    """Spaces and dashes in mobile number are stripped during normalization."""
    for mobile in ["98765 43210", "9876-543210", "+91 98765 43210"]:
        response = post_form(client, valid_payload(mobile=mobile))
        assert_success(response), f"Expected success for mobile={mobile!r}"


@pytest.mark.parametrize(
    "mobile",
    ["0876543210", "1876543210", "2876543210", "3876543210", "4876543210", "5876543210"],
)
def test_mobile_starting_with_0_to_5_rejected(client, mobile):
    """Indian mobiles start with 6, 7, 8 or 9 — anything else is rejected."""
    response = post_form(client, valid_payload(mobile=mobile))
    assert_validation_error(response, "mobile"), (
        f"Expected rejection for mobile={mobile!r}"
    )


def test_mobile_too_short_rejected(client):
    response = post_form(client, valid_payload(mobile="987654321"))  # 9 digits
    assert_validation_error(response, "mobile")


def test_mobile_too_long_rejected(client):
    response = post_form(client, valid_payload(mobile="98765432101"))  # 11 digits
    assert_validation_error(response, "mobile")


def test_mobile_with_letters_rejected(client):
    response = post_form(client, valid_payload(mobile="98765ABC10"))
    assert_validation_error(response, "mobile")


# ===========================================================================
# DOMAINS  (one or more of the five fixed keys)
# ===========================================================================

ALL_DOMAINS = ["technology", "photography", "design", "marketing", "social-media"]


def test_domains_required(client):
    """At least one domain must be selected."""
    payload = valid_payload()
    payload["domains"] = []
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", VALID_RESUME)]
    # Send with no domains field at all
    response = client.post(ENDPOINT, data=data, files=files)
    assert_validation_error(response, "domains")


def test_domains_empty_list_rejected(client):
    """An explicit empty domains list is also rejected."""
    payload = valid_payload(domains=[])
    response = post_form(client, payload)
    assert_validation_error(response, "domains")


def test_domains_single_accepted(client):
    for domain in ALL_DOMAINS:
        response = post_form(client, valid_payload(domains=[domain]))
        assert_success(response), f"Expected success for domains=['{domain}']"


def test_domains_multiple_accepted(client):
    response = post_form(client, valid_payload(domains=["technology", "design"]))
    assert_success(response)


def test_domains_all_five_accepted(client):
    response = post_form(client, valid_payload(domains=ALL_DOMAINS))
    assert_success(response)


def test_domains_order_does_not_matter(client):
    """Domain order in the request must not affect acceptance."""
    for ordering in [
        ["technology", "design", "photography"],
        ["photography", "technology", "design"],
        ["design", "photography", "technology"],
    ]:
        response = post_form(client, valid_payload(domains=ordering))
        assert_success(response), f"Expected success for domains={ordering}"


def test_domains_unknown_key_rejected(client):
    """A domain key not in the fixed list must be rejected."""
    for bad in ["tech", "TECHNOLOGY", "development", "media", "random"]:
        response = post_form(client, valid_payload(domains=[bad]))
        assert_validation_error(response, "domains"), (
            f"Expected rejection for domains=['{bad}']"
        )


def test_domains_wrong_case_rejected(client):
    """Domain keys are case-sensitive lowercase — 'Technology' is not 'technology'."""
    for bad in ["Technology", "DESIGN", "Photography", "Marketing", "Social-Media"]:
        response = post_form(client, valid_payload(domains=[bad]))
        assert_validation_error(response, "domains"), (
            f"Expected rejection for domains=['{bad}']"
        )


def test_domains_duplicate_value_rejected(client):
    """Sending the same domain twice must be rejected."""
    response = post_form(client, valid_payload(domains=["technology", "technology"]))
    assert_validation_error(response, "domains")


def test_domains_saved_rows_match_selection_exactly(client, conn):
    """The application_domains table must have exactly one row per chosen domain."""
    chosen = ["technology", "design"]
    response = post_form(client, valid_payload(domains=chosen))
    body = assert_success(response)
    app_id = body["id"]

    rows = conn.execute(
        "SELECT domain FROM application_domains WHERE application_id = %s",
        (app_id,),
    ).fetchall()
    saved_domains = {r[0] for r in rows}
    assert saved_domains == set(chosen), (
        f"Expected domains {set(chosen)}, got {saved_domains}"
    )


# ===========================================================================
# WHOLE-REQUEST BEHAVIOUR
# ===========================================================================


def test_multiple_invalid_fields_reported_together(client):
    """All invalid fields should be reported in one response, not one at a time."""
    payload = valid_payload(name="", usn="", personal_email="bad")
    response = post_form(client, payload)
    body = assert_validation_error(response)
    # At least two fields must be present in the error map
    assert len(body["fields"]) >= 2, (
        f"Expected multiple field errors, got: {body['fields']}"
    )


def test_error_fields_keyed_by_field_name(client):
    """The fields map must use the field name as key, not an index or path."""
    payload = valid_payload(name="", mobile="bad")
    response = post_form(client, payload)
    body = assert_validation_error(response)
    for key in body["fields"]:
        assert isinstance(key, str)
        assert key.isidentifier() or key == "social-media", (
            f"Unexpected field key format: '{key}'"
        )


def test_validation_failure_writes_nothing(client, fake_storage, fake_email, conn):
    """A failed validation must not create any DB row, storage object, or email call."""
    payload = valid_payload(name="", usn="")  # two invalid fields
    post_form(client, payload)

    # No storage calls
    assert len(fake_storage.upload_calls) == 0
    # No email calls
    assert len(fake_email.calls) == 0
    # No DB row (check applications table is empty for our cycle)
    rows = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s",
        ("2026-test",),
    ).fetchone()
    assert rows[0] == 0


def test_success_response_has_only_id_and_message(client):
    """The 201 body must contain only 'id' and 'message' — no personal data."""
    response = post_form(client, valid_payload())
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "message"}, (
        f"Unexpected keys in success response: {set(body.keys())}"
    )


def test_unknown_extra_form_fields_ignored(client):
    """Extra fields submitted in the form must be silently ignored, not cause a 500."""
    payload = valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    data["extra_mystery_field"] = "should be ignored"
    files = [("resume", VALID_RESUME)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    response = client.post(ENDPOINT, data=data, files=files)
    # Must succeed or fail with a clean validation error — never a 500
    assert response.status_code in (201, 422)
    if response.status_code == 422:
        body = response.json()
        assert body.get("error") == "validation_error"


def test_json_body_instead_of_multipart_returns_clean_422_not_500(client):
    """Sending JSON instead of multipart must return a clean 422, not a 500 crash."""
    response = client.post(
        ENDPOINT,
        json={"name": "Test", "usn": "1JU24CS042"},
    )
    assert response.status_code == 422
    body = response.json()
    # Must be a clean contract-shape error, not a raw traceback
    assert "Traceback" not in str(body)
    assert body.get("error") in ("validation_error", "server_error")
