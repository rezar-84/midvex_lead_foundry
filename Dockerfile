FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.22
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN python manage.py collectstatic --noinput \
 && mkdir -p /data/evidence && chown 10001:10001 /data/evidence
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "lead_foundry.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
