# course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy, PostgreSQL, Alembic migrations,
GraphQL on Strawberry, and JWT login with roles (Labs 4–9, "Advanced Web Technologies").

## How to run

You need Python 3.11 or newer and PostgreSQL 16 or newer.

Once, as the `postgres` superuser, create the role and the database:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Then, from the project folder:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy .env.example to .env and fill in the values
cp .env.example .env
# Edit .env: set DATABASE_URL and generate SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"

# 4. Apply migrations
alembic upgrade head

# 5. Load seed data
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql

# 6. Create demo users (must run after every seed.sql)
python seed_users.py

# 7. Start the server
fastapi dev main.py
```

REST docs: http://localhost:8000/docs. GraphiQL: http://localhost:8000/graphql.

Demo users (teaching passwords; a real project never publishes them):

| E-mail | Role | Password |
|--------|------|----------|
| admin@example.com | admin | admin-demo-password |
| aigerim@example.com | student (student 1) | aigerim-demo-pass |
| daniyar@example.com | student (student 2) | daniyar-demo-pass |
| asel@example.com | student (student 3) | asel-demo-password |

`seed.sql` also clears `users`: after it, always run `python seed_users.py`.

## Access matrix

The codes come from `python try_access.py` (14 of 14 as expected). The "—" cell: the
administrator has no student profile, so there is nobody to enroll "for yourself".

| Request | Anonymous | Student | Administrator |
|---------|-----------|---------|---------------|
| `GET /courses` | 200 | 200 | 200 |
| `GET /me` | 401 | 200 | 200 |
| `GET /enrollments` | 401 | 403 | 200 |
| `POST /enrollments`, for yourself | 401 | 201 | — |
| `POST /enrollments`, for another | 401 | 403 | 201 |

## Open spots

Found by `scan_routes.py` and `scan_graphql.py`; not closed in this lab.

| Route or field | Verdict | How to close it |
|----------------|---------|-----------------|
| `GET /` | by design: health check, no data | no need to close it |
| `GET /courses` | by design: the catalog is open to everyone | no need to close it |
| `GET /courses/{id}` | by design: a single course is public | no need to close it |
| `POST /courses/{id}/like` | a hole: an anonymous caller inflates the counter | `CurrentUser` dependency, one like per user |
| `POST /students` | a hole: anyone can create student profiles | `AdminUser` or `CurrentUser` with self-registration logic |
| `GET /students/{id}` | a hole: returns email to anyone | `CurrentUser` + `IsSelfOrAdmin` check |
| `GET /students/{id}/enrollments` | a hole: anyone can see another student's courses | `CurrentUser` + `can_access_student` check |
| `GET /stats/courses` | by design: aggregate stats are public | no need to close it |
| GraphQL `courses` | by design: the catalog is public | no need to close it |
| GraphQL `course` | by design: a single course is public | no need to close it |
| GraphQL `student` | a hole: name is public but enrollment path leaks data | `CurrentUser` in context + check in resolver |
| GraphQL `enrollments` | a hole: lists all students' enrollments | `IsAdmin` permission on the query |
| GraphQL `Course.enrollments` | a hole: anyone sees who is in a course | `IsAuthenticated` on the field |
| GraphQL `Student.enrollments` | a hole: anyone traverses to student's courses | `IsSelfOrAdmin` on the field |
| GraphQL `enroll` | a hole: anyone can enroll any student | `IsAuthenticated` + owner check via `can_access_student` |
| GraphQL `likeCourse` | a hole: anonymous caller inflates the counter | `IsAuthenticated` permission on the mutation |

## Threat table

| Where | What can break | How it is covered | How I checked |
|-------|----------------|-------------------|---------------|
| The login form | Same error text hides whether email exists; timing leak reveals registered addresses | `DUMMY_HASH` is verified even when no user is found, equalizing response time; same error text "Incorrect email or password" for all failures | `try_auth.py` (6/6); `try_timing.py` — both medians within a few ms of each other (~99 ms) |
| Passwords and the key | Leaked DB exposes passwords; missing key lets app start insecurely | Argon2id hashes (m=65536, t=3, p=4); `SECRET_KEY` has `min_length=32`, no default — app refuses to start without it; `.env` is in `.gitignore` | `check_users.py` (4/4); experiment 1 — `ValidationError` without key or with short key |
| Token and role | Forged, expired, or unsigned tokens; role in token stays stale after DB change | PyJWT with `algorithms=["HS256"]`, `issuer`, `require=["exp","sub","iss"]`; role read from DB on every request, not from token | `try_tokens.py` (9/9); experiment 3 — 8 forgeries all rejected; experiment 4 — role change in DB takes effect immediately |
| Permissions on objects | BOLA: student enrolls another student; anonymous reads all enrollments; GraphQL path bypass | `can_access_student` in `POST /enrollments`; `AdminUser` on `GET /enrollments`; `IsSelfOrAdmin` on `Student.email` field (not just on query) | `try_access.py` (14/14); experiment 5 — removing owner check shows 201 for another student; experiment 6a — closing only the `students` query still exposes email via `student(id)` |
| Cookie and Next.js | XSS steals token from localStorage; CSRF; forged cookie bypasses proxy | Token in `httpOnly` cookie (not JS-accessible); `SameSite=Lax`; `Secure`; two-layer check: `proxy.ts` (cookie exists?) + `verifySession()` (API validates token) | Browser DevTools: `document.cookie` returns `""`; experiment 7 — forged cookie passes proxy but `verifySession()` redirects to `/login` |
| Logout and lifetime | Token stays valid after logout until `exp` (15 min) | Cookie deleted on logout; token is short-lived (15 min) | Experiment 8 — copied token still works at API after browser logout |

Deliberately not closed:

- **Login brute force**: There is no limit on failed login attempts. A per-IP or per-email counter could be stored in Redis or a DB table. A per-email-only limit is dangerous: an attacker can lock out any user by sending wrong passwords to their address. With multiple server processes, the counter must live in a shared store (Redis), not process memory.

- **Token after logout**: The token remains valid for up to 15 minutes after the browser cookie is deleted. Options: (1) a `token_version` column in `users` — incremented at logout, checked on every request (one extra DB read); (2) a `jti` blacklist in Redis — allows per-device revocation but needs fast storage; (3) shorter lifetime (e.g. 5 min) with a long-lived refresh token stored in DB. For this project `token_version` is the best balance: one extra column, one extra read, full revocation on logout.

## Experiment log

| No. | Experiment | What I saw | Cause | How I fixed it |
|-----|------------|------------|-------|----------------|
| 1 | No key / short key; two hashes of same password | `ValidationError: Field required` without key; `String should have at least 32 characters` with short key; two hashes differ despite same input | `Field(min_length=32)` with no default forces validation; Argon2id uses a random salt per hash | Restored the real 64-char key in `.env` |
| 2 | Login time with and without `DUMMY_HASH` | With protection: unknown ≈ 99 ms, known ≈ 99 ms (< 1 ms diff). Without: unknown ≈ 4 ms, known ≈ 97 ms (~24× faster) | Without `DUMMY_HASH`, returning `None` early skips the expensive Argon2 hash computation | Kept `DUMMY_HASH` path: `hashed = user.password_hash if user else DUMMY_HASH` |
| 3 | Nine forged tokens; signature check off | All 9 forgeries rejected (9/9). With `verify_signature: False`: 6 FAILs — expired, wrong key, wrong issuer, no exp, edited payload, alg:none all accepted; forged admin token returned `admin@example.com` | `algorithms=`, `issuer=`, `require=` each stop one class of attack; disabling signature check removes all of them simultaneously | Restored `jwt.decode` with all three arguments via `git restore security.py` |
| 4 | Role changes in DB, same token | Before: `GET /enrollments` returns 200. After `UPDATE users SET role='student'`: same token returns 403 immediately. Reverting to `admin`: 200 again | Role is loaded from DB on every request in `get_optional_user`; token only carries `sub` (user id) | No fix needed — this is the intended behavior |
| 5 | Owner check removed from `POST /enrollments` | `try_access.py`: 13/14, cell "POST /enrollments, for another / student" shows `201 (want 403)`. Aigerim could enroll Daniyar without his consent | The 3-line `if not can_access_student(...)` block was commented out | Restored via `git restore main.py` |
| 6 | Path closed, not field (a); closed field not nullable (b) | (a) 7/9: `student(id:2).email` and `enrollments→student.email` leak Daniyar's email via non-`students` paths. (b) 7/9: `student(2)` returns `null` entirely — name is also lost; `enrollments` returns `{"data":null}` | (a) Permission only on `students` query, not on the `email` field of `StudentType`. (b) Non-nullable field raises error that propagates up the tree | Restored `IsSelfOrAdmin` on `email: Optional[str]` via `git restore graphql_api.py` |
| 7 | Forged cookie vs real check | Without cookie: `proxy.ts` redirects immediately, API never called. With `session=forged.token.value`: proxy passes, page calls `verifySession()`, API returns 401, redirect to `/login` | `proxy.ts` only checks cookie existence; `verifySession()` calls `GET /me` for real validation | Restored `verifySession()` call in account page via `git restore` |
| 8 | Token after logout | After logout cookie is deleted; `/account` redirects to `/login`. But copied token value still returns 200 from `GET /me` for up to 15 minutes | JWT is stateless; server has no revocation list; deleting the cookie only removes client-side access | No fix in this lab. Mitigation: `token_version` column (see threat table) |

## Decisions

- **Role from DB, not token**: Reading `user.role` from the database on every request costs one extra `SELECT` per authenticated call. The benefit is instant revocation: promoting or demoting a user takes effect on the very next request without waiting for token expiry. For a system where role changes happen rarely (once a year), the DB read is an acceptable price. For extremely high-traffic systems, putting the role in the token with a 5-minute lifetime is a reasonable trade-off.

- **Nullable field + permission on the type, not the query**: A closed field must have type `Optional[str]` (allowing `null`) so that a denial replaces just the field value with `null` and an error entry — not the entire parent object. The check is on `Student.email` (the field of the type), not on `Query.student` (the root query), because the same `StudentType` is reachable through multiple paths: `student(id)`, `enrollments → student`, `courses → enrollments → student`. A check only on the root query leaves all other paths open (experiment 6a showed this).

- **`proxy.ts` as first line, `verifySession()` as the real guard**: `proxy.ts` checks only that a cookie named `session` exists. It cannot verify the token without calling the API, and doing so on every route request would add latency and couple the proxy to the backend. Its job is to redirect clearly unauthenticated users (no cookie) quickly. `verifySession()` sits next to the data and performs the real check: it presents the token to the API, which verifies the signature, expiry, issuer, and the user's existence in the database. This is the only check that matters for security. A page that calls `verifySession()` is safe even if `proxy.ts` is bypassed (experiment 7b showed that removing `verifySession()` while keeping `proxy.ts` lets a forged cookie through).
