FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# postgresql-client provides pg_dump for the weekly database backup task
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/backend

# PORT is set by Render (default 10000). start.sh binds Gunicorn to $PORT.
EXPOSE 10000

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
