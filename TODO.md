# TODO — The Turing Club Website

Tracking what's fixed vs. what's new to build. Move items to `[x]` once done, and feel free to append new ones under the right section.

---

## Fixes

- [x] Make Navbar a bit bigger (height/padding)
- [x] Make the club logo in Navbar bigger and more highlighted/prominent
- [x] Replace "Jain University" with "Jain (Deemed-to-be-University)" everywhere it appears (Navbar, About, Footer, etc.)
- [x] Update real event photos in the HackNCrack section (replace placeholder image paths)
- [X] Update real leader/member images (replace placeholder image paths)
- [X] Restructure Leaders section hierarchy:
  - Faculty Advisor on top (already separate, keep as-is)
  - Below that: President, Vice President, Secretary shown in the middle/featured row
  - Remaining leads (Tech, Design, Social Media, Marketing, Photography) below as usual grid
- [X] Fix production asset paths

---

## Add-ons / Features

- [x] "See Upcoming Events" button (Hero) should scroll/link to the current open event — for now, point it to "Hiring Open — 2nd & 3rd Year Students"
- [x] Add a notification strip below the Navbar (highlighted color — red or a color matching the theme) showing the current upcoming event, e.g. "Hiring Open — 2nd & 3rd Year Students". Should stay visible/persistent until the event changes.
- [x] About Us: add a line about the club supporting and encouraging research
- [x] About Us: mention that the club also runs webinars and seminars, not just hackathons/workshops
- [x] "See More Events" (Events section) should link to a **separate Events page**, not scroll within the homepage:
  - Own hero section with its own heading/subheading and CTA
  - Sub-sections for: Events, Workshops, Seminars, Webinars (3–4 categories)
  - Reuses the same design system (colors, typography, card styles) as the rest of the site
- [X] Add Deeksharambh 2025 and 2026 events, bid & byte events and cybersecurity workshop data

---

## Round 2 — Hiring Results + Hiring 1st Years

Two **independent tasks**, built by two different people. Task A and Task B touch some of the same files, so read **"Who owns what"** and **"Merge order"** below before you start.

| | **Task A — Hiring 2nd & 3rd Year: Results** | **Task B — New "Hiring 1st Years" card** |
| --- | --- | --- |
| Owner | Subham | Swapnil |
| What it is | Finish the *existing* card: announce results, remove all "to be announced" text, remove home-page results links | Build a *brand-new* card with Read More, Results, 4 photos and its own data |
| Suggested branch | `feat/hiring-2nd-year-results` | `feat/hiring-1st-year-card` |
| Results data file | `src/data/results-2nd-year.json` | `src/data/results-1st-year.json` |
| Slug | `hiring-2nd-3rd-year-2026` (already exists) | `hiring-1st-year-2026` (new) |
| Main risk | Breaking/forgetting to remove old "pending" text | Copy-pasting 2nd-year content by mistake |

> Per `CONTRIBUTING.md`: open **one GitHub issue per task**, branch from an up-to-date `main`, run `npm run build` before the PR, and add yourself to `CONTRIBUTORS.md`.

### Shared rules (both tasks)

- Results are shown **tab-wise by domain**, in this order: **Tech, Design, Photography, Marketing, Social Media**. **Tech is the default tab.**
- Each domain's tab lists the **final / selected students** only.
- Results data lives in a **JSON file** (not hardcoded in JSX). One file per hiring drive.
- Use design tokens from `src/index.css` (`bg-surface`, `border-border`, `text-primary-light`, ...). No hardcoded hex colors.
- Check desktop and mobile (tabs must wrap/scroll cleanly on a phone).

### Agreed JSON shape (both files must follow this exactly)

```json
{
  "event": "Hiring 2nd & 3rd Year Students",
  "slug": "hiring-2nd-3rd-year-2026",
  "announcedOn": "YYYY-MM-DD",
  "domains": {
    "tech":         { "label": "Tech",         "selected": [ { "name": "Full Name", "year": "2nd" } ] },
    "design":       { "label": "Design",       "selected": [] },
    "photography":  { "label": "Photography",  "selected": [] },
    "marketing":    { "label": "Marketing",    "selected": [] },
    "social-media": { "label": "Social Media", "selected": [] }
  }
}
```

- Domain keys are fixed: `tech`, `design`, `photography`, `marketing`, `social-media`. Do not rename them.
- A student entry needs at least `name` and `year`. Any extra field (e.g. `program`) must be added by **both** people, or the Results page must treat it as optional.
- An empty `selected` array must render a friendly "No selections announced for this domain yet." message, not a blank tab.
- *Confirm with the team lead which student details are OK to publish before filling real data.*

### Who owns what (to avoid merge conflicts)

| File | Subham | Swapnil |
| --- | --- | --- |
| `src/pages/Results.jsx` | **Owns** (rewrites it) | Do not edit |
| `src/data/results/index.js` (new registry, see A5) | **Owns** | Adds **one line** for the 1st-year file only |
| `src/data/results-2nd-year.json` | **Owns** | - |
| `src/data/results-1st-year.json` | - | **Owns** |
| `src/data/events.js` | Edits only the `hiring-2nd-3rd-year-2026` object | Only **adds** the new object + its image imports |
| `src/components/Hero.jsx`, `NotificationBar.jsx`, `src/data/notification.js` | **Owns** | Do not edit |
| `src/pages/OurWork.jsx`, `EventDetail.jsx`, `ResultsButton.jsx` | Only if Subham finds a bug | Only if Swapnil finds a bug; tell Subham first |
| `src/assets/images/events/hiring-1st-year-2026/` | - | **Owns** |

### Merge order

1. **Subham merges first**, because the generic Results page and the results registry come from Task A.
2. Swapnil can build the card, Read More page, photos and JSON in parallel, but **rebases on `main` after Subham merges** and then wires the Results page (B6). In `events.js` both people edit different objects; if Git still complains, resolve locally (not in GitHub's web editor).

---

### Task A — Hiring 2nd & 3rd Year: announce results *(Subham)*

Current state (from the code): the Hero has a "Applications closed — results pending" card with a Results button; `notification.js` says "Hiring Results To Be Announced Soon" with a "View Results" link; `Results.jsx` just says "Results to be announced. Stay tuned!".

#### A1. Remove the home page results entry points *(marked for removal)*

- [x] `src/components/Hero.jsx`: delete the whole "hiring results card" block (the box with "Hiring · 2nd & 3rd Year Students", "Applications closed — results pending" and the Results button).
- [x] `src/components/Hero.jsx`: remove the now-unused `import ResultsButton from './ResultsButton';`.
- [x] `src/components/NotificationBar.jsx`: remove the **"View Results →"** link. If the bar stays in the codebase, make sure it does not point to any results route.
- [x] `src/data/notification.js`: remove the "Hiring Results To Be Announced Soon" message and the `/our-work/hiring-2nd-3rd-year-2026/results` href. Keep `active: false` so nothing renders.
- [x] Search the whole `src` folder for any other home-page link to `/results` (`grep -rn -i "result" src`) and remove it. Home must have **no** Results button or redirect.

#### A2. Remove every "results to be announced / pending / soon" text

- [x] `src/pages/Results.jsx`: remove "Results to be announced. Stay tuned!".
- [x] Final check: `grep -rn -i -E "to be announced|stay tuned|pending|announced soon" src` returns nothing related to results.

#### A3. Create `src/data/results-2nd-year.json`

- [x] Use the agreed JSON shape above, `slug: "hiring-2nd-3rd-year-2026"`.
- [x] Fill in the final/selected students for **Tech, Design, Photography, Marketing, Social Media** (get the final list from the club leads).
- [x] Set `announcedOn` to the real announcement date.

#### A4. Rebuild `src/pages/Results.jsx` as a tabbed page

- [x] Tabs: Tech, Design, Photography, Marketing, Social Media. **Tech is the default.**
- [x] Read the active tab from `?tab=` (e.g. `/our-work/hiring-2nd-3rd-year-2026/results?tab=design`) the same way `OurWork.jsx` does, and fall back to Tech for a missing/invalid value.
- [x] Show the list of selected students for the active domain, with a count (e.g. "12 selected").
- [x] Empty domain shows the friendly empty-state message.
- [x] Keep the existing "Back to ..." link and the same page header style.
- [x] Page must be **generic** (driven by the slug), so Task B's 1st-year results work with no extra page code.

#### A5. Make results lookup generic (this is what unblocks Swapnil)

- [x] Create `src/data/results/index.js` exporting a map of slug to JSON, e.g.:

  ```js
  import hiring2nd from '../results-2nd-year.json';
  export const RESULTS = {
    'hiring-2nd-3rd-year-2026': hiring2nd,
    // Task B adds: 'hiring-1st-year-2026': hiring1st,
  };
  ```

- [x] `Results.jsx` looks up `RESULTS[slug]`. If a slug has no entry, show a neutral "Results aren't available for this event." (do **not** reuse the old "to be announced" wording).
- [x] Tell Swapnil as soon as this is merged.

#### A6. Keep Results buttons only where intended

- [x] Results button **stays** on the Our Work > Events card and on the event detail page for this event (`hasResults: true` in `events.js` stays).
- [x] Update the comment in `ResultsButton.jsx` (it still says the page "just says results are pending").

#### A7. Verify and ship

- [x] Open `/`, confirm no Results button/link anywhere on the home page and no notification strip.
- [x] Open Our Work > Events > Hiring 2nd & 3rd Year > **Results**, confirm tabs work, Tech opens first, every domain shows the right names.
- [x] `npm run build` and `npm run lint` pass.
- [x] Add yourself to `CONTRIBUTORS.md`, open PR, link the issue.

---

### Task B — New card: "Hiring 1st Years" *(Swapnil)*

Goal: a second hiring card in the **Our Work > Events** tab that behaves exactly like the 2nd & 3rd year card: card with **Read More** and **Results** buttons, a Read More page that goes one level deeper with more content, **4 event photos**, and its own results JSON.

#### B1. Collect the content first (blocker)

- [x] Get from the team: final title, date, short description (for the card), longer description (for Read More), and which domains were open for 1st years.
- [x] Get **4 event photos** (JPEG, ideally compressed to a reasonable size).
- [x] Working title: **"Hiring 1st Year Students"** (matches the existing "Hiring 2nd & 3rd Year Students"; rename if the team prefers "Hiring 1st Years").

#### B2. Add the photos

- [x] Create folder `src/assets/images/events/hiring-1st-year-2026/`.
- [x] Add `photo-1.jpeg`, `photo-2.jpeg`, `photo-3.jpeg`, `photo-4.jpeg` (same naming as the other event folders).

#### B3. Add the event entry in `src/data/events.js`

- [x] Add four image imports (`hiring1stPhoto1` ... `hiring1stPhoto4`) next to the existing `hiringPhoto*` imports.
- [x] Add a **new object** to `EVENTS` (do not copy-edit the 2nd/3rd year object in place; add alongside it):

  ```js
  {
    slug: 'hiring-1st-year-2026',
    category: 'Events',
    title: 'Hiring 1st Year Students',
    meta: 'Recruitment',
    date: '<Month Year>',
    hasResults: true,
    description: '<short card text>',
    photos: [hiring1stPhoto1, hiring1stPhoto2, hiring1stPhoto3, hiring1stPhoto4],
  }
  ```

- [x] The card appears automatically in Our Work > Events (`OurWork.jsx` maps over `EVENTS`) with **Read More** and **Results** buttons. Confirm both render.

#### B4. Read More page (one step deeper, with more content)

- [x] The page is `EventDetail.jsx` at `/our-work/hiring-1st-year-2026`. It currently shows only title, tag, date, `description` and the photos.
- [x] Add the richer content: the longer write-up (what the drive was, who could apply, which domains, how selection worked), shown on this page and **not** on the card.
- [x] Prefer adding an optional field to the event object (e.g. `details: [...]` paragraphs/sections) and rendering it in `EventDetail.jsx` **only when present**, so no other event page changes.
- [x] Confirm all **4 photos** show in the gallery grid.
- [x] Confirm the Results button shows on this page (it uses `hasResults`).
- [x] If you change `EventDetail.jsx`, tell Subham (shared file) and keep the change small and backwards compatible.

#### B5. Create `src/data/results-1st-year.json`

- [x] Use the agreed JSON shape, `slug: "hiring-1st-year-2026"`.
- [x] Fill in final/selected students per domain (Tech, Design, Photography, Marketing, Social Media). If a domain has none yet, leave `"selected": []`.
- [x] Do not copy names from `results-2nd-year.json`.

#### B6. Wire it into the Results page (after Subham has merged)

- [x] `git pull origin main` / rebase to get Subham's generic Results page and `src/data/results/index.js`.
- [x] Add exactly one import and one registry line for the 1st-year file in `src/data/results/index.js`.
- [x] Do **not** edit `Results.jsx`. If something is missing in it, ask Subham.
- [x] Open `/our-work/hiring-1st-year-2026/results` and confirm tabs, Tech default, and correct names.

#### B7. Verify and ship

- [x] Our Work > Events shows both hiring cards and each Read More / Results button goes to the right slug (1st year card must not open the 2nd/3rd year page or the other way round).
- [x] The **home page is unchanged** by this task (no new Results button/link; the home Events section is not part of this task).
- [x] Mobile check for the card, detail page and results tabs.
- [x] `npm run build` and `npm run lint` pass.
- [x] Add yourself to `CONTRIBUTORS.md`, open PR, link the issue.

---

### Quick difference summary (Subham vs Swapnil)

| Area | Subham | Swapnil |
| --- | --- | --- |
| Card | Already exists, just stop saying "pending" | Does not exist, create it |
| Read More page | Untouched | New content + 4 photos |
| Home page | **Remove** Hero results card + notification results link | Nothing |
| Results page code | **Rewrite** (tabs, Tech default, generic by slug) | Not touched; only adds a registry line |
| JSON | `results-2nd-year.json` | `results-1st-year.json` |
| Depends on the other? | No | Yes, for step B6 only (needs Subham's merge) |

---

## Round 3 — "Apply to Join": real application form + backend

Today "Apply to Join" does nothing useful: the Hero button is a plain `<button>` with no action, the navbar pill and mobile drawer link to the old `/our-work/hiring-1st-year-2026` event page, and "Apply Now" in `UpcomingEvents.jsx` is also a dead button. This round makes it real. Clicking **Apply to Join** opens a form; the answers go to a **FastAPI** backend, the text data is stored in **Neon (Postgres)**, the resume PDF is stored in **MinIO**, and the applicant gets a thank-you email through **Brevo SMTP**. This is the first backend and database the project has ever had.

### Team and ownership

| Person | Area | In one line |
|---|---|---|
| **Darsh** (lead) | Database, storage, email, CI/CD | Neon DB + schema, MinIO, Brevo email, GitHub Actions, deployment, final merge to `main`; also leads email integration across features |
| **Subham** | Frontend | `/apply` page and form UI, validation, success/error states, rewire every "Apply to Join" button — coordinates with Diganth if needed |
| **Diganth** | Backend | FastAPI app, the submit endpoint, validation, duplicate handling, rate limiting |
| **Swapnil** | Backend regression tests | All pytest regression tests (Groups 1–9) for the apply-service — **coordinates with Diganth** on the API behaviour |
| **Krishnapriya** | Integration | Connect frontend to backend for real, error mapping, env/CORS, full-stack local setup, end-to-end + contract tests |

### Branch strategy (read this first)

**Nothing from this feature goes to `main` until it all works.** Everything lands on one long-lived integration branch, and Darsh merges it into `main` at the very end.

- Integration branch: **`feat/apply-form`** (Darsh creates it from an up-to-date `main`).
- Everyone branches **off `feat/apply-form`** and opens PRs **into `feat/apply-form`** (set the *base branch* on GitHub; do **not** leave it on `main`). This is an intentional exception to `CONTRIBUTING.md`, which says PRs go to `main`.
  ```bash
  git checkout feat/apply-form
  git pull origin feat/apply-form
  git checkout -b feat/apply-form-ui      # example
  ```
- **Branch names must not use a slash after `feat/apply-form`.** Use `feat/apply-form-ui`, not `feat/apply-form/ui`. Git cannot have both a branch `feat/apply-form` and a branch `feat/apply-form/ui`.
- Sub-PRs are **squash-merged** into `feat/apply-form` after CI passes and one review.
- **Darsh keeps `feat/apply-form` in sync with `main`** (merge `main` into it) before work starts and again whenever anything new lands on `main`. Everyone then pulls `feat/apply-form` before starting the next PR. This avoids a giant conflict on the last day. Round 2 is already on `main` and this file already includes its ticked items, so merging `main` into `feat/apply-form` first keeps `TODO.md` conflict-free.
- **Only Darsh** opens and merges the final PR `feat/apply-form` → `main`, once everything works end to end.
- Still required from `CONTRIBUTING.md`: one GitHub issue per PR (`Closes #n`), `npm run build` passing, conventional commit prefixes, and a `CONTRIBUTORS.md` entry. For `CONTRIBUTORS.md` use your **real GitHub username and the real PR number**, no `<issue>` placeholders.
- **Never commit secrets.** `.env` files are already git-ignored. Share real credentials only through GitHub Secrets or a password manager, never in chat, issues or code.

### Dependency order (who can start when)

| Can start immediately | Needs something first |
|---|---|
| Darsh: **D0** provisioning, **D1** CI/infra, **D2** database schema (already built in `apply-service/db/schema.sql`, goes straight to `main`) | Darsh **D3** MinIO code, **D4** email code: need **B1** |
| Diganth: **B1** backend scaffold | Diganth **B2** endpoint: needs **B1** and **D2** (the schema); uses stand-ins for **D3/D4** until they land |
| Subham: **S1** form UI (against a mock API) | Diganth **B3**: needs **B2**, **D3**, **D4** |
| | Subham **S2** entry points: needs **S1** |
| | Krishnapriya **I1**: needs **S1** + **B2**; **I2**: needs **I1** + **D1** |
| | Darsh **D5** deploy: needs **B1**, **D2**; **D6** final merge: needs everything |

Parallel start: **D0/D1/D2, B1 and S1 begin on day one.** Services (D3, D4) are written against the interfaces below, so B2 does not have to wait for them.

---

### Folder structure (agreed target; the owner is in brackets)

```
turing-club/
├── .github/
│   └── workflows/
│       └── ci.yml                         [Darsh, D1]
├── apply-service/
│   ├── app/
│   │   ├── main.py                        FastAPI app, CORS, error handlers, routes [Diganth]
│   │   ├── config.py                      settings from environment variables [Diganth]
│   │   ├── schemas.py                     request/response models and validation rules [Diganth]
│   │   └── services/
│   │       ├── application_service.py     submit flow: validate, duplicate check, storage, DB, email [Diganth]
│   │       ├── storage.py                 MinIO upload / delete / presigned URL [Darsh, D3]
│   │       └── email.py                   Brevo SMTP confirmation email [Darsh, D4]
│   ├── db/
│   │   └── schema.sql                     database schema [Darsh, D2, done]
│   ├── tests/
│   │   ├── conftest.py, helpers.py        shared test setup [Darsh, exists; Diganth adds fixtures]
│   │   ├── test_schema.py                 schema tests [Darsh, exists]
│   │   └── test_*.py                      API regression tests [Diganth]
│   ├── .env.example  .gitignore  pytest.ini     (exist)
│   ├── requirements.txt
│   └── README.md
├── src/                                   existing frontend; only adds the Apply page and API client
│   ├── pages/Apply.jsx                    [Subham, S1]
│   └── api/applications.js                mock first [Subham], real fetch [Krishnapriya]
├── public/
├── package.json
└── vite.config.js
```

Additions to the sketch the team agreed on: `app/config.py`, `app/services/storage.py`, `app/services/email.py`, `db/schema.sql` and the existing test and config files. Database queries live inside `application_service.py`; if that file gets too big, split them into `app/db.py` and tell Darsh.

### Shared contracts (everyone codes against these; change them only after telling the team)

#### 1. Domains (fixed keys)

| Key | Label shown on the form |
|---|---|
| `technology` | Technology |
| `photography` | Photography |
| `design` | Design |
| `marketing` | Marketing (Outreach, PR, Events) |
| `social-media` | Social Media |

- An applicant can pick **one or more**. Marketing is **one** domain; "Outreach, PR, Events" is helper text, not three separate choices.
- Note: Round 2's results JSON uses the key `tech` for Technology. The apply form uses `technology`. If the two are ever joined, add an explicit mapping; do not silently rename either one.

#### 2. Field rules (backend is the source of truth; frontend mirrors them for fast feedback)

| Field | Required | Rule |
|---|---|---|
| `name` | Yes | Trimmed, 2 to 100 chars, letters, spaces and `. ' -` only |
| `usn` | Yes | **No fixed format** (USN changes every year, so never enforce a year/branch pattern). Trimmed, stored **uppercase**, letters and digits only, 5 to 20 chars. Limits live in one settings constant |
| `college_email` | **No** | Optional (people may not have one). Missing, empty or whitespace-only is fine and stored as `NULL`. If given, must be a valid email; **no domain restriction** |
| `personal_email` | Yes | Valid email, stored lowercase |
| `mobile` | Yes | Indian mobile: 10 digits starting 6 to 9. Accept `+91`, leading `0` and spaces, then **store 10 digits** |
| `domains` | Yes | 1 or more of the keys above, no duplicates |
| `resume` | Yes | **PDF only**, max **5 MB**, not empty. Backend must check the real file signature (starts with `%PDF-`), not just the extension or `Content-Type` |

#### 3. Database schema (owned by Darsh; Neon / Postgres)

```sql
applications
  id                         uuid primary key default gen_random_uuid()
  cycle                      text not null            -- e.g. '2026-hiring' (from env APPLICATION_CYCLE)
  name                       text not null
  usn                        text not null            -- uppercase
  college_email              text null
  personal_email             text not null
  mobile                     text not null            -- 10 digits
  resume_object_key          text not null            -- key inside the MinIO bucket
  resume_original_filename   text not null
  resume_size_bytes          integer not null
  confirmation_email_status  text not null default 'pending'   -- pending | sent | failed
  confirmation_email_sent_at timestamptz null
  created_at                 timestamptz not null default now()
  unique (usn, cycle)                                  -- one application per student per hiring cycle

application_domains
  application_id  uuid not null references applications(id) on delete cascade
  domain          text not null check (domain in ('technology','photography','design','marketing','social-media'))
  primary key (application_id, domain)
  -- plus an index on (domain) for per-domain listing
```

The `cycle` column lets the same student apply again in a later audition without being blocked as a duplicate.

#### 4. API contract

`POST /api/v1/applications` as `multipart/form-data`. Fields: `name`, `usn`, `college_email` (optional), `personal_email`, `mobile`, `domains` (**repeat the field once per domain**), `resume` (file).

| Status | When | Body |
|---|---|---|
| `201` | Saved | `{ "id": "<uuid>", "message": "Application received" }` |
| `422` | Any field invalid | `{ "error": "validation_error", "fields": { "usn": "Enter a valid USN", "domains": "Select at least one domain" } }` |
| `409` | Same USN already applied this cycle | `{ "error": "duplicate_application", "message": "You have already applied." }` |
| `413` | Resume over 5 MB | `{ "error": "file_too_large", "message": "Resume must be 5 MB or less." }` |
| `415` | Resume is not a real PDF | `{ "error": "invalid_file_type", "message": "Resume must be a PDF." }` |
| `429` | Too many requests | `{ "error": "rate_limited", "message": "..." }` |
| `500` | Anything unexpected | `{ "error": "server_error", "message": "Something went wrong. Please try again." }` |

`GET /api/v1/health` returns `{ "status": "ok" }`. FastAPI's default 422 shape is different, so Diganth must override it to the shape above; Subham and Krishnapriya depend on `fields` being a plain `{ fieldName: message }` map.

#### 5. Service interfaces (Darsh implements, Diganth calls)

```python
# apply-service/app/services/storage.py   (MinIO)
def upload_resume(application_id: str, cycle: str, data: bytes) -> str: ...   # returns object key
def delete_resume(object_key: str) -> None: ...
def presigned_resume_url(object_key: str, expires_seconds: int = 300) -> str: ...

# apply-service/app/services/email.py     (Brevo SMTP)
def send_confirmation_email(to: str, name: str, domains: list[str]) -> None: ...  # raises on failure
```

Until D3 and D4 merge, Diganth uses simple fakes with these exact signatures so nothing is blocked.

#### 6. Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | backend | Neon **pooled** connection string, `sslmode=require` |
| `DATABASE_URL_DIRECT` | schema setup | Neon **direct** (non-pooled) string, used only to run `db/schema.sql` and any later `ALTER` scripts |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` | backend | Bucket is `resumes`. Use a dedicated service account, not the root user |
| `BREVO_SMTP_HOST`, `BREVO_SMTP_PORT`, `BREVO_SMTP_LOGIN`, `BREVO_SMTP_KEY` | backend | Brevo SMTP relay; the **SMTP key**, not the account password |
| `EMAIL_FROM`, `EMAIL_FROM_NAME` | backend | Must be a sender verified in Brevo |
| `CORS_ORIGINS` | backend | Comma-separated allowed frontend origins, no `*` in production |
| `APPLICATION_CYCLE` | backend | e.g. `2026-hiring` |
| `MAX_RESUME_MB` | backend | Default `5` |
| `VITE_API_BASE_URL` | frontend | Public by design. **Never put a secret in any `VITE_` variable** |

Each side commits a `.env.example` listing these with fake values.

---

### DARSH: database, storage, email, CI/CD

**D0. Provisioning (no PR, do this first)**
- [ ] Create the Neon project. Use separate Neon **branches** (or projects) for `production`, `dev` and, optionally, throwaway CI testing. Note both the pooled and direct connection strings.
- [ ] Stand up MinIO (a server you control). Create the private bucket `resumes` (no public read). Create a service account limited to that bucket and keep the root credentials to yourself.
- [ ] Create the Brevo account, generate an **SMTP key**, and verify the sender. Authenticate the sending domain (SPF, DKIM, DMARC) so the thank-you mails don't land in spam. Check the current free-plan daily sending limit.
- [ ] Decide where the backend runs and create the GitHub issues for every PR below.
- [ ] Create `feat/apply-form`, and enable branch protection on it (CI required, 1 review).
- [ ] Put real credentials into GitHub Secrets / your password manager and share per-person dev credentials safely.

**D1. CI** (the workflow file is already written and tested, see `.github/workflows/ci.yml`; no Docker anywhere in this project)
- [ ] Commit `.github/workflows/ci.yml`. It runs on pull requests into, and pushes to, `main` and any `feat/**` branch:
  - **Frontend job:** `npm ci`, `npm run lint`, `npm test` (only if the script exists), `npm run build`.
  - **apply-service job:** installs PostgreSQL directly on the CI runner (no Docker), starts a local Postgres, installs `requirements.txt`, runs `ruff check` and `pytest` (the schema tests), then applies `db/schema.sql` twice with `psql` the way you do on Neon. It never touches Neon.
  - MinIO tests (D3) will be added to this job later, also without Docker (run the MinIO server binary on the runner).
- [ ] On GitHub: Settings, Branches, add a rule for `main` that requires the two CI checks (**Frontend (lint + build)** and **apply-service (lint + schema tests)**) to pass before merging.
- [ ] `.env.example` at root (backend vars) and a frontend `.env.example`.
- [ ] Commit the updated `.github/CODEOWNERS` (`/.github/` and `/apply-service/db/` are Darsh only).
- Done when: a test PR shows both CI checks running and green, and `main` requires them.

**D2. Database schema** (committed straight to `main`, no PR; built and tested already, see `apply-service/db/schema.sql`)
- [ ] Commit the `apply-service/` folder (`db/schema.sql`, `tests/`, `README.md`, `requirements.txt`, `pytest.ini`, `.env.example`, `.gitignore`) to `main`.
- [ ] Run `db/schema.sql` on the Neon **dev** branch using the **direct** URL (Neon SQL Editor or `psql -f`), then on production when ready. The file is safe to re-run and applies all-or-nothing.
- [ ] Add a CI step that runs `pytest` in `apply-service/` against the service Postgres (the schema tests).
- [ ] Note for Diganth: test the app on the **pooled** URL and watch for prepared-statement errors with async drivers (the pooler can cause them).
- [ ] Note for Diganth: Neon auto-suspends, so the first connection after idle is slow. Use connection retries / sensible timeouts.
- Rules for later changes: `schema.sql` always describes the final schema. Once tables exist on Neon, changes need matching `ALTER TABLE` statements run on dev, then production, plus an updated test in `apply-service/tests/test_schema.py`.
- Done when: a fresh empty database gets the full schema by running one file, in CI and on Neon dev, and the schema tests pass.

**D3. PR `feat/apply-minio-storage`** (needs B1 merged)
- [ ] Implement `apply-service/app/services/storage.py` per the interface above.
- [ ] Object key format: `resumes/{cycle}/{application_id}.pdf`. **Never** put the user's filename in the key.
- [ ] Short-lived presigned URLs for viewing a resume; the bucket stays private; the frontend never talks to MinIO.
- [ ] Script/step to create the bucket idempotently.
- [ ] Tests against a real MinIO server: upload, delete, presigned URL works, missing object handled.
- Done when: the tests pass in CI and a resume uploaded locally can be fetched with a presigned link.

**D4. PR `feat/apply-brevo-email`** (needs B1 merged)
- [ ] Implement `apply-service/app/services/email.py` using Brevo SMTP (host `smtp-relay.brevo.com`, port 587, STARTTLS).
- [ ] Email content: thank the applicant for registering and say we'll update them when the next auditions are announced. Mention their name and chosen domains. Provide both HTML and plain-text versions. Subject example: "Thanks for applying to The Turing Club".
- [ ] Sent to the **personal email**. The function raises on failure; the caller decides what to do (see B3).
- [ ] Tests with a mocked/fake SMTP server (no real emails in CI), covering success, auth failure and timeout.
- [ ] Send one real test email from `dev` and confirm it lands in inbox, not spam.
- Done when: tests pass and a real test mail arrives with correct sender and content.

**D5. PR `chore/apply-cd`** (needs B1, D2)
- [ ] A backend deploy workflow that runs on merge to `main`. No Docker; what it looks like depends on where the backend is hosted (decide this first).
- [ ] If a release includes schema changes (`ALTER` scripts), they are applied to the production database before the new version starts.
- [ ] Production env vars/secrets configured on the host; `CORS_ORIGINS` set to the real site; `VITE_API_BASE_URL` set on the frontend host.
- [ ] Post-deploy smoke test hitting `/api/v1/health`.
- [ ] Write down how to roll back.

**D6. Final merge (no sub-PR)**
- [ ] Merge `main` into `feat/apply-form`, resolve conflicts locally, and test the full flow end to end.
- [ ] Open the PR `feat/apply-form` → `main`; use a normal merge commit so each person's work stays visible in history.
- [ ] After deploy: submit one real application end to end in production and delete the test data.

---

### SUBHAM: frontend

All design must use the tokens from `src/index.css` (`bg-surface`, `border-border`, `text-primary-light`, ...). No hardcoded hex colors. Work on desktop and mobile. You do **not** need the backend to start.

**S1. PR `feat/apply-form-ui`** (base: `feat/apply-form`)
- [x] New route **`/apply`**: add the page (`src/pages/Apply.jsx`) and register it in `App.jsx`.
- [x] Build the form with these fields: Name, USN, College email (**marked optional**), Personal email, Mobile number, Resume (PDF upload), Domain (**multi-select**, at least one: Technology, Photography, Design, Marketing with helper text "Outreach, PR, Events", Social Media). Domains work well as selectable chips/cards. Use the keys and labels from the contract.
- [x] Client-side validation mirroring the field rules table: required fields, email format, 10-digit mobile, PDF only, 5 MB limit, at least one domain. Show errors under each field, only after the field is touched or on submit.
- [x] Submit button shows a loading state and is disabled while sending (prevents double submit).
- [x] **Success screen**: "Thanks for registering. We'll update you when the next auditions are announced." Mention that a confirmation email was sent to the personal email they entered.
- [x] **Error states**: field errors from the API (`422` `fields` map shown under the right inputs), a clear message for duplicate (`409`), file too large (`413`), wrong file type (`415`), and a generic retry message for `429` / `500` / network failure. Never show raw error text from the server.
- [x] Accessibility: real `<label>`s, `aria-invalid` and error text linked to inputs, keyboard-usable domain selection, visible focus.
- [x] All API access goes through **one function**: `submitApplication(formData)` in `src/api/applications.js`. For now it is a **mock** that returns the contract's success and error responses (switchable so you can test every error state). Krishnapriya replaces the mock with the real call in I1; do not hardcode URLs in components.
- [x] Add frontend tests (Vitest + React Testing Library): each validation rule, optional college email, multi-domain selection, success screen, and each error state. Add an `npm test` script so D1's CI can run it.
- [x] Mobile check at phone width: no horizontal scroll, upload control is usable.
- Done when: the form works fully against the mock, `npm run lint`, `npm test` and `npm run build` pass, and screenshots (desktop + mobile) are in the PR.

**S2. PR `feat/apply-entry-points`** (needs S1)
- [x] Point **every** "Apply to Join" entry at `/apply`:
  - `src/components/Hero.jsx` (currently a `<button>` with no action; make it a `<Link to="/apply">` or navigate)
  - `src/components/navbar/ActionPill.jsx` (currently links to `/our-work/hiring-1st-year-2026`)
  - `src/components/navbar/MobileNavDrawer.jsx` (same old link; keep `onClose` so the drawer closes)
  - `src/components/UpcomingEvents.jsx` ("Apply Now" button currently does nothing)
- [x] Run `grep -rn -i "apply" src` and confirm nothing still points to the old event page or to nothing.
- [x] Keep this PR small and separate. Round 2 already changed `Hero.jsx` on `main`, so make sure Darsh has merged `main` into `feat/apply-form` and pull it right before you start.
- Done when: every Apply button, on desktop and mobile, lands on `/apply`, and the Our Work event pages are untouched.

---

### DIGANTH: backend (FastAPI)

You own the API layer: routes, request validation, business flow. You do **not** write the database schema, MinIO code or email code (Darsh does, per the interfaces above); use fakes with the same signatures until those merge.

**B1. PR `feat/apply-backend-scaffold`** (base: `feat/apply-form`; start immediately)
- [ ] Inside the existing `apply-service/` folder add: the FastAPI app in `app/main.py`, settings loaded from environment variables in `app/config.py` (pydantic settings) using the variable names in the contract, your packages added (pinned) to the existing `requirements.txt`, and a `ruff.toml`. `pytest.ini` already exists.
- [ ] `GET /api/v1/health`.
- [ ] CORS middleware using `CORS_ORIGINS` (explicit origins, no `*`).
- [ ] Global error handlers that produce the contract's response shapes (`validation_error` with a `fields` map, `server_error`, etc.), replacing FastAPI's default 422 body.
- [ ] The shared fixtures and the **Group 1 tests** from "Mandatory regression tests (Diganth)" below.
- [ ] Follow the "Folder structure" section above. Yours: `app/main.py`, `app/config.py`, `app/schemas.py`, `app/services/application_service.py` and the API test files. Darsh's, don't edit: `app/services/storage.py`, `app/services/email.py`, `db/schema.sql`, `tests/test_schema.py`.
- Done when: `uvicorn` starts, `/api/v1/health` works, `pytest` and `ruff` pass in CI. **Merge this quickly; Darsh's D3 and D4 are waiting on it.**

**B2. PR `feat/apply-submit-endpoint`** (needs B1 + D2)
- [ ] `POST /api/v1/applications` per the contract: multipart form with repeated `domains` field and a `resume` file.
- [ ] Pydantic schemas in `app/schemas.py` implementing every rule in the field rules table: trimming, uppercase USN, lowercase emails, mobile normalization to 10 digits, domain whitelist, no duplicate domains.
- [ ] Resume checks: reject non-PDF (check the `%PDF-` signature, not only the extension), reject empty files, reject files over `MAX_RESUME_MB` (return `413`; don't read an unbounded upload into memory).
- [ ] Flow in `app/services/application_service.py`, in this order: validate, check duplicate (`usn` + `cycle`), upload resume via `storage.upload_resume`, insert application and domain rows in **one transaction**, return `201`. The route in `app/main.py` only calls this function.
- [ ] If the DB insert fails after the upload, **delete the uploaded object** (`storage.delete_resume`) so no orphan files remain.
- [ ] Two simultaneous submissions from the same USN must not both succeed: rely on the DB unique constraint, catch the integrity error and return `409`.
- [ ] Do not log personal data (names, USN, phones, emails). Log the application `id` only.
- [ ] **All tests in Groups 2 to 6** of "Mandatory regression tests (Diganth)" below (validation, resume, save flow, duplicates and concurrency, privacy and security), using the fakes for storage.
- Done when: all tests pass in CI and the endpoint can be called with curl/Postman against local Postgres.

**B3. PR `feat/apply-email-and-hardening`** (needs B2, D3, D4)
- [ ] Swap the fakes for the real storage and email services.
- [ ] After a successful save, send the confirmation email as a **background task**: the `201` must **not wait for** the email, and an email failure must **never** fail or roll back the application. Update `confirmation_email_status` (`sent` / `failed`) and `confirmation_email_sent_at`; log failures without personal data.
- [ ] Rate limiting on `POST /applications` (per IP) returning the `429` shape.
- [ ] **All tests in Groups 7 to 9** of "Mandatory regression tests (Diganth)" below (email, rate limiting, full flows). The whole suite (Groups 1 to 9) must pass together.
- Done when: the full flow works against local Postgres + MinIO and a real test email arrives; CI is green.

#### Mandatory regression tests (Diganth)

These tests are **required**. A backend PR cannot merge into `feat/apply-form` unless the tests assigned to it below exist and pass in CI. More tests are welcome. Rules:

- **No `skip`, `xfail` or deleting** a mandatory test without Darsh's approval. Parametrized cases (`@pytest.mark.parametrize`) count as one test with many cases, and are encouraged for the "many examples" tests.
- Use the names below (or an obviously equivalent name, mapped in the PR description in a small table: test name to ticked/passing).
- **Run against real Postgres** (Postgres installed on the CI runner). Storage and email are replaced by in-memory fakes (`fake_storage`, `fake_email`) that record calls and can be told to fail or be slow.
- **No real emails, no real MinIO writes, never the production Neon DB** in these tests.
- **Every bug found later gets a new regression test in the same PR that fixes it.**
- Test boundaries (min/max lengths, size limit) must use the constants from the settings module, not copied numbers, so a limit can change without rewriting tests.
- _Not covered here:_ the database schema (Darsh's D2), the real MinIO and real SMTP code (Darsh's D3 and D4), and browser/e2e flows (Krishnapriya's I2).
### Swapnil: All backend tests
**Files** (under `apply-service/tests/`): `conftest.py`, `test_health_config_errors.py`, `test_validation.py`, `test_resume.py`, `test_save_flow.py`, `test_duplicates.py`, `test_privacy_security.py`, `test_email.py`, `test_rate_limit.py`, `test_full_flows.py`.

**Fixtures in `conftest.py`** (B1/B2):
- [ ] `client` (FastAPI test client). A **real Postgres test database** setup already exists in `apply-service/tests/conftest.py` (`db_url`, `conn`). `TEST_DATABASE_URL` points at a local Postgres **server**; each test run creates a temporary database from `db/schema.sql` and drops it automatically. **Add your fixtures to that file; don't replace it.** Each test must stay isolated (rollback or truncate).
- [ ] `fake_storage`: in-memory, records `upload_resume` / `delete_resume` calls, can raise on demand.
- [ ] `fake_email`: records calls (`to`, `name`, `domains`), can raise or sleep on demand.
- [ ] `valid_payload()`: a complete valid form dict that tests then tweak one field at a time.
- [ ] `make_pdf(size_bytes)`: returns bytes that start with `%PDF-`, padded to the exact size.
- [ ] Settings override: fixed `APPLICATION_CYCLE`, small rate limit; **rate limiting disabled by default** and enabled only in `test_rate_limit.py`.

**About USN and college email (important for these tests)**
- **USN has no fixed format** (it changes every year), so the backend and these tests must **never** assert a year-, branch- or college-specific pattern. Rules are deliberately loose: trimmed, uppercased, letters and digits only, within a min/max length.
- **College email is optional** and has **no domain restriction**. People may or may not have one, so absent, empty and whitespace-only must all be fine and stored as `NULL`.

**Group 1: health, config, CORS, error shape** (required in **B1**)
- [ ] `test_health_returns_ok`
- [ ] `test_unknown_route_returns_json_404`
- [ ] `test_wrong_method_returns_json_405`
- [ ] `test_validation_error_uses_contract_shape` (`error` + `fields` map)
- [ ] `test_unexpected_exception_returns_500_contract_shape_without_internals`
- [ ] `test_app_fails_fast_when_required_env_missing`
- [ ] `test_cors_allows_configured_origin`
- [ ] `test_cors_blocks_unlisted_origin`
- [ ] `test_cors_preflight_options_succeeds`
- [ ] `test_cors_wildcard_origin_rejected_in_production_config`

**Group 2: field validation** (required in **B2**, file `test_validation.py`)

Name
- [ ] `test_name_required`
- [ ] `test_name_trimmed`
- [ ] `test_name_too_short_rejected`
- [ ] `test_name_too_long_rejected`
- [ ] `test_name_allows_dots_apostrophes_hyphens`
- [ ] `test_name_accepts_non_ascii_letters`
- [ ] `test_name_with_html_or_script_rejected`

USN (no fixed format)
- [ ] `test_usn_required`
- [ ] `test_usn_whitespace_only_rejected`
- [ ] `test_usn_trimmed_and_uppercased`
- [ ] `test_usn_accepts_many_different_formats` (parametrized: old-style, new-style, all digits, letters-first, shortest and longest allowed; proves no year/branch pattern is enforced)
- [ ] `test_usn_boundary_lengths_accepted` (exactly min and exactly max)
- [ ] `test_usn_too_short_rejected`
- [ ] `test_usn_too_long_rejected`
- [ ] `test_usn_inner_spaces_rejected`
- [ ] `test_usn_special_characters_rejected` (parametrized: `<script>`, SQL-looking text, `../`, emoji, punctuation)

College email (optional)
- [ ] `test_college_email_omitted_is_ok` (field missing entirely, stored `NULL`)
- [ ] `test_college_email_empty_string_stored_as_null`
- [ ] `test_college_email_whitespace_only_stored_as_null`
- [ ] `test_college_email_valid_is_stored_trimmed_and_lowercase`
- [ ] `test_college_email_invalid_rejected`
- [ ] `test_college_email_any_domain_accepted` (no domain restriction)
- [ ] `test_college_email_same_as_personal_email_is_ok`

Personal email
- [ ] `test_personal_email_required`
- [ ] `test_personal_email_invalid_rejected` (parametrized: no `@`, double `@`, spaces, no domain, trailing dot)
- [ ] `test_personal_email_trimmed_and_lowercased`
- [ ] `test_personal_email_plus_addressing_accepted`

Mobile
- [ ] `test_mobile_required`
- [ ] `test_mobile_ten_digits_accepted`
- [ ] `test_mobile_plus91_prefix_normalized_to_ten_digits`
- [ ] `test_mobile_leading_zero_normalized_to_ten_digits`
- [ ] `test_mobile_spaces_and_dashes_normalized`
- [ ] `test_mobile_starting_with_0_to_5_rejected`
- [ ] `test_mobile_too_short_rejected`
- [ ] `test_mobile_too_long_rejected`
- [ ] `test_mobile_with_letters_rejected`

Domains
- [ ] `test_domains_required`
- [ ] `test_domains_empty_list_rejected`
- [ ] `test_domains_single_accepted`
- [ ] `test_domains_multiple_accepted`
- [ ] `test_domains_all_five_accepted`
- [ ] `test_domains_order_does_not_matter`
- [ ] `test_domains_unknown_key_rejected`
- [ ] `test_domains_wrong_case_rejected` (e.g. `Technology` instead of `technology`)
- [ ] `test_domains_duplicate_value_rejected`
- [ ] `test_domains_saved_rows_match_selection_exactly` (one `application_domains` row per chosen domain)

Whole-request behaviour
- [ ] `test_multiple_invalid_fields_reported_together`
- [ ] `test_error_fields_keyed_by_field_name`
- [ ] `test_validation_failure_writes_nothing` (no DB row, no storage call, no email call)
- [ ] `test_success_response_has_only_id_and_message`
- [ ] `test_unknown_extra_form_fields_ignored`
- [ ] `test_json_body_instead_of_multipart_returns_clean_422_not_500`

**Group 3: resume upload** (required in **B2**, file `test_resume.py`)
- [ ] `test_resume_required`
- [ ] `test_valid_pdf_accepted`
- [ ] `test_pdf_exactly_at_size_limit_accepted`
- [ ] `test_pdf_one_byte_over_limit_returns_413`
- [ ] `test_oversized_upload_never_reaches_storage`
- [ ] `test_empty_file_rejected`
- [ ] `test_non_pdf_with_pdf_extension_returns_415`
- [ ] `test_spoofed_pdf_content_type_with_non_pdf_bytes_returns_415`
- [ ] `test_other_file_types_rejected_415` (parametrized: image, docx, zip, exe, text)
- [ ] `test_resume_filename_with_path_traversal_is_handled_safely`
- [ ] `test_resume_filename_unicode_and_very_long_handled`
- [ ] `test_object_key_never_contains_original_filename`
- [ ] `test_object_key_format_uses_cycle_and_application_id`

**Group 4: save flow and data integrity** (required in **B2**, file `test_save_flow.py`)
- [ ] `test_successful_application_creates_exactly_one_application_row`
- [ ] `test_application_row_stores_normalized_values` (uppercase USN, lowercase emails, 10-digit mobile)
- [ ] `test_application_id_is_valid_uuid`
- [ ] `test_cycle_taken_from_config`
- [ ] `test_resume_metadata_saved` (object key, original filename, size)
- [ ] `test_confirmation_email_status_starts_as_pending`
- [ ] `test_application_and_domain_rows_commit_together` (force the domain insert to fail, expect no application row either)
- [ ] `test_db_failure_after_upload_deletes_uploaded_resume`
- [ ] `test_db_failure_returns_clean_500_with_no_partial_rows`
- [ ] `test_storage_failure_returns_clean_500_and_no_db_row`
- [ ] `test_storage_cleanup_failure_is_logged_and_does_not_mask_original_error`
- [ ] `test_database_unavailable_returns_500_without_crashing_the_app`

**Group 5: duplicates and concurrency** (required in **B2**, file `test_duplicates.py`)
- [ ] `test_second_application_same_usn_same_cycle_returns_409`
- [ ] `test_duplicate_usn_different_case_returns_409`
- [ ] `test_duplicate_usn_with_surrounding_spaces_returns_409`
- [ ] `test_same_usn_in_different_cycle_is_allowed`
- [ ] `test_different_usn_same_personal_email_is_allowed` (uniqueness is on USN + cycle only)
- [ ] `test_duplicate_leaves_no_orphan_resume_in_storage`
- [ ] `test_duplicate_does_not_send_email`
- [ ] `test_duplicate_does_not_modify_the_first_application`
- [ ] `test_concurrent_submissions_same_usn_only_one_succeeds` (several parallel requests: exactly one `201`, the rest `409`, exactly one row)
- [ ] `test_concurrent_duplicates_leave_no_orphan_objects`

**Group 6: privacy and security** (required in **B2**, file `test_privacy_security.py`)
- [ ] `test_logs_never_contain_name_usn_phone_or_email` (capture logs across success, validation failure and 500)
- [ ] `test_responses_never_echo_personal_data` (success and error bodies)
- [ ] `test_sql_injection_payloads_rejected_or_stored_as_plain_data_and_tables_intact`
- [ ] `test_500_response_has_no_stack_trace_or_connection_string`

**Group 7: confirmation email** (required in **B3**, file `test_email.py`)
- [ ] `test_confirmation_email_triggered_after_successful_save`
- [ ] `test_email_sent_to_personal_email_only` (never to the college email)
- [ ] `test_email_called_with_normalized_name_and_selected_domains`
- [ ] `test_email_failure_still_returns_201`
- [ ] `test_email_failure_sets_status_failed_and_keeps_application`
- [ ] `test_email_success_sets_status_sent_and_timestamp`
- [ ] `test_slow_email_does_not_delay_the_201_response`
- [ ] `test_email_not_sent_when_validation_fails`
- [ ] `test_email_not_sent_when_storage_fails`
- [ ] `test_email_failure_logged_without_personal_data`

**Group 8: rate limiting** (required in **B3**, file `test_rate_limit.py`)
- [ ] `test_requests_under_limit_succeed`
- [ ] `test_request_over_limit_returns_429_contract_shape`
- [ ] `test_rate_limit_is_per_client_ip`
- [ ] `test_rate_limit_resets_after_window` (freeze/advance time, don't sleep)
- [ ] `test_rate_limited_request_writes_nothing`
- [ ] `test_health_endpoint_is_not_rate_limited`
- [ ] `test_spoofed_forwarded_header_does_not_bypass_limit`

**Group 9: full flows** (required in **B3**, file `test_full_flows.py`)
- [ ] `test_full_happy_path_all_fields_all_five_domains` (DB rows, storage call, email call, `201`)
- [ ] `test_minimal_application_no_college_email_one_domain`
- [ ] `test_realistic_applicant_matrix` (parametrized set of different-looking but valid applicants, including different USN shapes)

---

### KRISHNAPRIYA: integration

You make sure the frontend and backend actually work **together**, and that they stay in sync in the future. Mismatches between the two (field names, error shapes, domain keys) are your bugs to find.

**I1. PR `feat/apply-integration`** (needs S1 + B2)
- [ ] Replace the mock in `src/api/applications.js` with the real `fetch` call: `multipart/form-data` to `${VITE_API_BASE_URL}/api/v1/applications`, with `domains` appended once per selected domain. (Do not set the `Content-Type` header manually for `FormData`; the browser adds the boundary.)
- [ ] Map every response in the contract to what the form expects: `422` `fields` to per-field errors, `409`, `413`, `415`, `429`, `500`, and network failure / timeout.
- [ ] Keep the mock available behind an env flag so Subham can still develop the UI offline.
- [ ] Local dev setup: either a Vite dev proxy or confirmed CORS so `npm run dev` + the local backend work with no browser errors. Document the exact steps.
- [ ] Verify CORS from the real frontend origin, including the preflight request.
- [ ] Check field-name and domain-key parity between frontend and backend; any mismatch is fixed with the owner of that side.
- Done when: submitting the real form on your machine creates a row, uploads the resume and shows the success screen, and each error state shows correctly.

**I2. PR `test/apply-e2e`** (needs I1 + D1)
- [ ] Full-stack run on a developer machine (Postgres + MinIO + backend + frontend, started without Docker), with the steps documented in the README.
- [ ] End-to-end tests (Playwright suggested): fill and submit the form with a real PDF, assert the success screen; assert a row in `applications` and `application_domains`, the object exists in MinIO, and the confirmation email was triggered (use a fake SMTP in this environment).
- [ ] End-to-end error cases: duplicate USN, non-PDF, oversized file, no domain selected, backend down.
- [ ] **Contract test**: one test that fails if the frontend's domain list/keys and the backend's allowed domains ever differ.
- [ ] Add the e2e job to CI (coordinate with Darsh, who owns the workflows).
- Done when: the e2e suite runs green in CI on a clean checkout.

---

### Testing (regression safety, shared)

- **Backend** (Diganth writes, Darsh's CI runs): pytest with real Postgres and MinIO servers. Cover every field rule, all error statuses, duplicate and race handling, resume cleanup on failure, email failure not failing the request, and rate limiting. Services (email/storage) are tested in isolation by Darsh.
- **Frontend** (Subham): Vitest + React Testing Library for form validation and the success/error states.
- **Integration** (Krishnapriya): Playwright end-to-end plus the contract test.
- **Rules:** CI must pass before any PR merges into `feat/apply-form` or `main`. **Every bug found later gets a regression test in the same PR that fixes it.** CI never talks to the production Neon database or sends real emails.

## Notes

- Keep all new work following `CONTRIBUTING.md` (branch naming, PR template, code style)
- Update this file as items are completed or new ones come up