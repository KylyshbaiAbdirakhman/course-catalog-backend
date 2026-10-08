# Course Catalog API

A simple REST API built with FastAPI to manage and browse a course catalog.

## How to Run It

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server using FastAPI CLI:
   ```bash
   fastapi dev main.py
   ```

## What Was Verified

Below are the verified requests and their expected outcomes tested during the lab:

- **`GET /courses`**
  - **Result:** Returns all 6 courses, with `ai-integration` first (32 likes) and `api-design` last (11 likes).

- **`GET /courses?is_elective=true`**
  - **Result:** Returns 2 elective courses: `ai-integration` and `api-design`.

- **`GET /courses?is_elective=false`**
  - **Result:** Returns 4 required courses: `modern-frontend`, `web-security`, `backend-fastapi`, and `databases-postgresql`.

- **`GET /courses?sort=title`**
  - **Result:** Returns all 6 courses sorted alphabetically by title (`ai-integration`, `api-design`, `backend-frontend` / `backend-fastapi`, etc.).

- **`GET /courses?page=1&page_size=2`**
  - **Result:** Returns the first 2 courses (`ai-integration`, `modern-frontend`).

- **`GET /courses?page=2&page_size=2`**
  - **Result:** Returns the next 2 courses (`web-security`, `backend-fastapi`).

- **`GET /courses?page=3&page_size=2`**
  - **Result:** Returns the following 2 courses (`databases-postgresql`, `api-design`).

- **`GET /courses?page=4&page_size=2`**
  - **Result:** Returns an empty list `[]` since there are no more items.

- **`GET /courses` (default page_size = 20)**
  - **Result:** Returns all 6 courses.

- **`GET /courses/web-security`**
  - **Result:** Returns the single course object for web security.

- **`GET /courses/nope`**
  - **Result:** Returns a `404 Not Found` status code with the JSON body `{"detail": "Course not found"}`.

GET /stats

Result: Returns catalog statistics using the Stats Pydantic model ({"total": 6, "total_credits": 28, "electives": 2}).