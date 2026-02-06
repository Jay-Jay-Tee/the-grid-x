# Grid-X Coordinator - run on ONE machine; workers connect via COORDINATOR_WS
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# HTTP API (clients, UI); WebSocket (workers)
ENV GRIDX_HTTP_PORT=8081
ENV GRIDX_WS_PORT=8080
ENV GRIDX_DB_PATH=/data/gridx.db

EXPOSE 8080 8081

# Persist DB outside container (mount /data)
RUN mkdir -p /data
VOLUME /data

CMD ["python", "main.py"]
