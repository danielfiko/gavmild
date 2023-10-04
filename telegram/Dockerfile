FROM python:3.11.5

WORKDIR /usr/src/telegram
COPY requirements.txt .
RUN pip install -r requirements.txt --upgrade

COPY bot/ .

EXPOSE 5006
CMD ["python", "bot/run.py"]
