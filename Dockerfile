FROM python:3.11.5 AS base

WORKDIR /usr/src/code

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

EXPOSE 5005

FROM base AS development
ENV FLASK_ENV=development
CMD ["flask", "--app", "app:create_app", "run", "--debug", "--host=0.0.0.0", "--port=5005"]

FROM base AS production
ENV FLASK_ENV=production
COPY ./app ./app
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5005", "app:create_app()"]