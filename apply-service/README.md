# apply-service

Microservice for **Apply to Join**: stores applications (Neon / Postgres), resume PDFs (MinIO) and sends the thank-you email (Brevo). This change adds the FastAPI scaffold, configuration, health endpoint, CORS, and shared JSON error responses. The multipart submission endpoint and transactional persistence are implemented here. Real storage and email integrations are follow-up tasks.

## What is here

```
apply-service/
  app/
    main.py               FastAPI app, health route, CORS, and error responses
    config.py             validated environment settings
    errors.py             sanitized API errors
    schemas.py            API response schemas
    services/             application service package
  db/schema.sql           the whole database schema (one file)
  tests/                  API and schema tests
  requirements.txt        pinned API, test, and lint dependencies
  ruff.toml
  pytest.ini
  .env.example
```

## Start the API

Copy `.env.example` to `.env`, set the runtime values (including `DATABASE_URL`,
`APPLICATION_CYCLE`, and `CORS_ORIGINS`), then run:

```bash
uvicorn app.main:app --reload
```

The health endpoint is `GET /api/v1/health`. `CORS_ORIGINS` accepts a
comma-separated list of explicit frontend origins and rejects wildcard origins.
Validation, HTTP, and unexpected errors use the API's JSON contract; unexpected
errors are logged without exposing internal details in the response.

## Submit an application

`POST /api/v1/applications` accepts multipart form fields `name`, `usn`, `personal_email`, `mobile`, one or more repeated `domains` fields, an optional `college_email`, and a PDF `resume`. The service normalizes and validates fields, enforces the configured resume size limit, uploads through an injected storage service, and commits the application and selected domains in one PostgreSQL transaction. Storage remains an injected interface in this change; the tests use an in-memory fake. Do not enable live submissions until Darsh's MinIO integration is wired in.

Run backend tests with `TEST_DATABASE_URL` set to a disposable local PostgreSQL server whose role can create databases. The tests create and drop their own temporary database; never use production data.

## Tables

**`applications`**: one row per applicant per hiring cycle.
`id` (uuid), `cycle`, `name`, `usn`, `college_email` (optional), `personal_email`, `mobile`, `resume_object_key`, `resume_original_filename`, `resume_size_bytes`, `confirmation_email_status` (`pending` | `sent` | `failed`), `confirmation_email_sent_at`, `created_at`. Unique on (`usn`, `cycle`).

**`application_domains`**: one row per domain the applicant chose. Primary key (`application_id`, `domain`), deleted automatically with the application. Domains: `technology`, `photography`, `design`, `marketing`, `social-media`.

### Rules enforced by the database itself

The backend must normalize **before** inserting; the database rejects anything that isn't.

| Column | Rule |
|---|---|
| `usn` | Trimmed and **UPPERCASE**, not blank. **No fixed format** (it changes every year) |
| `personal_email` | Trimmed, lowercase, not blank |
| `college_email` | `NULL` when not given. Never `''`. If present: trimmed, lowercase |
| `mobile` | Exactly 10 digits, starting 6 to 9 (no `+91`, no spaces) |
| `name`, `cycle`, `resume_object_key` | Not blank |
| `resume_size_bytes` | Greater than 0 |
| `domain` | One of the five keys above (lowercase) |

Because `usn` must already be uppercase and trimmed, the unique key reliably catches `1ab23` vs `1AB23` vs ` 1AB23` duplicates.

## Create the tables on Neon

Use the **direct** connection string (host **without** `-pooler`). Either:

- **Neon SQL Editor:** open your database in the Neon console, paste the contents of `db/schema.sql`, run it.
- **psql:**
  ```bash
  psql -v ON_ERROR_STOP=1 "$DATABASE_URL_DIRECT" -f db/schema.sql
  ```
  PowerShell: `psql -v ON_ERROR_STOP=1 $env:DATABASE_URL_DIRECT -f db/schema.sql`

`schema.sql` is safe to run again (`IF NOT EXISTS`) and runs as one transaction, so it either fully applies or not at all. Do this on a Neon **dev** branch first.

## Run the tests

Use a throwaway database: a Postgres installed on your machine, or a **separate throwaway Neon branch** made just for tests. **Never** point it at your dev or production data: the test run wipes that database's `public` schema and rebuilds it from `db/schema.sql`.

```bash
cd apply-service
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost/apply_test"
pytest
```

## Changing the schema later

1. Edit `db/schema.sql` so it always describes the **final** schema.
2. If the tables already exist on Neon, `schema.sql` will not alter them (it only creates what is missing). Write the matching `ALTER TABLE ...` statements, run them on Neon dev, then production, and tell the team.
3. Add or update a test in `tests/test_schema.py` for the change, and run `pytest`.

## CI

`.github/workflows/ci.yml` runs on every pull request and push to `main` and `feat/**` branches:

- **Frontend (lint + build):** `npm ci`, `npm run lint`, `npm run build`.
- **apply-service (lint + schema tests):** installs Postgres on the runner, runs `ruff check`, `pytest`, and applies `db/schema.sql` twice with `psql`.

Run the same checks locally before pushing: `ruff check .` and `pytest` inside `apply-service/`.