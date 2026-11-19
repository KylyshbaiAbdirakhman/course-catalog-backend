# course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic migrations,
and GraphQL on Strawberry (Labs 4–8, "Advanced Web Technologies").

## How to run

You need Python 3.11 or newer and PostgreSQL 16 or newer.

Once, as the `postgres` superuser:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

From the project folder:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

alembic upgrade head
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
fastapi dev main.py
```

REST docs: http://localhost:8000/docs  
GraphiQL: http://localhost:8000/graphql

Password `change-me` is for teaching only.

## What changed in the API (Lab 8)

- **REST errors** now use the Problem Details format (RFC 9457): `application/problem+json`,
  with a `type` field like `https://example.com/problems/course-not-found`. Rules live in
  `services.py`; `problem.py` translates codes into HTTP responses.
- **`/graphql`** is a second entrance to the same database. GraphiQL opens in a browser.
  The schema has `Course`, `Student`, `Enrollment` types and nested queries.
- **Mutations** `enroll` and `likeCourse` return `userErrors` for expected rule errors
  (duplicate enrollment, unknown course). Unexpected errors stay in `errors`.
- **`X-SQL-Queries`** header on every response counts how many SQL queries the server ran.
- **Protection**: query depth ≤ 5, aliases ≤ 10, `limit` checked (1–100), `id` validated,
  internal error text hidden. `GRAPHQL_INTROSPECTION=false` disables introspection.
- **New REST routes**: `GET /students/{id}` and `GET /students/{id}/enrollments`.

## Example queries

The "My courses" query (Variables: `{"id": "2"}`):

```graphql
query MyCourses($id: ID!) {
  student(id: $id) {
    name
    enrollments { id course { title credits level } }
  }
}
```

The `enroll` mutation — first call succeeds, second returns `userErrors`:

```graphql
mutation Enroll($input: EnrollInput!) {
  enroll(input: $input) {
    enrollment { id enrolledAt course { title } }
    userErrors { code message }
  }
}
```

Answer on a repeated enrollment:

```json
{
  "data": {
    "enroll": {
      "enrollment": null,
      "userErrors": [{"code": "ALREADY_ENROLLED", "message": "Student is already enrolled in this course"}]
    }
  }
}
```

## REST vs GraphQL comparison

The "My courses" screen of student 2; numbers from `measure.py`, starting data.

| Criterion | REST | GraphQL | Source |
|-----------|------|---------|--------|
| Requests and rounds per screen | 5 requests, 2 rounds | 1 request, 1 round | `measure.py`, step 8 |
| Bytes in the responses | ~1160 bytes | ~339 bytes | `measure.py`, step 8 |
| SQL queries per screen | 5 | 3 | `measure.py`, `X-SQL-Queries` |
| SQL growth with more students | grows with courses count | always 3 (DataLoaders) | `try_n_plus_1.py`, exp. 4–5 |
| Error in the query text | 404 for unknown path, 422 for bad params | status 200, `errors` key, `data: null` | experiments 1 and 8 |
| Expected rule error (repeated enrollment) | 409, `application/problem+json`, `type .../already-enrolled` | 200, `userErrors[0].code = ALREADY_ENROLLED` | steps 1 and 4 |
| HTTP cache | GET responses can be cached by URL | POST /graphql can't be cached by default | lecture section 14 |
| Protection from expensive queries | rate limiter per route | depth + alias limits, argument checks | experiments 6 and 7 |

**Conclusion.** Simple list screens (courses, enrollments) stay well on REST: one route,
one query, easy to cache by URL. For personal screens like "My courses" GraphQL wins: one
request instead of five, only the needed fields (339 vs 1160 bytes), and SQL queries stay
constant regardless of how many courses the student has. GraphQL pays off when the client
needs data from several related resources in one round-trip.

## Experiment log

| # | Experiment | What I saw | Cause | How I fixed it |
|---|---|---|---|---|
| 1 | Typo `titel` in field name, `is_elective` instead of `isElective` | Status 200, `errors` key, `data: null`, "Did you mean…" hint | Engine validates query against schema before execution | Fixed to `title` and `isElective` |
| 2 | Removed `\| None` from `course` query, asked for nonexistent course | `"Cannot return null for non-nullable field Query.course"`, `data: null` | Broken promise: schema said `!` but resolver returned null — null propagated up | Restored `\| None` |
| 3 | Mutation sent with GET method | HTTP 400, plain text `"mutations are not allowed when using GET"` | GET is a safe method; mutations change data and must use POST | Used POST |
| 4 | Ran `more_students.sql`, re-ran `try_n_plus_1.py` | 7→27 and 7→24 queries for 3→20 students | Lazy loading: one DB query per object per level | Added DataLoaders (step 6) |
| 5 | Batch function returned rows sorted by column desc, without grouping by key | First query: `WrongNumberOfResultsReturned`. Second query (enrollments→course): silent wrong data — 4 of 6 enrollments showed wrong course | Length matched by accident; rows not in key order | Restored `groups` dict: match rows to keys by value |
| 6 | Six dangerous queries without protection then with it | Without: DB errors leaked SQL text and params. With: short safe messages, 0 SQL for flood | Unhandled exceptions expose internals; extensions block before execution | Added `QueryDepthLimiter`, `MaxAliasesLimiter`, `MaskErrors`, argument checks |
| 7 | `GRAPHQL_INTROSPECTION=false`, sent `__schema` query, then typo | `__schema` rejected. Typo still showed "Did you mean…" | Introspection hides the schema map but not individual field names | Restored `GRAPHQL_INTROSPECTION=true` |
| 8 | Typo in query / removed `errors` check / API stopped | GraphQLRequestError with field name / TypeError destructuring null / fetch failed | Without errors check status 200 hides the real error; no server = no response | Restored checks |

## Decisions

- **Rules in `services.py`, REST and GraphQL translate codes separately**: if logic lived
  in both layers it would drift apart. One `ServiceError("ALREADY_ENROLLED", …)` becomes
  409 + Problem Details in REST and `userErrors[0].code` in GraphQL — from the same code path.

- **Loaders created in `Context` per request, batch function matches by value not position**:
  a single app-wide loader would cache stale data and mix users' results. Matching by value
  (the `groups` dict) is required because the database doesn't guarantee row order matching
  key order — experiment 5 showed silent wrong data when relying on position.

- **Two-layer protection — `check_limit`/`parse_id` + `MaskErrors`**: the first layer gives
  the client a clear actionable message ("limit must be between 1 and 100", "Invalid ID: 'abc'").
  `MaskErrors` covers everything else — unforeseen DB errors, bugs — with "Unexpected error."
  so the client never sees SQL text, table names, or stack traces.
