FROM python:3.11.5

WORKDIR /usr/src/backend
COPY requirements.txt .
RUN pip install -r requirements.txt --upgrade

COPY . .

EXPOSE 5005
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5005", "app:create_app()"]
