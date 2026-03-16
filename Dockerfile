FROM python:3.13-slim AS base

WORKDIR /usr/src/code

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir --upgrade pip uv && uv sync --frozen --no-dev

EXPOSE 5005

FROM base AS development
ENV FLASK_ENV=development
CMD ["uv", "run", "flask", "--app", "app:create_app", "run", "--debug", "--host=0.0.0.0", "--port=5005"]

FROM base AS production
ENV FLASK_ENV=production
COPY ./app ./app
CMD ["uv", "run", "gunicorn", "-w", "1", "-b", "0.0.0.0:5005", "app:create_app()"]