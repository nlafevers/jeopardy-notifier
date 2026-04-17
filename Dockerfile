FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    PORT=8080 \
    DEBUG=false \
    REQUIRE_TURNSTILE=true \
    SECURE_SSL_REDIRECT=true \
    SESSION_COOKIE_SECURE=true \
    CSRF_COOKIE_SECURE=true \
    SECURE_HSTS_SECONDS=3600 \
    SECURE_HSTS_INCLUDE_SUBDOMAINS=true \
    SECURE_HSTS_PRELOAD=true \
    LOG_LEVEL=INFO

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["sh", "-c", "if [ -z \"$DATABASE_URL\" ]; then python manage.py migrate --noinput; fi && gunicorn jeopardy_notifier.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers ${WEB_CONCURRENCY:-1} --threads ${GUNICORN_THREADS:-8} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile - --log-level info"]
