"""Group 5: duplicate and concurrency tests.

Required in PR feat/apply-submit-endpoint (B2).
Covers:
  - Same USN + same cycle → 409
  - Different case / surrounding spaces treated as duplicates
  - Same USN in a different cycle → allowed
  - Different USN, same email → allowed (uniqueness is USN + cycle only)
  - Duplicate leaves no orphan resume in storage
  - Duplicate does not send an email
  - Duplicate does not modify the first application
  - Concurrent submissions: exactly one 201, rest 409, exactly one row
  - Concurrent duplicates leave no orphan objects
"""

import threading

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
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B2 PR)"
)

ENDPOINT = "/api/v1/applications"
VALID_RESUME = ("resume.pdf", make_pdf(1024), "application/pdf")


def post_form(client, payload=None, resume=VALID_RESUME):
    payload = payload or valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


def assert_success(response):
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    return response.json()


# ===========================================================================
# Basic duplicate detection
# ===========================================================================


def test_second_application_same_usn_same_cycle_returns_409(client):
    """Submitting twice with the same USN in the same cycle must return 409."""
    payload = valid_payload(usn="DUPTEST01")
    post_form(client, payload)  # first — must succeed
    response = post_form(client, payload)  # second — must be 409
    assert response.status_code == 409
    body = response.json()
    assert body.get("error") == "duplicate_application"


def test_duplicate_usn_different_case_returns_409(client):
    """USN comparison is case-insensitive: '1JU24CS042' and '1ju24cs042' are the same."""
    post_form(client, valid_payload(usn="1JU24CS042"))
    response = post_form(client, valid_payload(usn="1ju24cs042"))
    assert response.status_code == 409
    assert response.json().get("error") == "duplicate_application"


def test_duplicate_usn_with_surrounding_spaces_returns_409(client):
    """USN is trimmed before comparison — ' 1JU24CS042 ' matches '1JU24CS042'."""
    post_form(client, valid_payload(usn="TRIMTEST1"))
    response = post_form(client, valid_payload(usn=" TRIMTEST1 "))
    assert response.status_code == 409
    assert response.json().get("error") == "duplicate_application"


def test_same_usn_in_different_cycle_is_allowed(client, monkeypatch):
    """The same USN can apply again in a later hiring cycle."""
    post_form(client, valid_payload(usn="CYCLETEST1"))  # cycle = 2026-test

    # Change the cycle and resubmit
    monkeypatch.setenv("APPLICATION_CYCLE", "2027-test")
    response = post_form(client, valid_payload(usn="CYCLETEST1"))
    assert response.status_code == 201


def test_different_usn_same_personal_email_is_allowed(client):
    """Two different students can share the same personal email (only USN+cycle is unique)."""
    shared_email = "shared@example.com"
    post_form(client, valid_payload(usn="USNA001", personal_email=shared_email))
    response = post_form(client, valid_payload(usn="USNB002", personal_email=shared_email))
    assert response.status_code == 201


# ===========================================================================
# Duplicate leaves no side effects
# ===========================================================================


def test_duplicate_leaves_no_orphan_resume_in_storage(client, fake_storage):
    """When a duplicate is detected, any uploaded resume must be deleted immediately."""
    payload = valid_payload(usn="ORPH001")
    post_form(client, payload)  # first submission

    upload_count_before = len(fake_storage.upload_calls)
    post_form(client, payload)  # duplicate

    # Upload may have been attempted and then cleaned up, or never attempted
    assert len(fake_storage.delete_calls) >= (len(fake_storage.upload_calls) - upload_count_before), (
        "Duplicate: every upload after the first must be deleted (no orphan objects)"
    )


def test_duplicate_does_not_send_email(client, fake_email):
    """A duplicate submission must not trigger a confirmation email."""
    payload = valid_payload(usn="EMAILDUP1")
    post_form(client, payload)  # first — email sent
    calls_after_first = len(fake_email.calls)

    post_form(client, payload)  # duplicate — no email
    assert len(fake_email.calls) == calls_after_first, (
        "Duplicate submission must not trigger an additional email"
    )


def test_duplicate_does_not_modify_the_first_application(client, conn):
    """The first application row must be unchanged after a duplicate attempt."""
    payload = valid_payload(usn="MODCHECK1", name="First Name")
    first_response = post_form(client, payload)
    first_body = assert_success(first_response)
    first_id = first_body["id"]

    # Read the first row
    before = conn.execute(
        "SELECT name, created_at FROM applications WHERE id = %s", (first_id,)
    ).fetchone()

    # Attempt duplicate with different name
    dup_payload = valid_payload(usn="MODCHECK1", name="Different Name")
    post_form(client, dup_payload)

    # Read again
    after = conn.execute(
        "SELECT name, created_at FROM applications WHERE id = %s", (first_id,)
    ).fetchone()

    assert before[0] == after[0], "name was modified by duplicate submission"
    assert before[1] == after[1], "created_at was modified by duplicate submission"


# ===========================================================================
# Concurrency
# ===========================================================================


def test_concurrent_submissions_same_usn_only_one_succeeds(client, conn):
    """Several parallel requests with the same USN: exactly 1 must get 201, rest get 409."""
    payload = valid_payload(usn="CONCURRENT1")
    results = []
    num_threads = 5

    def submit():
        response = post_form(client, payload)
        results.append(response.status_code)

    threads = [threading.Thread(target=submit) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = results.count(201)
    conflicts = results.count(409)

    assert successes == 1, f"Expected exactly 1 success, got {successes}: {results}"
    assert conflicts == num_threads - 1, (
        f"Expected {num_threads - 1} conflicts, got {conflicts}: {results}"
    )

    # Exactly one row in the DB
    row = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE usn = 'CONCURRENT1' AND cycle = '2026-test'"
    ).fetchone()
    assert row[0] == 1


def test_concurrent_duplicates_leave_no_orphan_objects(client, fake_storage):
    """After concurrent duplicate submissions, every upload beyond the first is cleaned up."""
    payload = valid_payload(usn="CONCURRENT2")
    num_threads = 5

    threads = [threading.Thread(target=lambda: post_form(client, payload))
               for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    uploads = len(fake_storage.upload_calls)
    deletes = len(fake_storage.delete_calls)
    # Exactly one upload must remain (the winner's resume). All others must be deleted.
    surviving_objects = uploads - deletes
    assert surviving_objects == 1, (
        f"Expected 1 surviving object, got {surviving_objects} "
        f"(uploads={uploads}, deletes={deletes})"
    )
