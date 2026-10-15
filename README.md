# Course Catalog API

Бэкенд-сервис на FastAPI для управления каталогом курсов и записями студентов.

## Что изменено (Лабораторная работа 5)
- **CORS Middleware**: Добавлена поддержка Cross-Origin Resource Sharing для фронтенда `http://localhost:3000`.
- **CamelCase схемы**: Базовый класс `CamelModel` через Pydantic v2 (`alias_generator=to_camel`) преобразует имена полей в camelCase (`is_elective` -> `isElective`, `course_id` -> `courseId`).
- **Новые роуты**:
  - `POST /courses/{course_id}/like` — добавление лайка курсу (возвращает 200 с обновленным объектом курса, либо 404).
  - `POST /enrollments` — запись студента на курс (201 при успехе, 404 если курс не найден, 422 при валидации имени < 2 символов).
  - `GET /enrollments` — список всех записей.

## Инструкция по запуску
```bash
python -m venv .venv
# Активация окружения (Windows):
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
