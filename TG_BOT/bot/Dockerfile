
FROM python:3.10-slim

WORKDIR /app

RUN pip install aiogram asyncpg psycopg2-binary

COPY . .

CMD ["python", "bot.py"]

