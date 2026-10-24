"""Group 9: full end-to-end flow tests.

Required in PR feat/apply-email-and-hardening (B3).
These are the highest-level tests that exercise the complete happy path
and a realistic variety of valid applicants. They verify that the whole
stack works together: validation, DB, storage, email status.
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

ALL_DOMAINS = ["technology", "photography", "design", "marketing", "social-media"]


def post_form(client, payload=None, resume=None):
    payload = payload or valid_payload()
    resume = resume or ("resume.pdf", make_pdf(1024), "application/pdf")
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


def assert_success(response):
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert set(body.keys()) == {"id", "message"}
    return body


# ===========================================================================
# Full happy path: all fields, all five domains
# ===========================================================================


def test_full_happy_path_all_fields_all_five_domains(client, conn, fake_storage, fake_email):
    """Complete submission with all five domains.

    After the call:
    - One application row in the DB
    - Five application_domains rows
    - One storage upload call with the correct key format
    - One email queued to personal_email
    - Status starts as 'pending'
    """
    import time

    pdf_bytes = make_pdf(512 * 1024)  # 512 KB
    payload = valid_payload(
        name="Ravi Shankar Kumar",
        usn="1JU24CS042",
        college_email="ravi@jainuniversity.ac.in",
        personal_email="ravi.kumar@gmail.com",
        mobile="+91 98765 43210",
        domains=ALL_DOMAINS,
    )
    response = post_form(client, payload, resume=("cv_ravi.pdf", pdf_bytes, "application/pdf"))
    body = assert_success(response)
    app_id = body["id"]

    # DB: application row
    row = conn.execute(
        "SELECT usn, name, personal_email, mobile, cycle, confirmation_email_status "
        "FROM applications WHERE id = %s",
        (app_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "1JU24CS042"
    assert row[2] == "ravi.kumar@gmail.com"
    assert row[3] == "9876543210"
    assert row[4] == "2026-test"
    assert row[5] == "pending"

    # DB: domain rows
    domains = conn.execute(
        "SELECT domain FROM application_domains WHERE application_id = %s", (app_id,)
    ).fetchall()
    assert {r[0] for r in domains} == set(ALL_DOMAINS)

    # Storage: correct key, no original filename in key
    assert len(fake_storage.upload_calls) == 1
    key = fake_storage.upload_calls[0]["key"]
    assert key == f"resumes/2026-test/{app_id}.pdf"
    assert "cv_ravi" not in key

    # Email: queued (background — give it a moment)
    time.sleep(0.2)
    assert len(fake_email.calls) == 1
    assert fake_email.calls[0]["to"] == "ravi.kumar@gmail.com"


# ===========================================================================
# Minimal valid application: no college email, one domain
# ===========================================================================


def test_minimal_application_no_college_email_one_domain(client, conn, fake_storage):
    """A minimal but valid application with no college email and one domain."""
    payload = valid_payload(domains=["design"])
    payload.pop("college_email", None)
    response = post_form(client, payload)
    body = assert_success(response)
    app_id = body["id"]

    # college_email must be stored as NULL
    row = conn.execute(
        "SELECT college_email FROM applications WHERE id = %s", (app_id,)
    ).fetchone()
    assert row[0] is None, f"Expected NULL for college_email, got: {row[0]!r}"

    # One domain row
    domains = conn.execute(
        "SELECT domain FROM application_domains WHERE application_id = %s", (app_id,)
    ).fetchall()
    assert {r[0] for r in domains} == {"design"}


# ===========================================================================
# Realistic applicant matrix
# ===========================================================================


@pytest.mark.parametrize(
    "name,usn,mobile,domains,college_email",
    [
        # Classic JU-style USN, +91 prefix mobile, one domain
        ("Priya Nair", "1JU24CS099", "+919876501234", ["technology"], "priya@jainuniversity.ac.in"),
        # Old-style USN (letters first), leading zero mobile, multi-domain
        ("Mohammed Aziz", "1AB23CD001", "09123456789", ["design", "photography"], None),
        # All-digits USN, spaces in mobile, all domains
        ("Anita Sharma", "123456789", "98765 43210", ALL_DOMAINS, "anita@example.com"),
        # Hyphenated name, max-length USN (20 chars), one domain
        ("Jean-Pierre Dubois", "A" * 20, "7000000001", ["marketing"], None),
        # Apostrophe in name, 5-char USN (shortest), social-media domain
        ("O'Brien Singh", "AB123", "6000000002", ["social-media"], "obrien@gmail.com"),
        # Unicode name, mixed-case USN (normalised to upper), personal email only
        ("Rénée Gupta", "1ju24cs001", "8100000003", ["technology", "design"], None),
        # Plus-addressed personal email, design domain
        ("Deepika Rao", "DEEPIKA01", "9900000004", ["design"], "deepika+turing@gmail.com"),
    ],
)
def test_realistic_applicant_matrix(
    client, conn, name, usn, mobile, domains, college_email
):
    """Parametrized realistic applicants with varied USN shapes, mobiles, and domains."""
    payload = valid_payload(
        name=name,
        usn=usn,
        mobile=mobile,
        domains=domains,
        college_email=college_email or "",
    )
    response = post_form(client, payload)
    body = assert_success(response)
    app_id = body["id"]

    # Verify application row exists
    row = conn.execute(
        "SELECT usn, name FROM applications WHERE id = %s", (app_id,)
    ).fetchone()
    assert row is not None, f"Application row not found for {name!r}"
    assert row[0] == usn.strip().upper(), (
        f"Expected USN {usn.strip().upper()!r}, got {row[0]!r}"
    )

    # Verify all chosen domains are stored
    saved_domains = {
        r[0] for r in conn.execute(
            "SELECT domain FROM application_domains WHERE application_id = %s", (app_id,)
        ).fetchall()
    }
    assert saved_domains == set(domains), (
        f"Expected domains {set(domains)}, got {saved_domains}"
    )
