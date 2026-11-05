# course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy 2.0, PostgreSQL, and Alembic migrations
(Labs 4–7 of "Advanced Web Technologies").

## How to run

You need Python 3.11 or newer and PostgreSQL 16 or newer.

Once, as the `postgres` superuser, create the role and the database:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Then, from the project folder:

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env from the example
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux

# 4. Apply migrations (creates all tables)
alembic upgrade head

# 5. Load initial data
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql

# 6. Start the server
fastapi dev main.py
```

API docs: http://localhost:8000/docs

Password `change-me` is for teaching only; never put real passwords into the repository.

## What changed in the API (Lab 7)

- **Data is now stored in PostgreSQL** — it survives server restarts.
- **`POST /enrollments`** now takes `studentId` (integer) instead of `studentName`.
- **New routes**: `POST /students` (create a student), `GET /stats/courses` (enrollment counts per course).
- **`GET /enrollments`** now returns `courseTitle` and `studentName` via a JOIN.
- **`level` field** added to courses (`beginner` / `intermediate`); `GET /courses` accepts `?level=` filter.
- **Database constraint violations** return proper HTTP responses: 409 Conflict for duplicates, 404 Not Found for missing foreign keys.

## Migrations

| Command | What it does |
|---------|--------------|
| `alembic upgrade head` | applies all missing migrations |
| `alembic downgrade -1` | rolls back the last migration |
| `alembic current` | shows the current database version |
| `alembic history` | shows the migration chain |
| `alembic revision --autogenerate -m "text"` | generates a draft migration from models vs database |
| `alembic check` | reports whether models and database have diverged |
| `alembic upgrade 0001:0002 --sql` | prints SQL of a migration without running it |
| `alembic stamp head` | marks database as up to date without running migrations |

## Experiment log

| # | Experiment | What I saw | Cause | How I fixed it |
|---|---|---|---|---|
| 1 | Changed `uq` template in `naming_convention` | `names only in models: ['enrollments_course_id_unique', 'students_email_unique']` | Template must produce `_key` suffix to match PostgreSQL | Restored `%(table_name)s_%(column_0_N_name)s_key` |
| 2 | Removed `min_length=2` from `StudentIn`, sent name `N` | `500 Internal Server Error` — `students_name_check` not in dict | Pydantic no longer caught it; DB CHECK fired but handler didn't know the name | Restored `Field(min_length=2)` |
| 3 | Typo in constraint name key: `students_email_uniq` | `500 Internal Server Error` | Dict lookup failed; unknown violation re-raised as 500 | Fixed key to `students_email_key` |
| 4 | `ALTER TABLE courses ALTER COLUMN title DROP NOT NULL` manually | `alembic check` → `Detected NOT NULL on column 'courses.title'` FAILED | Model says NOT NULL but database doesn't | `ALTER TABLE courses ALTER COLUMN title SET NOT NULL` |
| 5 | Auto-generated migration 0002 with `nullable=False` on existing data | `IntegrityError: column "level" contains null values` | Cannot add NOT NULL column to table with existing rows | Rewrote upgrade() as 3 steps: add nullable → UPDATE → set NOT NULL |
| 6 | Commented out `import models` in `env.py` | Alembic proposed to DROP all 3 tables | Without import, Base.metadata is empty | Restored `import models` |
| 7 | Added `phone: Mapped[str \| None]` to Student without migration | `alembic check` → `Detected added column 'students.phone'` FAILED | Model ahead of database | Removed `phone` field from model |
| 8 | Created two revisions from same base, got two heads | `alembic upgrade head` failed: `Multiple head revisions are present` | Two branches in migration history | `alembic merge heads`, then deleted experimental files |

## Decisions

- **Response chosen by constraint name, not SQLSTATE**: SQLSTATE `23505` fires for ANY unique constraint. The constraint name (`students_email_key` vs `enrollments_course_id_student_id_key`) tells us exactly which rule fired. Catching after `commit()` avoids race conditions — a `SELECT` check before insert can become stale before the insert completes.

- **Like incremented with `UPDATE SET likes = likes + 1`**: Two simultaneous requests both reading `11` and both writing `12` would lose one like. `likes + 1` executes atomically in the database with a row lock — the second request waits, reads `12`, writes `13`.

- **Migration 0002 split into three steps**: PostgreSQL cannot add a NOT NULL column to a table that already has rows (no value for existing rows). Steps: (1) add nullable, (2) fill with UPDATE, (3) set NOT NULL.

## Migration 0002 self-check

| What to check | Result |
|---|---|
| Goal and steps | Yes. Add `level` column. Three steps: nullable → UPDATE → NOT NULL. |
| Data | Yes. Existing rows filled: electives → `beginner`, others → `intermediate`. |
| Renames and drops | No renames or drops. Only ADD COLUMN. |
| Rollback | Yes. `downgrade()` drops `level`. Level data lost on rollback — acceptable for training. |
| Verification | Yes. `--sql` reviewed. upgrade→downgrade→upgrade cycle tested. `alembic check` clean. |
| History | Yes. Single head. Migration committed with model and schema changes. |
| Application | Yes. `CourseOut` has `level`. `seed.sql` updated. `?level=` filter added to GET /courses. |
