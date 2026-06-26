FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    cron git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cron job: hourly ingest
COPY deploy/ingest.cron /etc/cron.d/kb-ingest
RUN chmod 0644 /etc/cron.d/kb-ingest

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5057

CMD ["/entrypoint.sh"]
