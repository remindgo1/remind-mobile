FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install --no-cache-dir .
EXPOSE 8080
CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && uvicorn remind_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
